import argparse
from pathlib import Path

import nibabel
import numpy as np

from glm_prep.artifacts import Regressor, TimingMetadata
from glm_prep.builders import build_acompcor, build_drift, build_motion, build_tedana
from glm_prep.confounds import (
    parse_acompcor_metadata,
    parse_confounds_timeseries,
    parse_tedana_components,
    parse_tedana_metrics,
    read_acompcor_metadata,
    read_confounds_timeseries,
    read_tedana_components,
    read_tedana_metrics,
)
from glm_prep.design import (
    BoldMetadata,
    DesignMatrixProvenance,
    build_design_matrix,
    build_stimulus_simple,
    parse_bold_metadata,
    parse_events,
    read_bold_metadata,
    read_events,
    summarize_design_matrix,
)
from glm_prep.errors import DataContractError
from glm_prep.figures import (
    save_design_matrix_correlation_figure,
    save_design_matrix_figure,
)
from glm_prep.io import save_design_matrix, save_design_matrix_summary
from glm_prep.locate import find_runs
from glm_prep.models import GLMPolicy
from glm_prep.parser import load_policy


def main():
    parser = argparse.ArgumentParser(description="GLM Prep Worker")

    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--bids-root", type=Path, required=True)
    parser.add_argument("--fmriprep-root", type=Path, required=True)
    parser.add_argument("--tedana-root", type=Path)
    parser.add_argument("--derivatives-root", type=Path, required=True)
    parser.add_argument("--subject", type=int)
    parser.add_argument("--run_ind", type=int)

    args = parser.parse_args()

    run(
        policy_path=args.policy,
        bids_root=args.bids_root,
        fmriprep_root=args.fmriprep_root,
        tedana_root=args.tedana_root,
        derivatives_root=args.derivatives_root,
        subject=args.subject,
        run_ind=args.run_ind,
    )


def run(
    policy_path: Path,
    bids_root: Path,
    fmriprep_root: Path,
    tedana_root: Path | None,
    derivatives_root: Path,
    subject: int | None = None,
    run_ind: int | None = None,
) -> None:
    derivatives_root_for_policy = derivatives_root / "glm_prep" / policy_path.stem

    policy = load_policy(policy_path)
    validate_cli_inputs(policy, tedana_root)

    validate_directory(bids_root)

    validate_directory(fmriprep_root)

    if tedana_root is not None:
        validate_directory(tedana_root)

    runs = find_runs(bids_root, fmriprep_root, tedana_root)

    if subject is not None:
        runs = [r for r in runs if r.events.key.subject == subject]

    if run_ind is not None:
        runs = [r for r in runs if r.events.key.run == run_ind]

    for run in runs:
        run_key = run.events.key

        events_raw = read_events(run.events.path)
        bold_metadata_raw = read_bold_metadata(run.bold_metadata.path)
        confounds_ts_raw = read_confounds_timeseries(run.confound_timeseries.path)
        confounds_meta_raw = read_acompcor_metadata(run.confound_metadata.path)

        tedana_components_raw = None
        if run.tedana_components:
            tedana_components_raw = read_tedana_components(run.tedana_components.path)

        tedana_metrics_raw = None
        if run.tedana_metrics:
            tedana_metrics_raw = read_tedana_metrics(run.tedana_metrics.path)

        try:
            bold_meta = parse_bold_metadata(bold_metadata_raw)
        except DataContractError as e:
            raise DataContractError(
                f"Failed while parsing BOLD metadata from {run.bold_metadata.path!s}"
            ) from e

        try:
            events = parse_events(events_raw)
        except DataContractError as e:
            raise DataContractError(
                f"Failed while parsing events from {run.events.path!s}"
            ) from e

        try:
            motion, acompcor, drift = parse_confounds_timeseries(confounds_ts_raw)
        except DataContractError as e:
            raise DataContractError(
                f"Failed while parsing confounds timeseries from "
                f"{run.confound_timeseries.path!s}"
            ) from e

        try:
            acompcor_meta = parse_acompcor_metadata(confounds_meta_raw)
        except DataContractError as e:
            raise DataContractError(
                f"Failed while parsing aCompCor metadata from "
                f"{run.confound_metadata.path!s}"
            ) from e

        tedana_components = None
        if tedana_components_raw is not None and run.tedana_components is not None:
            try:
                tedana_components = parse_tedana_components(tedana_components_raw)
            except DataContractError as e:
                raise DataContractError(
                    f"Failed while parsing tedana components from "
                    f"{run.tedana_components.path!s}"
                ) from e

        tedana_metrics = None
        if tedana_metrics_raw is not None and run.tedana_metrics is not None:
            try:
                tedana_metrics = parse_tedana_metrics(tedana_metrics_raw)
            except DataContractError as e:
                raise DataContractError(
                    f"Failed while parsing tedana metrics from "
                    f"{run.tedana_metrics.path!s}"
                ) from e

        timing_metadata = build_timing_metadata(run.bold_data.path, bold_meta)
        frame_times = build_frame_times(timing_metadata)

        stimulus_regressors = build_stimulus_simple(
            policy.stimulus, events, frame_times
        )

        drift_regressors: list[Regressor] = []
        if policy.drift is not None:
            drift_regressors = build_drift(policy.drift, drift)

        motion_regressors: list[Regressor] = []
        if policy.motion is not None:
            motion_regressors = build_motion(policy.motion, motion)

        acompcor_regressors: list[Regressor] = []
        if policy.acompcor is not None:
            acompcor_regressors = build_acompcor(
                policy.acompcor, acompcor, metadata=acompcor_meta
            )

        tedana_regressors: list[Regressor] = []
        if (
            policy.tedana is not None
            and tedana_components is not None
            and tedana_metrics is not None
        ):
            tedana_regressors = build_tedana(
                policy.tedana, tedana_components, metadata=tedana_metrics
            )

        provenance = DesignMatrixProvenance.from_runfiles(run, policy=policy_path)

        design_matrix = build_design_matrix(
            stimulus=stimulus_regressors,
            drift=drift_regressors,
            motion=motion_regressors,
            acompcor=acompcor_regressors,
            tedana=tedana_regressors,
            provenance=provenance,
        )

        save_design_matrix(
            design_matrix, root=derivatives_root_for_policy, run_key=run_key
        )

        summary = summarize_design_matrix(design_matrix)

        save_design_matrix_summary(
            summary, root=derivatives_root_for_policy, run_key=run_key
        )

        save_design_matrix_figure(
            design_matrix, root=derivatives_root_for_policy, run_key=run_key
        )

        save_design_matrix_correlation_figure(
            design_matrix, root=derivatives_root_for_policy, run_key=run_key
        )


if __name__ == "__main__":
    main()


def validate_cli_inputs(
    policy: GLMPolicy,
    tedana_root: Path | None,
) -> None:

    if policy.tedana is not None and tedana_root is None:
        raise RuntimeError(
            "Tedana policy specified but --tedana-root was not provided."
        )


def validate_directory(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_dir():
        raise NotADirectoryError(path)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_timing_metadata(
    bold_file: Path, bold_metadata: BoldMetadata
) -> TimingMetadata:
    img = nibabel.load(bold_file)

    if len(img.shape) != 4:
        raise DataContractError(f"Expected 4D BOLD image. Got shape {img.shape}")

    return TimingMetadata(
        tr=bold_metadata.repetition_time,
        n_volumes=img.shape[3],
    )


def build_frame_times(timing_metadata: TimingMetadata) -> np.ndarray:

    n_volumes = timing_metadata.n_volumes
    tr = timing_metadata.tr

    return np.arange(n_volumes) * tr
