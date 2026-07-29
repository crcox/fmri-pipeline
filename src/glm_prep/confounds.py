import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from glm_prep.errors import DataContractError
from glm_prep.models import (
    ACompCorMask,
)
from glm_prep.types import Vector

MotionConfounds = Mapping[str, Vector]
ACompCorConfounds = Mapping[str, Vector]


@dataclass(frozen=True)
class ACompCorComponentInfo:
    name: str
    mask: ACompCorMask
    retained: bool
    singular_value: float
    variance_explained: float
    cumulative_variance_explained: float


ACompCorMetadata = Mapping[str, ACompCorComponentInfo]

DriftConfounds = Mapping[str, Vector]
TedanaComponents = Mapping[str, Vector]


@dataclass(frozen=True)
class TedanaComponentInfo:
    component_id: str
    classification: str
    tags: set[str]
    metrics: Mapping[str, float]


TedanaMetadata = Mapping[str, TedanaComponentInfo]

_TEDANA_REQUIRED_CLASSIFICATION: tuple[str, ...] = (
    "Component",
    "classification",
    "classification_tags",
)
_TEDANA_REQUIRED_METRICS: tuple[str, ...] = ("kappa", "rho")
_TEDANA_OPTIONAL_METRICS: tuple[str, ...] = (
    "variance explained",
    "normalized variance explained",
    "countsigFT2",
    "countsigFS0",
    "dice_FT2",
    "dice_FS0",
    "countnoise",
    "signal-noise_t",
    "signal-noise_p",
    "d_table_score",
    "optimal sign",
    "varex kappa ratio",
    "d_table_score_node20",
    "Var Exp of rejected to accepted",
)

_ACOMPCOR_PREFIXES: tuple[str, ...] = (
    "a_comp_cor_",
    "w_comp_cor_",
    "c_comp_cor_",
)


def validate_tedana_metrics(df: pd.DataFrame, metrics: Sequence[str]) -> None:
    missing: list[str] = []
    for metric in metrics:
        if metric not in df.columns:
            missing.append(metric)

    if missing:
        raise DataContractError(
            "Missing required Tedana metrics columns:\n"
            + "\n".join(f"  - {m!r}" for m in missing)
        )


def ensure_1d(array: np.ndarray) -> Vector:
    if array.ndim != 1:
        raise ValueError(f"Expected 1D array, got shape {array.shape}")
    return cast(Vector, array)


def get_vector(df: pd.DataFrame, col: str) -> Vector:
    if col not in df.columns:
        raise DataContractError(f"Missing column {col!r}")

    series = df[col]
    array = series.to_numpy(dtype=np.float64)

    return ensure_1d(array)


def read_confounds_timeseries(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", na_values="n/a")


def parse_confounds_timeseries(
    df: pd.DataFrame,
) -> tuple[MotionConfounds, ACompCorConfounds, DriftConfounds]:
    motion: dict[str, Vector] = {
        col: get_vector(df, col)
        for col in df.columns
        if col.startswith(("trans_", "rot_"))
    }
    acompcor: dict[str, Vector] = {
        col: get_vector(df, col)
        for col in df.columns
        if col.startswith(_ACOMPCOR_PREFIXES)
    }
    cosine: dict[str, Vector] = {
        col: get_vector(df, col)
        for col in df.columns
        if re.fullmatch(r"cosine_?\d{2}", col)
    }
    return motion, acompcor, cosine


def read_tedana_components(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", na_values="n/a")


def parse_tedana_components(df: pd.DataFrame) -> TedanaComponents:
    components: dict[str, Vector] = {col: get_vector(df, col) for col in df.columns}
    return components


def read_tedana_metrics(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", na_values="n/a")


def parse_tedana_metrics(df: pd.DataFrame) -> TedanaMetadata:
    required_fields = _TEDANA_REQUIRED_CLASSIFICATION + _TEDANA_REQUIRED_METRICS
    validate_tedana_metrics(df, required_fields)
    records = df.to_dict(orient="records")

    metadata: dict[str, TedanaComponentInfo] = {}

    for row in records:
        try:
            component_id = str(row["Component"])
            classification = str(row["classification"])
            raw_tags = str(row["classification_tags"])
        except KeyError as e:
            raise DataContractError(
                f"Missing required tedana field {e.args[0]!r}"
            ) from e

        metrics: dict[str, float] = {}

        for metric in _TEDANA_REQUIRED_METRICS + _TEDANA_OPTIONAL_METRICS:
            if metric not in row:
                continue

            if pd.isna(row[metric]):
                continue

            try:
                value = float(row[metric])
            except (TypeError, ValueError) as e:
                raise DataContractError(
                    f"Invalid value for tedana metric {metric!r}"
                ) from e

            metrics[metric] = value

        tags = {t.strip() for t in raw_tags.split(",") if t.strip()}

        info = TedanaComponentInfo(
            component_id=component_id,
            classification=classification,
            tags=tags,
            metrics=metrics,
        )
        metadata[component_id] = info

    return metadata


def read_acompcor_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise DataContractError(f"aCompCor metadata file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataContractError(
            f"Failed to parse aCompCor metadata JSON: {path}"
        ) from e

    if not isinstance(data, dict):
        raise DataContractError(
            f"aCompCor metadata must be a JSON object at top level: {path}"
        )

    return data


def parse_acompcor_metadata(json_dict: dict[str, Any]) -> ACompCorMetadata:
    metadata: dict[str, ACompCorComponentInfo] = {}

    for name, data in json_dict.items():
        if data.get("Method") != "aCompCor":
            continue

        if not isinstance(data, dict):
            raise DataContractError(f"Metadata entry for {name!r} must be an object")

        try:
            mask = ACompCorMask(data["Mask"])
            retained = bool(data["Retained"])
            singular_value = float(data["SingularValue"])
            variance_explained = float(data["VarianceExplained"])
            cumulative_variance_explained = float(data["CumulativeVarianceExplained"])
        except KeyError as e:
            raise DataContractError(
                f"Missing required aCompCor field {e.args[0]!r} for {name}"
            ) from e
        except (TypeError, ValueError) as e:
            raise DataContractError(
                f"Invalid value in aCompCor metadata for {name!r}"
            ) from e

        metadata[name] = ACompCorComponentInfo(
            name=name,
            mask=mask,
            retained=retained,
            singular_value=singular_value,
            variance_explained=variance_explained,
            cumulative_variance_explained=cumulative_variance_explained,
        )

    if not metadata:
        raise DataContractError("No aCompCor metadata in JSON")

    return metadata


@dataclass(frozen=True)
class Confounds:
    motion: MotionConfounds
    acompcor: ACompCorConfounds
    acompcor_metadata: ACompCorMetadata
    drift: DriftConfounds
    tedana_components: TedanaComponents
    tedana_metadata: TedanaMetadata
