import re

from glm_prep.artifacts import (
    Regressor,
    RegressorDiagnostics,
    RegressorInfo,
    RegressorSource,
)
from glm_prep.confounds import (
    ACompCorConfounds,
    ACompCorMetadata,
    DriftConfounds,
    MotionConfounds,
    TedanaComponents,
    TedanaMetadata,
)
from glm_prep.errors import DataContractError, PolicyDefinitionError
from glm_prep.models import (
    ACompCorFixedModel,
    ACompCorPolicy,
    ACompCorVarianceModel,
    DriftCosineFromTSV,
    DriftPolicy,
    MotionModel,
    MotionPolicy,
    TedanaClassificationSelection,
    TedanaMetricSelection,
    TedanaPolicy,
)

_MOTION_BASE = [
    "trans_x",
    "trans_y",
    "trans_z",
    "rot_x",
    "rot_y",
    "rot_z",
]


def derivative_name(name: str) -> str:
    return f"{name}_derivative1"


def square_name(name: str) -> str:
    return f"{name}_power2"


def deriv_square_name(name: str) -> str:
    return f"{name}_derivative1_power2"


def validate_motion_model(model: MotionModel, motion: MotionConfounds) -> None:
    motion_key_set = set(motion.keys())

    missing: set[str] = set()

    if model in {MotionModel.DERIVATIVES, MotionModel.FULL}:
        required = {derivative_name(x) for x in _MOTION_BASE}
        missing.update(required - motion_key_set)

    if model == MotionModel.FULL:
        required = {square_name(x) for x in _MOTION_BASE}
        required.update(deriv_square_name(x) for x in _MOTION_BASE)
        missing.update(required - motion_key_set)

    if missing:
        raise DataContractError(
            f"Missing motion confounds required by model {model.value}:\n"
            + "\n".join(f"  - {m!r}" for m in missing)
        )


def build_motion(policy: MotionPolicy, motion: MotionConfounds) -> list[Regressor]:

    model = policy.model
    validate_motion_model(model, motion)

    regressors: list[Regressor] = []

    def build_regressor(
        name: str,
        kind: str,
        base_name: str,
        motion: MotionConfounds,
    ) -> Regressor:
        values = motion[name]
        info = RegressorInfo(
            name=name,
            source=RegressorSource.MOTION,
            column=-1,
            metadata={
                "motion_param": base_name,
                "term": kind,  # base, derivative, square, derivative_square
            },
            diagnostics=RegressorDiagnostics.from_values(values),
        )

        return Regressor(values=values, info=info)

    # Base parameters
    for name in _MOTION_BASE:
        regressors.append(
            build_regressor(name=name, kind="base", base_name=name, motion=motion)
        )

    # Add derivatives
    if model in {MotionModel.DERIVATIVES, MotionModel.FULL}:
        for name in _MOTION_BASE:
            regressors.append(
                build_regressor(
                    name=derivative_name(name),
                    kind="derivative",
                    base_name=name,
                    motion=motion,
                )
            )

    # Add squares
    if model == MotionModel.FULL:
        for name in _MOTION_BASE:
            regressors.append(
                build_regressor(
                    square_name(name),
                    kind="square",
                    base_name=name,
                    motion=motion,
                )
            )

        for name in _MOTION_BASE:
            regressors.append(
                build_regressor(
                    deriv_square_name(name),
                    kind="derivative_square",
                    base_name=name,
                    motion=motion,
                )
            )

    return regressors


def build_drift(
    policy: DriftPolicy,
    confounds: DriftConfounds,
) -> list[Regressor]:

    regressors: list[Regressor] = []

    if isinstance(policy.model, DriftCosineFromTSV):
        # ASSUMPTION: fmri prep only models drift with discrete cosine transform (DCT)
        metadata = {
            "model": "cosine",
            "source": "fmri_prep",
        }
    else:
        raise NotImplementedError

    for name in sorted(confounds.keys()):
        values = confounds[name]
        regressors.append(
            Regressor(
                values=values,
                info=RegressorInfo(
                    name=name,
                    source=RegressorSource.DRIFT,
                    column=-1,
                    metadata=metadata,
                    diagnostics=RegressorDiagnostics.from_values(values),
                ),
            )
        )

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
            selected_ids = [cid for cid, val in scored if val >= selection.threshold]

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
                    diagnostics=RegressorDiagnostics.from_values(values),
                ),
            )
        )

    return regressors


_COMPONENT_RE = re.compile(r"^(?:a|w|c)_comp_cor_(\d+)$")


def acompcor_index(name: str) -> int:
    match = _COMPONENT_RE.fullmatch(name)
    if match is None:
        raise DataContractError(f"Invalid aCompCor component name {name!r}")

    return int(match.group(1))


def build_acompcor(
    policy: ACompCorPolicy,
    confounds: ACompCorConfounds,
    metadata: ACompCorMetadata,
) -> list[Regressor]:

    selected_metadata = {
        name: info for name, info in metadata.items() if info.mask == policy.mask
    }

    missing = set(selected_metadata) - set(confounds)

    if missing:
        raise DataContractError(
            "Missing aCompCor vectors:\n" + "\n".join(sorted(missing))
        )

    sorted_names = sorted(
        selected_metadata,
        key=acompcor_index,
    )

    model = policy.model

    if isinstance(model, ACompCorFixedModel):
        selected_names = sorted_names[: model.n_components]

    elif isinstance(model, ACompCorVarianceModel):
        selected_names: list[str] = []

        for name in sorted_names:
            selected_names.append(name)

            info = selected_metadata[name]

            if info.cumulative_variance_explained >= model.variance_explained:
                break

    else:
        raise ValueError(f"Unsupported aCompCor model {type(model)!r}")

    regressors: list[Regressor] = []

    for name in selected_names:
        info = selected_metadata[name]
        values = confounds[name]

        regressors.append(
            Regressor(
                values=values,
                info=RegressorInfo(
                    name=name,
                    source=RegressorSource.ACOMPCOR,
                    column=-1,
                    metadata={
                        "mask": info.mask.value,
                        "variance_explained": info.variance_explained,
                        "cumulative_variance_explained": info.cumulative_variance_explained,
                    },
                    diagnostics=RegressorDiagnostics.from_values(values),
                ),
            )
        )

    return regressors
