import re
from dataclasses import dataclass
from pathlib import Path

from glm_prep.domain import LocatedFile, RunKey
from glm_prep.errors import DataContractError

# derivatives/tedana
_TEDANA_COMPONENTS_GLOB = "sub-???/run-??/sub-???_run-??_desc-ICA_mixing.tsv"
_TEDANA_COMPONENTS_FILENAME_RE = re.compile(
    r"^sub-(?P<subject>\d{3})"
    r"_run-(?P<run>\d{2})"
    r"_desc-(?P<desc>ICA_mixing)"
    r"\.tsv$"
)

_TEDANA_METRICS_GLOB = "sub-???/run-??/sub-???_run-??_desc-tedana_metrics.tsv"
_TEDANA_METRICS_FILENAME_RE = re.compile(
    r"^sub-(?P<subject>\d{3})"
    r"_run-(?P<run>\d{2})"
    r"_desc-(?P<desc>tedana_metrics)"
    r"\.tsv$"
)


# derivatives/fmriprep
_BOLD_T1w_NII_GLOB = (
    "sub-???_task-semjudge_acq-*_run-??_space-T1w_desc-preproc_bold.nii.gz"
)
_BOLD_T1w_NII_FILENAME_RE = re.compile(
    r"^sub-(?P<subject>\d{3})"
    r"_task-(?P<task>semjudge)"
    r"_acq-(?P<acq>[a-z]+)"
    r"_run-(?P<run>\d{2})"
    r"_space-(?P<space>T1w)"
    r"_desc-(?P<desc>preproc_bold)"
    r"\.nii.gz$"
)

_BOLD_T1w_JSON_GLOB = (
    "sub-???_task-semjudge_acq-*_run-??_space-T1w_desc-preproc_bold.json"
)
_BOLD_T1w_JSON_FILENAME_RE = re.compile(
    r"^sub-(?P<subject>\d{3})"
    r"_task-(?P<task>semjudge)"
    r"_acq-(?P<acq>[a-z]+)"
    r"_run-(?P<run>\d{2})"
    r"_space-(?P<space>T1w)"
    r"_desc-(?P<desc>preproc_bold)"
    r"\.json$"
)

_BOLD_MNI_GLOB = "sub-???_task-semjudge_acq-*_run-??_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz"
_BOLD_MNI_FILENAME_RE = re.compile(
    r"^sub-(?P<subject>\d{3})"
    r"_task-(?P<task>semjudge)"
    r"_acq-(?P<acq>[a-z]+)"
    r"_run-(?P<run>\d{2})"
    r"_space-(?P<space>MNI152NLin2009cAsym)"
    r"_desc-(?P<desc>preproc_bold)"
    r"\.nii.gz$"
)

_CONFOUNDS_TSV_GLOB = (
    "sub-???/func/sub-???_task-semjudge_acq-*_run-??_desc-confounds_timeseries.tsv"
)
_CONFOUNDS_TSV_FILENAME_RE = re.compile(
    r"^sub-(?P<subject>\d{3})"
    r"_task-(?P<task>semjudge)"
    r"_acq-(?P<acq>[a-z]+)"
    r"_run-(?P<run>\d{2})"
    r"_desc-(?P<desc>confounds_timeseries)"
    r"\.tsv$"
)

_CONFOUNDS_JSON_GLOB = (
    "sub-???/func/sub-???_task-semjudge_acq-*_run-??_desc-confounds_timeseries.json"
)
_CONFOUNDS_JSON_FILENAME_RE = re.compile(
    r"^sub-(?P<subject>\d{3})"
    r"_task-(?P<task>semjudge)"
    r"_acq-(?P<acq>[a-z]+)"
    r"_run-(?P<run>\d{2})"
    r"_desc-(?P<desc>confounds_timeseries)"
    r"\.json$"
)

# bids/
_EVENTS_GLOB = "sub-???/func/sub-???_task-semjudge_acq-*_run-??_events.tsv"
_EVENTS_FILENAME_RE = re.compile(
    r"^sub-(?P<subject>\d{3})"
    r"_task-(?P<task>semjudge)"
    r"_acq-(?P<acq>[a-z]+)"
    r"_run-(?P<run>\d{2})"
    r"_(?P<desc>events)"
    r"\.tsv$"
)


