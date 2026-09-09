from pathlib import Path

from glm_prep.cli import run

run(
    policy_path=Path("policies/glm_prep/task-baseline-v1.yaml"),
    bids_root=Path("bids"),
    fmriprep_root=Path("derivatives/fmriprep"),
    tedana_root=Path("derivatives/tedana"),
    derivatives_root=Path("derivatives"),
)
