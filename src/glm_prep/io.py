import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from glm_prep.artifacts import (
    DesignMatrix,
    DesignMatrixProvenance,
    DesignMatrixSummary,
    RegressorDiagnostics,
    RegressorInfo,
    RegressorSource,
)
from glm_prep.domain import RunKey


def design_prefix(root: Path, run_key: RunKey) -> Path:
    design_dir = root / f"sub-{run_key.subject:03d}" / "design"
    design_stem = f"sub-{run_key.subject:03d}_run-{run_key.run:02d}_design"
    return design_dir / design_stem


def serialize_regressor_info(
    regressor: RegressorInfo,
) -> dict[str, Any]:
    return {
        "name": regressor.name,
        "source": regressor.source.value,
        "column": regressor.column,
        "metadata": regressor.metadata,
        "diagnostics": regressor.diagnostics.to_dict(),
    }


def deserialize_regressor_info(
    data: dict[str, Any],
) -> RegressorInfo:
    return RegressorInfo(
        name=data["name"],
        source=RegressorSource(data["source"]),
        column=data["column"],
        metadata=data["metadata"],
        diagnostics=RegressorDiagnostics.from_dict(data["diagnostics"]),
    )


def deserialize_provenance(
    data: dict[str, Any],
) -> DesignMatrixProvenance:
    return DesignMatrixProvenance(
        subject=int(data["subject"]),
        run=int(data["run"]),
        events_file=Path(data["events_file"]),
        bold_data_file=Path(data["bold_data_file"]),
        bold_metadata_file=Path(data["bold_metadata_file"]),
        confound_timeseries_file=Path(data["confound_timeseries_file"]),
        confound_metadata_file=Path(data["confound_metadata_file"]),
        tedana_components_file=Path(data["tedana_components_file"])
        if "tedana_components_file" in data
        else None,
        tedana_metrics_file=Path(data["tedana_metrics_file"])
        if "tedana_metrics_file" in data
        else None,
        policy_file=Path(data["policy_file"]),
    )


def save_design_matrix_summary(
    summary: DesignMatrixSummary, root: Path, run_key: RunKey
) -> None:
    prefix = design_prefix(root, run_key)

    prefix.parent.mkdir(parents=True, exist_ok=True)

    path = prefix.parent / f"{prefix.name}_summary.json"

    with path.open("w") as f:
        json.dump(asdict(summary), f, indent=2)


def save_design_matrix(
    design: DesignMatrix,
    root: Path,
    run_key: RunKey,
) -> None:
    prefix = design_prefix(root, run_key)

    prefix.parent.mkdir(parents=True, exist_ok=True)

    np.save(prefix.with_suffix(".npy"), design.matrix)

    with open(prefix.with_suffix(".json"), "w") as f:
        json.dump(
            {
                "version": 1,
                "provenance": design.provenance.to_dict(),
                "regressors": [serialize_regressor_info(r) for r in design.regressors],
            },
            f,
            indent=2,
        )


def load_design_matrix(root: Path, run_key: RunKey) -> DesignMatrix:
    prefix = design_prefix(root, run_key)

    matrix = np.load(prefix.with_suffix(".npy"))

    with open(prefix.with_suffix(".json"), "r") as f:
        data = json.load(f)

    regressors = [deserialize_regressor_info(x) for x in data["regressors"]]
    provenance = deserialize_provenance(data["provenance"])

    return DesignMatrix(
        matrix=matrix,
        regressors=regressors,
        provenance=provenance,
    )
