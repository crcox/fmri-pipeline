from glm_prep.models import (
    MotionModel,
    MotionPolicy,
    ACompCorFixedModel,
    ACompCorVarianceModel,
    ACompCorModel,
    ACompCorMask,
    ACompCorPolicy,
    DriftCosineFromTSV,
    DriftCosineGenerated,
    DriftModel,
    DriftPolicy,
    TedanaClassificationSelection,
    TedanaMetricSelection,
    TedanaSelection,
    TedanaPolicy,
    GLMPolicy
)
from glm_prep.errors import ParseError
from pathlib import Path
import yaml


def _parse_motion(data: dict | None, path: list[str]) -> MotionPolicy | None:
    if data is None:
        return None

    if "model" not in data:
        raise ParseError(
            "motion policy requires 'model'",
            path=path,
            expected="key 'model'",
            received=data
        )

    try:
        model = MotionModel(data["model"])
    except ValueError:
        raise ParseError(
            "Invalid motion model",
            path=path + ['model'],
            expected="one of ['base', 'derivatives', or 'full']",
            received=data['model']
        )

    return MotionPolicy(
        model=model
    )


def _parse_acompcor_model(data: dict, path: list[str]) -> ACompCorModel:
    if "n_components" in data:
        return ACompCorFixedModel(n_components=data["n_components"])

    if "variance_explained" in data:
        return ACompCorVarianceModel(
            variance_explained=data["variance_explained"]
        )

    raise ParseError(
        "acompcor model must specify either 'n_components' or 'variance_explained'",
        path=path,
        expected="one of ['n_components', 'variance_explained']",
        received=data
    )


def _parse_acompcor(data: dict | None, path: list[str]) -> ACompCorPolicy | None:
    if data is None:
        return None

    if "mask" not in data:
        raise ParseError(
            "acompcor policy requires 'mask'",
            path=path,
            expected="'mask: wm' OR 'mask: 'csf' OR 'mask: combined'.",
            received=data
        )

    if "model" not in data:
        raise ParseError(
            "acompcor policy requires 'model'",
            path=path,
            expected=(
                "A 'model' field must exist under 'acompcor', which should "
                "itself contain either 'n_components' or 'variance_explained'"
            ),
            received=data
        )

    try:
        mask = ACompCorMask(data['mask'])
    except ValueError:
        raise ParseError(
            "Invalid acompcor mask",
            path=path + ['mask'],
            expected="one of ['wm', 'csf', or 'combined']",
            received=data['mask']
        )

    model_data = data['model']

    model = _parse_acompcor_model(model_data, path=path + ['model'])

    return ACompCorPolicy(mask=mask, model=model)


def _parse_drift_cosine(data: dict, path: list[str]) -> DriftModel:
    if data == {}:
        return DriftCosineFromTSV()

    elif "generate" in data:
        generate = data["generate"]

        if "high_pass" not in generate:
            raise ParseError(
                "cosine.generate requires 'high_pass'",
                path=path,
                expected="key 'high_pass'",
                received=data
            )

        return DriftCosineGenerated(high_pass=generate["high_pass"])

    raise ParseError(
        "Invalid drift.cosine specification",
        path=path,
        expected=(
            "Either an empty dict '{}' signalling that cosine bases should be "
            "read from desc-confounds_timeseries.tsv or 'generate' if you intend "
            "to generate a cosine basis set."
        ),
        received=data
    )


def _parse_drift(data: dict | None, path: list[str]) -> DriftPolicy | None:
    if data is None:
        return None

    if "cosine" not in data:
        raise ParseError(
            "drift policy currently supports only 'cosine'",
            path=path,
            expected=(
                "A 'cosine' field under drift, containing either an empty dict "
                "'{}' signalling the cosine bases should be read from "
                "desc-confounds_timeseries.tsv or 'generate' if you intend to "
                "generate a cosine basis set."
            ),
            received=data
        )

    cosine_data = data["cosine"]
    model = _parse_drift_cosine(cosine_data, path=path+['cosine'])

    return DriftPolicy(model=model)


def _parse_tedana_classification(data: dict, path: list[str]) -> TedanaClassificationSelection:
    if not data:
        return TedanaClassificationSelection()

    tags = data.get("tags", {})
    include = tags.get("include")

    return TedanaClassificationSelection(tags_include=include)


def _parse_tedana_metric(data: dict, path: list[str]) -> TedanaMetricSelection:
    if "name" not in data:
        raise ParseError(
            "metric selection requires 'name'",
            path=path,
            expected="key 'name'",
            received=data
        )

    return TedanaMetricSelection(
        metric=data["name"],
        top_k=data.get("top_k"),
        threshold=data.get("threshold"),
    )


def _parse_tedana_selection(data: dict[str, Any], path: list[str]) -> TedanaSelection:
    if "classification" in data:
        model = _parse_tedana_classification(data["classification"], path=path + ['classification'])
        return model

    if "metric" in data:
        model = _parse_tedana_metric(data["metric"], path=path+['metric'])
        return model

    raise ParseError(
        "tedana selection must specify 'classification' or 'metric'",
        path=path,
        expected="one of ['classification', 'metric']",
        received=data
    )



def _parse_tedana(data: dict | None, path: list[str]) -> TedanaPolicy | None:
    if data is None:
        return None

    if "selection" not in data:
        raise ParseError(
            "tedana policy requires 'selection'",
            path=path,
            expected="key 'selection'",
            received=data
        )

    selection = _parse_tedana_selection(data["selection"], path=path + ['selection'])

    return TedanaPolicy(selection=selection)


def _load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}
    return data


def load_policy(path: Path) -> GLMPolicy:
    data = _load_yaml(path)
    return GLMPolicy(
        motion=_parse_motion(data.get("motion"), path=['motion']),
        acompcor=_parse_acompcor(data.get("acompcor"), path=['acompcor']),
        drift=_parse_drift(data.get("drift"), path=['drift']),
        tedana=_parse_tedana(data.get("tedana"), path=['tedana']),
    )

