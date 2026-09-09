from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from nilearn.glm.first_level import make_first_level_design_matrix

from glm_prep.artifacts import (
    DesignMatrix,
    DesignMatrixSummary,
    Regressor,
    RegressorDiagnostics,
    RegressorInfo,
    RegressorSource,
)
from glm_prep.builders import build_acompcor, build_drift, build_motion, build_tedana
from glm_prep.confounds import Confounds, ensure_1d
from glm_prep.errors import DataContractError
from glm_prep.locate import RunFiles
from glm_prep.models import GLMPolicy, StimulusPolicy

_REQUIRED_COLUMNS: tuple[str, ...] = ("onset", "duration", "stimulus")


@dataclass(frozen=True)
class BoldMetadata:
    repetition_time: float


def read_bold_metadata(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataContractError(f"Failed to parse BOLD metadata JSON: {path}") from e

    if not isinstance(data, dict):
        raise DataContractError(
            f"BOLD metadata must be a JSON object at top level: {path}"
        )

    return cast(dict[str, Any], data)


def parse_bold_metadata(data: dict[str, Any]) -> BoldMetadata:

    try:
        tr = float(data["RepetitionTime"])
    except KeyError as e:
        raise DataContractError(
            f"Missing required BOLD metadata field {e.args[0]!r}"
        ) from e
    except (TypeError, ValueError) as e:
        raise DataContractError("Invalid value in BOLD metadata") from e

    return BoldMetadata(repetition_time=tr)


@dataclass(frozen=True)
class Event:
    onset: float
    duration: float
    stimulus: str


@dataclass(frozen=True)
class DesignMatrixProvenance:
    subject: int
    run: int

    events_file: str
    bold_data_file: str
    bold_metadata_file: str

    confound_timeseries_file: str
    confound_metadata_file: str

    tedana_components_file: str | None
    tedana_metrics_file: str | None

    policy_file: str

    @classmethod
    def from_runfiles(
        cls,
        run: RunFiles,
        policy: Path,
    ) -> DesignMatrixProvenance:
        return cls(
            subject=run.events.key.subject,
            run=run.events.key.run,
            events_file=str(run.events.path),
            bold_data_file=str(run.bold_data.path),
            bold_metadata_file=str(run.bold_metadata.path),
            confound_timeseries_file=str(run.confound_timeseries.path),
            confound_metadata_file=str(run.confound_metadata.path),
            tedana_components_file=(
                str(run.tedana_components.path)
                if run.tedana_components is not None
                else None
            ),
            tedana_metrics_file=(
                str(run.tedana_metrics.path) if run.tedana_metrics is not None else None
            ),
            policy_file=str(policy),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def read_events(path: Path) -> pd.DataFrame:
    return pd.read_table(path)


def _parse_event(row: dict[str, Any]) -> Event:
    try:
        onset = float(row["onset"])
        duration = float(row["duration"])
        stimulus = str(row["stimulus"])
    except (TypeError, ValueError) as e:
        raise DataContractError("Invalid event row") from e

    if onset < 0:
        raise DataContractError(f"Invalid onset: {onset!r}")

    if duration < 0:
        raise DataContractError(f"Invalid duration: {duration!r}")

    if not stimulus:
        raise DataContractError("Empty stimulus label")

    return Event(onset=onset, duration=duration, stimulus=stimulus)


def parse_events(df: pd.DataFrame) -> list[Event]:
    missing = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise DataContractError(
            "Missing required event columns:\n"
            + "\n".join(f"  - {col!r}" for col in missing)
        )

    events: list[Event] = []

    rows = df.to_dict(orient="records")
    rows = cast(list[dict[str, Any]], rows)

    for row in rows:
        events.append(_parse_event(row))

    return events


def build_stimulus_simple(
    policy: StimulusPolicy,
    events: list[Event],
    frame_times: np.ndarray,
) -> list[Regressor]:
    events_df = pd.DataFrame(
        {
            "onset": [e.onset for e in events],
            "duration": [e.duration for e in events],
            "trial_type": [e.stimulus for e in events],
        }
    )

    design_matrix = make_first_level_design_matrix(
        frame_times, events_df, hrf_model=policy.hrf_model
    )

    if design_matrix.empty:
        raise DataContractError("Nilearn produced an empty design matrix.")

    # if not isinstance(design_matrix, pd.DataFrame):
    #    raise DataContractError(
    #        f"Expected nilearn.glm.make_first_level_design_matrix to return a pd.DataFrame. Received: {type(design_matrix)!r}"
    #    )

    stimulus_names = sorted({e.stimulus for e in events})

    stimulus_columns = [col for col in design_matrix.columns if col in stimulus_names]

    regressors: list[Regressor] = []

    for col in stimulus_columns:
        values = ensure_1d(design_matrix[col].to_numpy(dtype=np.float64))

        regressors.append(
            Regressor(
                values=values,
                info=RegressorInfo(
                    name=col,
                    source=RegressorSource.STIMULUS,
                    column=-1,
                    metadata={
                        "stimulus": col,
                        "hrf_model": policy.hrf_model,
                    },
                    diagnostics=RegressorDiagnostics.from_values(values),
                ),
            )
        )

    return regressors


def summarize_design_matrix(design: DesignMatrix) -> DesignMatrixSummary:
    counts = Counter(reg.source for reg in design.regressors)
    return DesignMatrixSummary(
        n_timepoints=int(design.matrix.shape[0]),
        n_regressors=int(design.matrix.shape[1]),
        matrix_rank=int(np.linalg.matrix_rank(design.matrix)),
        stimulus=int(counts[RegressorSource.STIMULUS]),
        drift=int(counts[RegressorSource.DRIFT]),
        motion=int(counts[RegressorSource.MOTION]),
        acompcor=int(counts[RegressorSource.ACOMPCOR]),
        tedana=int(counts[RegressorSource.TEDANA]),
    )


def assemble_design_matrix(regressors: list[Regressor]) -> DesignMatrix:

    if not regressors:
        raise DataContractError("No regressors selected.")

    n_timepoints = regressors[0].values.shape[0]

    for regressor in regressors[1:]:
        if regressor.values.shape[0] != n_timepoints:
            raise DataContractError(
                "Regressor lengths do not match. "
                f"Exception raised while checking: {regressor.info.name!r}"
            )

    matrix = np.column_stack([r.values for r in regressors])

    return DesignMatrix(
        matrix=matrix,
        regressors=[replace(r.info, column=i) for i, r in enumerate(regressors)],
    )


def build_design_matrix(
    stimulus: list[Regressor],
    drift: list[Regressor],
    motion: list[Regressor],
    acompcor: list[Regressor],
    tedana: list[Regressor],
) -> DesignMatrix:
    regressors = stimulus + drift + motion + acompcor + tedana

    return assemble_design_matrix(regressors)


def prepare_design_matrix(
    policy: GLMPolicy,
    confounds: Confounds,
    events: list[Event],
    frame_times: np.ndarray,
) -> DesignMatrix:
    stimulus = build_stimulus_simple(policy.stimulus, events, frame_times)

    drift: list[Regressor] = []
    motion: list[Regressor] = []
    acompcor: list[Regressor] = []
    tedana: list[Regressor] = []

    if policy.drift:
        drift = build_drift(policy.drift, confounds.drift)

    if policy.motion:
        motion = build_motion(policy.motion, confounds.motion)

    if policy.acompcor:
        acompcor = build_acompcor(
            policy.acompcor, confounds.acompcor, confounds.acompcor_metadata
        )

    if policy.tedana:
        tedana = build_tedana(
            policy.tedana, confounds.tedana_components, confounds.tedana_metadata
        )

    return build_design_matrix(
        stimulus=stimulus,
        drift=drift,
        motion=motion,
        acompcor=acompcor,
        tedana=tedana,
    )