def validate_directory(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path!r} does not exist")

    if not path.is_dir():
        raise NotADirectoryError(f"{path!r} is not a directory")


def build_run_key(match: re.Match[str]) -> RunKey:
    return RunKey(
        subject=int(match["subject"]),
        run=int(match["run"]),
    )


def _locate_files(
    root: Path, glob_filter: str, re_pattern: re.Pattern[str]
) -> list[LocatedFile]:
    located_files: list[LocatedFile] = []

    globbed_files = root.rglob(glob_filter)
    if not globbed_files:
        raise FileNotFoundError(
            f"No confound timeseries files matching {glob_filter!r} under {root!r}"
        )

    for path in globbed_files:
        match = re_pattern.fullmatch(path.name)

        if path.is_file() and match:
            located_files.append(
                LocatedFile(
                    key=build_run_key(match),
                    path=path,
                )
            )

    if not located_files:
        raise FileNotFoundError(
            f"No confound timeseries files matching "
            f"{re_pattern.pattern!r} "
            f"under {root!r}"
        )

    return sorted(
        located_files,
        key=lambda x: x.key.run,
    )


def _locate_confound_timeseries(root: Path) -> list[LocatedFile]:
    return _locate_files(
        root=root,
        glob_filter=_CONFOUNDS_TSV_GLOB,
        re_pattern=_CONFOUNDS_TSV_FILENAME_RE,
    )


def _locate_confound_metadata(root: Path) -> list[LocatedFile]:
    return _locate_files(
        root=root,
        glob_filter=_CONFOUNDS_JSON_GLOB,
        re_pattern=_CONFOUNDS_JSON_FILENAME_RE,
    )


def _locate_preproc_bold_data(root: Path) -> list[LocatedFile]:
    return _locate_files(
        root=root,
        glob_filter=_BOLD_T1w_NII_GLOB,
        re_pattern=_BOLD_T1w_NII_FILENAME_RE,
    )


def _locate_preproc_bold_metadata(root: Path) -> list[LocatedFile]:
    return _locate_files(
        root=root,
        glob_filter=_BOLD_T1w_JSON_GLOB,
        re_pattern=_BOLD_T1w_JSON_FILENAME_RE,
    )


def _locate_events(root: Path) -> list[LocatedFile]:
    return _locate_files(
        root=root,
        glob_filter=_EVENTS_GLOB,
        re_pattern=_EVENTS_FILENAME_RE,
    )


def _locate_tedana_components(root: Path) -> list[LocatedFile]:
    return _locate_files(
        root=root,
        glob_filter=_TEDANA_COMPONENTS_GLOB,
        re_pattern=_TEDANA_COMPONENTS_FILENAME_RE,
    )


def _locate_tedana_metrics(root: Path) -> list[LocatedFile]:
    return _locate_files(
        root=root,
        glob_filter=_TEDANA_METRICS_GLOB,
        re_pattern=_TEDANA_METRICS_FILENAME_RE,
    )


@dataclass(frozen=True)
class RunFiles:
    events: LocatedFile
    bold_data: LocatedFile
    bold_metadata: LocatedFile
    confound_timeseries: LocatedFile
    confound_metadata: LocatedFile
    tedana_components: LocatedFile | None
    tedana_metrics: LocatedFile | None


def format_run_keys(keys: set[RunKey]) -> str:
    return "\n".join(
        f"    - sub-{k.subject:03d} run-{k.run:02d}"
        for k in sorted(keys, key=lambda x: x.run)
    )


def compare_run_keys(
    reference_name: str,
    reference: set[RunKey],
    name: str,
    observed: set[RunKey],
) -> str | None:
    if reference == observed:
        return None

    missing = reference - observed
    extra = observed - reference

    messages: list[str] = [f"{name} does not match {reference_name}:"]

    if missing:
        messages.append("  Missing:\n" + format_run_keys(missing))

    if extra:
        messages.append("  Extra:\n" + format_run_keys(extra))

    return "\n".join(messages)


