from glm_prep.models import (
    DriftCosineFromTSV,
    DriftCosineGenerated,
    GLMPolicy
)

def _validate_acompcor_drift(policy: GLMPolicy) -> None:
    if policy.acompcor is not None:
        if policy.drift is None:
            raise ValueError(
                "Invalid policy:\n\n"
                "aCompCor regressors were requested, but no drift model was specified.\n\n"
                "Because fMRIPrep computes aCompCor on high-pass filtered data,\n"
                "corresponding cosine regressors must be included.\n\n"
                "Add:\n\n"
                "drift:\n"
                "  cosine: {}\n"
            )
    
        if not isinstance(policy.drift.model, DriftCosineFromTSV):
            raise ValueError(
                "Invalid policy:\n\n"
                "aCompCor regressors require cosine drift terms from "
                "desc-confounds_timeseries.tsv.\n\n"
                "Generated cosine bases are not compatible with precomputed aCompCor components.\n\n"
                "Use:\n\n"
                "drift:\n"
                "  cosine: {}\n"
            )


def _validate_drift_consistency(policy: GLMPolicy) -> None:
    if policy.drift is None:
        return

    model = policy.drift.model

    # No-op for now, but placeholder for future rules
    if isinstance(model, DriftCosineGenerated):
        pass


def _validate_tedana_constraints(policy: GLMPolicy) -> None:
    # No required cross-policy constraints for now
    pass


def validate_glm_policy(policy: GLMPolicy) -> None:
    _validate_acompcor_drift(policy)
    _validate_drift_consistency(policy)
    _validate_tedana_constraints(policy)




