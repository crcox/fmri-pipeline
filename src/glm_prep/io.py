import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from glm_prep.artifacts import (
    DesignMatrix,
    DesignMatrixSummary,
    RegressorInfo,
    RegressorSource,
)
from glm_prep.design import DesignMatrixProvenance
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
        diagnostics=data["diagnostics"],
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
    provenance: DesignMatrixProvenance,
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
                "provenance": provenance.to_dict(),
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

    return DesignMatrix(
        matrix=matrix,
        regressors=regressors,
    )