def validate_run_discovery(
    event_keys: set[RunKey],
    bold_data_keys: set[RunKey],
    bold_metadata_keys: set[RunKey],
    conf_keys: set[RunKey],
    meta_keys: set[RunKey],
    tedana_components_keys: set[RunKey] | None,
    tedana_metrics_keys: set[RunKey] | None,
):
    diagnostics: list[str] = []

    for name, keys in [
        ("bold_data", bold_data_keys),
        ("bold_metadata", bold_metadata_keys),
        ("confounds", conf_keys),
        ("metadata", meta_keys),
    ]:
        msg = compare_run_keys(
            reference_name="events",
            reference=event_keys,
            name=name,
            observed=keys,
        )

        if msg:
            diagnostics.append(msg)

    if tedana_components_keys:
        msg = compare_run_keys(
            reference_name="events",
            reference=event_keys,
            name="tedana",
            observed=tedana_components_keys,
        )

        if msg:
            diagnostics.append(msg)

    if tedana_metrics_keys:
        msg = compare_run_keys(
            reference_name="events",
            reference=event_keys,
            name="tedana",
            observed=tedana_metrics_keys,
        )

        if msg:
            diagnostics.append(msg)

    if diagnostics:
        raise DataContractError(
            "Run discovery produced inconsistent run keys:\n\n"
            + "\n\n".join(diagnostics)
        )


def find_runs(
    bids_dir: Path, func_dir: Path, tedana_dir: Path | None
) -> list[RunFiles]:
    validate_directory(bids_dir)
    events_files = _locate_events(bids_dir)

    validate_directory(func_dir)
    preproc_bold_data_files = _locate_preproc_bold_data(func_dir)
    preproc_bold_metadata_files = _locate_preproc_bold_metadata(func_dir)
    confound_timeseries_files = _locate_confound_timeseries(func_dir)
    confound_metadata_files = _locate_confound_metadata(func_dir)
    tedana_components_files: list[LocatedFile] | None = None
    tedana_metrics_files: list[LocatedFile] | None = None

    if tedana_dir:
        validate_directory(tedana_dir)
        tedana_components_files = _locate_tedana_components(tedana_dir)
        tedana_metrics_files = _locate_tedana_metrics(tedana_dir)

    event_by_key = {x.key: x for x in events_files}
    bold_data_by_key = {x.key: x for x in preproc_bold_data_files}
    bold_metadata_by_key = {x.key: x for x in preproc_bold_metadata_files}
    confound_by_key = {x.key: x for x in confound_timeseries_files}
    meta_by_key = {x.key: x for x in confound_metadata_files}
    tedana_components_by_key: dict[RunKey, LocatedFile] | None = None
    tedana_metrics_by_key: dict[RunKey, LocatedFile] | None = None

    if tedana_components_files:
        tedana_components_by_key = {x.key: x for x in tedana_components_files}

    if tedana_metrics_files:
        tedana_metrics_by_key = {x.key: x for x in tedana_metrics_files}

    validate_run_discovery(
        set(event_by_key.keys()),
        set(bold_data_by_key.keys()),
        set(bold_metadata_by_key.keys()),
        set(confound_by_key.keys()),
        set(meta_by_key.keys()),
        set(tedana_components_by_key.keys())
        if tedana_components_by_key is not None
        else None,
        set(tedana_metrics_by_key.keys())
        if tedana_metrics_by_key is not None
        else None,
    )

    runs: list[RunFiles] = []
    keys = sorted(event_by_key.keys(), key=lambda x: x.run)
    for key in keys:
        runs.append(
            RunFiles(
                events=event_by_key[key],
                bold_data=bold_data_by_key[key],
                bold_metadata=bold_metadata_by_key[key],
                confound_timeseries=confound_by_key[key],
                confound_metadata=meta_by_key[key],
                tedana_components=tedana_components_by_key[key]
                if tedana_components_by_key is not None
                else None,
                tedana_metrics=tedana_metrics_by_key[key]
                if tedana_metrics_by_key is not None
                else None,
            )
        )

    return runs
