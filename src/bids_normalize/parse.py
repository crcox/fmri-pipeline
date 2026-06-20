from pathlib import Path
from typing import TypeIs
import re

from .domain import SubjectCode, TaskCode, AcqCode, RunCode, EchoCode, T1wCodes, BoldCodes, EventsCodes

_SUBJECT_RE = re.compile(r"^sub-\d{3}$")
_T1W_FILENAME_RE = re.compile(
    r"^(?P<sub>sub-\d{3})_ses-001_T1w\.(nii\.gz|json)$"
)
_BOLD_FILENAME_RE = re.compile(
    r"^(?P<sub>sub-\d{3})_ses-001_task-_(?P<run>run-\d{2})_(?P<echo>echo-\d{1})_bold\.(nii\.gz|json)$"
)
_EVENTS_FILENAME_RE = re.compile(
    r"^(?P<sub>sub-\d{3})_(?P<run>run-\d{2})_task-semjudge_(?P<acq>acq-[a-z]+)\.tsv$"
)

_TASK_CODES: set[str] = {
    "task-semjudge"
}

_ACQ_CODES: set[str] = {
    "acq-domain",
    "acq-danger",
    "acq-size",
    "acq-orthography"
}

_RUN_CODES: set[str] = {
    "run-01",
    "run-02",
    "run-03",
    "run-04",
    "run-05",
    "run-06",
    "run-07",
    "run-08"
}

_ECHO_CODES: set[str] = {
    "echo-1",
    "echo-2",
    "echo-3"
}

class FilenameParseError(ValueError):
    pass

def parse_subject(value: str) -> SubjectCode:
    if not _SUBJECT_RE.fullmatch(value):
        raise FilenameParseError(f"Invalid subject code: {value!r}")

    return SubjectCode(value)

def is_task_code(value: str) -> TypeIs[TaskCode]:
    return value in _TASK_CODES

def parse_task(value: str) -> TaskCode:
    if not is_task_code(value):
        raise FilenameParseError(f"Invalid task code: {value!r}")
    return value

def is_acq_code(value: str) -> TypeIs[AcqCode]:
    return value in _ACQ_CODES

def parse_acq(value: str) -> AcqCode:
    if not is_acq_code(value):
        raise FilenameParseError(f"Invalid acq code: {value!r}")
    return value

def is_run_code(value: str) -> TypeIs[RunCode]:
    return value in _RUN_CODES

def parse_run(value: str) -> RunCode:
    if not is_run_code(value):
        raise FilenameParseError(f"Invalid run code: {value!r}")
    return value

def is_echo_code(value: str) -> TypeIs[EchoCode]:
    return value in _ECHO_CODES

def parse_echo(value: str) -> EchoCode:
    if not is_echo_code(value):
        raise FilenameParseError(f"Invalid echo code: {value!r}")
    return value

def parse_T1w_codes(path: Path) -> T1wCodes:
    match = _T1W_FILENAME_RE.fullmatch(path.name)
    if not match:
        raise FilenameParseError(f"Not a T1w file: {path.name!r}")

    subject = parse_subject(match.group("sub"))
    return T1wCodes(subject = subject)


def parse_bold_codes(path: Path) -> BoldCodes:
    match = _BOLD_FILENAME_RE.fullmatch(path.name)
    if not match:
        raise FilenameParseError(f"Not a bold file: {path.name!r}")

    subject = parse_subject(match.group("sub"))
    task = parse_task("task-semjudge")
    run = parse_run(match.group("run"))
    echo = parse_echo(match.group("echo"))
    return BoldCodes(
        subject = subject,
        task = task,
        acq = None,
        run = run,
        echo = echo
    )

def parse_events_codes(path: Path) -> EventsCodes:
    match = _EVENTS_FILENAME_RE.fullmatch(path.name)
    if not match:
        raise FilenameParseError(f"Not a T1w file: {path.name}")

    subject = parse_subject(match.group("sub"))
    task = parse_task("task-semjudge")
    run = parse_run(match.group("run"))
    return EventsCodes(
        subject = subject,
        task = task,
        acq = None,
        run = run
    )
