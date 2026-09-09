import re
from collections.abc import Iterator
from pathlib import Path

from .domain import BoldPath, EventsPath, T1wPath

_T1W_GLOB = "sub-???/anat/sub-???_ses-001_T1w.*"
_T1W_FILENAME_RE = re.compile(r"^(sub-\d{3})_ses-001_T1w\.(nii\.gz|json)$")
_BOLD_GLOB = "sub-???/func/sub-???_ses-001_task-_run-??_echo-?_bold.*"
_BOLD_FILENAME_RE = re.compile(
    r"^(sub-\d{3})_ses-001_task-_(run-\d{2})_(echo-\d{1})_bold\.(nii\.gz|json)$"
)
_EVENTS_GLOB = "sub-???/func/sub-???_run-??_task-semjudge_acq-*.tsv"
_EVENTS_FILENAME_RE = re.compile(
    r"^(sub-\d{3})_(run-\d{2})_task-semjudge_(acq-[a-z]+)\.tsv$"
)


def find_T1w_files(root: Path) -> Iterator[T1wPath]:
    if not root.exists():
        raise FileNotFoundError(f"'{root}' does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"'{root}' is not a directory")

    found = False
    for path in root.rglob(_T1W_GLOB):
        if path.is_file() and _T1W_FILENAME_RE.fullmatch(path.name):
            found = True
            yield (T1wPath(path))

    if not found:
        raise FileNotFoundError(
            f"No T1w files matching {_T1W_FILENAME_RE.pattern!r} under {root!r}"
        )


def find_bold_files(root: Path) -> Iterator[BoldPath]:
    if not root.exists():
        raise FileNotFoundError(f"'{root}' does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"'{root}' is not a directory")

    found = False
    for path in root.rglob(_BOLD_GLOB):
        if path.is_file() and _BOLD_FILENAME_RE.fullmatch(path.name):
            found = True
            yield (BoldPath(path))

    if not found:
        raise FileNotFoundError(
            f"No T1w files matching {_T1W_FILENAME_RE.pattern!r} under {root!r}"
        )


def find_events_files(root: Path) -> Iterator[EventsPath]:
    if not root.exists():
        raise FileNotFoundError(f"'{root}' does not exist")
    if not root.is_dir():
        raise NotADirectoryError(f"'{root}' is not a directory")

    found = False
    for path in root.rglob(_EVENTS_GLOB):
        if path.is_file() and _EVENTS_FILENAME_RE.fullmatch(path.name):
            found = True
            yield (EventsPath(path))

    if not found:
        raise FileNotFoundError(
            f"No T1w files matching {_T1W_FILENAME_RE.pattern!r} under {root!r}"
        )
