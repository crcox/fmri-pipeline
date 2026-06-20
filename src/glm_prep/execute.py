import pandas as pd

from glm_prep.types import Vector
from glm_prep.errors import DataContractError, PolicyDefinitionError
from glm_prep.models import (
    MotionPolicy,
    MotionModel,
    TedanaPolicy,
    TedanaClassificationSelection,
    TedanaMetricSelection,
    ACompCorPolicy,
    ACompCorFixedModel,
    ACompCorVarianceModel
)
from glm_prep.confounds import TedanaComponents, TedanaMetadata, ACompCorConfounds, ACompCorMetadata
from glm_prep.artifacts import RegressorInfo, RegressorSource, Regressor


MOTION_BASE = [
    "trans_x", "trans_y", "trans_z",
    "rot_x", "rot_y", "rot_z",
]


def derivative_name(name: str) -> str:
    return f"{name}_derivative1"


def square_name(name: str) -> str:
    return f"{name}_power2"


def deriv_square_name(name: str) -> str:
    return f"{name}_derivative1_power2"


def build_motion(policy: MotionPolicy, df: pd.DataFrame) -> list[Regressor]:

    regressors: list[Regressor] = []

    def build_regressor(name: str, kind: str, base_name: str, df: pd.DataFrame) -> Regressor:
        if name not in df.columns:
            raise DataContractError(f"Missing motion column '{name}' in confounds")

        values: Vector = ensure_1d(df[name].to_numpy())
        col_idx: int = len(columns)

        info = RegressorInfo(
            name=name,
            source=RegressorSource.MOTION,
            column=col_idx,
            metadata={
                "motion_param": base_name,
                "term": kind,   # base, derivative, square, derivative_square
            },
        )
        return Regressor(values=values, info=info)

    model = policy.model

    # Base parameters
    for name in MOTION_BASE:
        regressors.append(build_regressor(
            name,
            kind="base",
            base_name=name,
            df=df
        ))

    # Add derivatives
    if model in {MotionModel.DERIVATIVES, MotionModel.FULL}:
        for name in MOTION_BASE:
            regressors.append(build_regressor(
                derivative_name(name),
                kind="derivative",
                base_name=name,
                df=df,
            ))

    # Add squares
    if model == MotionModel.FULL:
        for name in MOTION_BASE:
            regressors.append(build_regressor(
                square_name(name),
                kind="square",
                base_name=name,
                df=df,
            ))

        for name in MOTION_BASE:
            regressors.append(build_regressor(
                deriv_square_name(name),
                kind="derivative_square",
                base_name=name,
                df=df,
            ))

    return regressors


def build_tedana(
    policy: TedanaPolicy,
    components: TedanaComponents,
    metadata: TedanaMetadata,
) -> list[Regressor]:

    regressors: list[Regressor] = []
    selected_ids: list[str] = []
    selection = policy.selection

    # --- CLASSIFICATION-BASED SELECTION ---
    if isinstance(selection, TedanaClassificationSelection):
        for component_id, info in metadata.items():
            if info.classification != "rejected":
                continue

            if selection.tags_include:
                if not (info.tags & set(selection.tags_include)):
                    continue

            selected_ids.append(component_id)

    # --- METRIC-BASED SELECTION ---
    # Need to REALLY check this. Not sure how metrics relate to evidence of
    # BOLD
    elif isinstance(selection, TedanaMetricSelection):
        metric_name = selection.metric
        scored: list[tuple[str, float]] = []

        for component_id, info in metadata.items():
            value = info.metrics.get(metric_name)

            if value is None:
                continue

            scored.append((component_id, value))

        scored.sort(key=lambda x: x[1], reverse=True)

        if selection.top_k is not None:
            selected_ids = [cid for cid, _ in scored[: selection.top_k]]

        elif selection.threshold is not None:
            selected_ids = [
                cid
                for cid, val in scored
                if val >= selection.threshold
            ]

    else:
        raise PolicyDefinitionError("Unknown Tedana selection type")

    # --- BUILD REGRESSORS ---
    for component_id in selected_ids:

        if component_id not in components:
            raise DataContractError(
                f"Tedana component {component_id!r} missing from components"
            )

        values = components[component_id]
        info = metadata[component_id]

        regressors.append(
            Regressor(
                values=values,
                info=RegressorInfo(
                    name=f"tedana_{component_id}",
                    source=RegressorSource.TEDANA,
                    column=-1,  # assigned later
                    metadata={
                        "component_id": component_id,
                        "classification": info.classification,
                        "tags": sorted(info.tags),
                        "metrics": info.metrics,
                    },
                ),
            )
        )

    return regressors


def build_acompcor(
    policy: ACompCorPolicy,
    confounds: ACompCorConfounds,
    cumulative_map: ACompCorMetadata | None = None,
) -> list[Regressor]:

    missing = set(confounds) - set(cumulative_map)

    if missing:
        raise DataContractError(
            "aCompCor metadata is missing entries for:\n"
            + "\n".join(f"  - {m}" for m in sorted(missing))
        )

    regressors: list[Regressor] = []

    def acompcor_index(name: str) -> int:
        return int(name.split("_")[-1])

    sorted_names = sorted(confounds, key=acompcor_index)
    selected_names: list[str] = []
    model = policy.model

    # --- FIXED MODEL ---
    if isinstance(model, ACompCorFixedModel):
        selected_names = sorted_names[: model.n_components]

    # --- VARIANCE MODEL ---
    elif isinstance(model, ACompCorVarianceModel):

        if cumulative_map is None:
            raise DataContractError(
                "Variance model requires cumulative variance information"
            )

        selected_names = []

        for name in sorted_names:
            selected_names.append(name)

            if cumulative_map[name] >= model.variance_explained:
                break

    else:
        raise PolicyDefinitionError("Unknown aCompCor model")

    # --- BUILD REGRESSORS ---
    for name in selected_names:
        values = confounds[name]

        regressors.append(
            Regressor(
                values=values,
                info=RegressorInfo(
                    name=name,
                    source=RegressorSource.ACOMPCOR,
                    column=-1,
                    metadata={
                        "component": name,
                        "index": acompcor_index(name),
                        "model": type(model).__name__,
                    },
                ),
            )
        )

    return regressors
