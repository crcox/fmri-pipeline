from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class HRFModel(str, Enum):
    SPM = "spm"
    FSL = "fsl"


@dataclass(frozen=True)
class StimulusPolicy:
    hrf_model: HRFModel


class MotionModel(str, Enum):
    BASE = "base"
    DERIVATIVES = "derivatives"
    FULL = "full"


@dataclass(frozen=True)
class MotionPolicy:
    model: MotionModel


class ACompCorMask(str, Enum):
    WM = "wm"
    CSF = "csf"
    COMBINED = "combined"


@dataclass(frozen=True)
class ACompCorFixedModel:
    n_components: int

    def __post_init__(self):
        if self.n_components < 1:
            raise ValueError(
                f"Invalid value for n_components ({self.n_components!r}). It must be a positive integer (n > 0)."
            )


@dataclass(frozen=True)
class ACompCorVarianceModel:
    variance_explained: float

    def __post_init__(self):
        if not (0 < self.variance_explained <= 1):
            raise ValueError(
                f"Invalid value for variance_explained ({self.variance_explained!r}). It must be in greater than 0 and less than or equal to 1."
            )


ACompCorModel = ACompCorFixedModel | ACompCorVarianceModel


@dataclass(frozen=True)
class ACompCorPolicy:
    mask: ACompCorMask
    model: ACompCorModel


@dataclass(frozen=True)
class DriftCosineFromTSV:
    """
    Use cosine regressors provided in desc-confounds_timeseries.tsv.

    Includes all cosine_XX columns present in the TSV.
    """


@dataclass(frozen=True)
class DriftCosineGenerated:
    """
    Generate cosine regressors internally.

    Parameters
    ----------
    high_pass : float
        High-pass cutoff frequency (Hz), e.g., 0.008.
    """

    high_pass: float

    def __post_init__(self):
        if self.high_pass <= 0:
            raise ValueError(
                f"Invalid value for high_pass ({self.high_pass!r}). "
                "It must be a positive number (Hz > 0)."
            )


DriftModel = DriftCosineFromTSV | DriftCosineGenerated


@dataclass(frozen=True)
class DriftPolicy:
    model: DriftModel


@dataclass(frozen=True)
class TedanaClassificationSelection:
    """
    Select components based on Tedana classification.

    By default, includes all components classified as 'rejected'.
    Optionally refines selection using classification_tags.
    """

    tags_include: Sequence[str] | None = None


@dataclass(frozen=True)
class TedanaMetricSelection:
    """
    Select components using Tedana-derived metrics.
    """

    metric: str
    top_k: int | None = None
    threshold: float | None = None

    def __post_init__(self):
        if self.top_k is None and self.threshold is None:
            raise ValueError(
                "TedanaMetricSelection requires either 'top_k' or 'threshold'."
            )

        if self.top_k is not None and self.top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        if self.threshold is not None:
            # no strict bound; depends on metric scale, but enforce numeric type
            if not isinstance(self.threshold, (int, float)):
                raise ValueError("threshold must be a numeric value.")


TedanaSelection = TedanaClassificationSelection | TedanaMetricSelection


@dataclass(frozen=True)
class TedanaPolicy:
    selection: TedanaSelection


@dataclass(frozen=True)
class GLMPolicy:
    stimulus: StimulusPolicy
    motion: MotionPolicy | None
    acompcor: ACompCorPolicy | None
    drift: DriftPolicy | None
    tedana: TedanaPolicy | None
