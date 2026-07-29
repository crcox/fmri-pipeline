from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from glm_prep.errors import DataContractError
from glm_prep.types import Matrix, Vector


@dataclass(frozen=True)
class DesignMatrix:
    """
    A fully expanded, time-aligned regressor matrix ready for GLM fitting
    """

    matrix: Matrix
    regressors: list[RegressorInfo]

    @property
    def ncol(self):
        return self.matrix.shape[1]

    @property
    def column_names(self) -> list[str]:
        return [r.name for r in self.regressors]

    def __post_init__(self):
        if len(self.column_names) != self.ncol:
            raise DataContractError(
                f"Column name count ({len(self.column_names)}) does not match "
                f"number of regressors ({self.ncol})."
            )

        if self.matrix.ndim != 2:
            raise DataContractError(
                "The design matrix must be a 2-dimensional nparray."
                f"  Attempted to define with {self.matrix.ndim} dimensions."
            )


class RegressorSource(str, Enum):
    MOTION = "motion"
    ACOMPCOR = "acompcor"
    DRIFT = "drift"
    TEDANA = "tedana"
    DESIGN = "design"


@dataclass(frozen=True)
class RegressorInfo:
    name: str
    source: RegressorSource
    column: int
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Regressor:
    values: Vector
    info: RegressorInfo


@dataclass(frozen=True)
class TimingMetadata:
    """
    Explicit timing parameters for the run.
    """

    tr: float  # repetition time in seconds
    n_volumes: int
    time_units: str = "seconds"

    high_pass_cutoff: float | None = None
    low_pass_cutoff: float | None = None
    band_pass: tuple[float, float] | None = None

    def __post_init__(self):
        if self.tr <= 0:
            raise ValueError("TR must be positive.")

        if self.n_volumes <= 0:
            raise ValueError("Number of volumes must be positive.")


@dataclass(frozen=True)
class QualityReport:
    """
    Minimal but high-value validation and diagnostic metrics.
    """

    n_timepoints: int
    n_regressors: int

    rank_deficient: bool
    condition_number: float

    empty_regressors: list[str]
    nan_columns: list[str]

    def __post_init__(self):
        if self.n_timepoints <= 0:
            raise ValueError("Number of timepoints must be positive.")

        if self.n_regressors <= 0:
            raise ValueError("Number of regressors must be positive.")

        if self.condition_number < 0:
            raise ValueError("Condition number must be non-negative.")


@dataclass(frozen=True)
class GLMPrepResult:
    """
    Container for all GLM prep artifacts.

    This is NOT written directly to disk, but used for orchestration.
    """

    design_matrix: DesignMatrix
    timing: TimingMetadata
    quality: QualityReport
