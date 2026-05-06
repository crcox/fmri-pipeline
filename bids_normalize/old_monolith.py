from pathlib import Path
from dataclasses import dataclass
from typing import Iterator, Generator, Literal, NewType, TypeIs
import argparse
import re

TaskCode = Literal["task-semjudge"]
RunCode = Literal["run-01", "run-02", "run-03", "run-04", "run-05", "run-06", "run-07", "run-08"]
AcqCode = Literal["acq-domain", "acq-danger", "acq-size", "acq-orthography"]
EchoCode = Literal["echo-1", "echo-2", "echo-3"]
SubjectCode = NewType("SubjectCode", str)
_SUBJECT_RE = re.compile(r"sub-\d{3}")

def is_run_code(value: str) -> TypeIs[RunCode]:
    return value in {"run-01", "run-02", "run-03", "run-04", "run-05", "run-06", "run-07", "run-08"}

def is_acq_code(value: str) -> TypeIs[AcqCode]:
    return value in {"acq-domain", "acq-danger", "acq-size", "acq-orthography"}

def is_echo_code(value: str) -> TypeIs[EchoCode]:
    return value in {"echo-1", "echo-2", "echo-3"}

def is_subject_code(value: str) -> TypeIs[SubjectCode]:
    return _SUBJECT_RE.fullmatch(value) is not None


@dataclass(frozen=True)
class RunAcqPair:
    run_code: RunCode
    acq_code: AcqCode

@dataclass(frozen=True)
class FileCodes:
    sub_code: SubjectCode

@dataclass(frozen=True)
class T1wCodes(FileCodes):
    pass

@dataclass(frozen=True)
class BoldCodes(FileCodes):
    task_code: TaskCode
    acq_code: AcqCode
    run_code: RunCode
    echo_code: EchoCode

@dataclass(frozen=True)
class EventsCodes(FileCodes):
    task_code: TaskCode
    acq_code: AcqCode
    run_code: RunCode

@dataclass(frozen=True)
class AnyCodes(FileCodes):
    task_code: TaskCode | None
    acq_code: AcqCode | None
    run_code: RunCode | None
    echo_code: EchoCode | None



EventsPath = NewType("EventsPath", Path)
_EVENTS_TSV_GLOB_PATTERN = "sub-001/func/sub-001_run-??_task-semjudge_acq-*_events.tsv"
_EVENTS_TSV_FILENAME_RE = re.compile(
    r"^(?P<sub_code>sub-\d{3})_(?P<sub_run>run-\d{2})_task-semjudge_(?P<acq_code>acq-[a-z]+)_events.tsv"
)

BoldPath = NewType("BoldPath", Path)
_BOLD_NII_GLOB_PATTERN = "sub-001/func/sub-001_ses-001_task-_run-??_echo-?_bold.nii.gz"
_BOLD_NII_FILENAME_RE = re.compile(
    r"^(?P<sub_code>sub-\d{3})_ses-001_task-_(?P<run_code>run-\d{2})_(?P<echo_code>echo-\d{1})_bold.nii.gz"
)
_BOLD_JSON_GLOB_PATTERN = "sub-001/func/sub-001_ses-001_task-_run-??_echo-?_bold.json"
_BOLD_JSON_FILENAME_RE = re.compile(
    r"^(?P<sub_echo>sub-\d{3})_ses-001_task-_(?P<run_code>run-\d{2})_(?P<echo_code>echo-\d{1})_bold.json"
)

T1wPath = NewType("T1wPath", Path)
_T1w_NII_GLOB_PATTERN = "sub-???/anat/sub-???_ses-001_T1w.nii.gz"
_T1w_NII_FILENAME_RE = re.compile(
    r"^(?P<sub_echo>sub-\d{3})_ses-001_T1w.nii.gz"
)
_T1w_JSON_GLOB_PATTERN = "sub-???/anat/sub-???_ses-001_T1w.json"
_T1w_JSON_FILENAME_RE = re.compile(
    r"^(?P<sub_echo>sub-\d{3})_ses-001_T1w.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename dataset files to a consistent BIDS-compliant form."
    )
    parser.add_argument(
        "dataset_root",
        type=Path,
        nargs="?",
        default=Path.cwd() / "bids",
        help="Root of the BIDS formatted dataset, containing subject directories."
    )
    return parser.parse_args()


def find_files(rootdir: Path, glob_pattern: str, re_pattern: re.Pattern) -> Iterator[Path]:
    if not rootdir.exists():
        raise FileNotFoundError(f"Directory '{rootdir}' does not exist.")

    if not rootdir.is_dir():
        raise NotADirectoryError(f"'{rootdir}' is not a directory.")

    for file in rootdir.rglob(glob_pattern):
        if file.is_file() and re_pattern.fullmatch(file.name):
            yield file
    

def find_T1w_nii(rootdir: Path) -> Iterator[T1wPath]:
    for path in find_files(rootdir, _T1w_NII_GLOB_PATTERN, _T1w_NII_FILENAME_RE):
        yield T1wPath(path)

def find_T1w_json(rootdir: Path) -> Iterator[T1wPath]:
    for path in find_files(rootdir, _T1w_JSON_GLOB_PATTERN, _T1w_JSON_FILENAME_RE):
        yield T1wPath(path)

def find_bold_nii(rootdir: Path) -> Iterator[BoldPath]:
    for path in find_files(rootdir, _BOLD_NII_GLOB_PATTERN, _BOLD_NII_FILENAME_RE):
        yield BoldPath(path)

def find_bold_json(rootdir: Path) -> Iterator[BoldPath]:
    for path in find_files(rootdir, _BOLD_JSON_GLOB_PATTERN, _BOLD_JSON_FILENAME_RE):
        yield BoldPath(path)

def find_events_tsv(rootdir: Path) -> Iterator[EventsPath]:
    for path in find_files(rootdir, _EVENTS_TSV_GLOB_PATTERN, _EVENTS_TSV_FILENAME_RE):
        yield EventsPath(path)

def extract_run_acq_pair(file: Path) -> RunAcqPair:
    match = _EVENTS_TSV_FILENAME_RE.fullmatch(file.name)
    if not match:
        raise RuntimeError(f"The file '{file.name}' does not match the pattern for an event file.")
    
    return RunAcqPair(match.group("run_code"), match.group("acq_code"))

def parse_codes_from_path(file: Path) -> AnyCodes:
    suffixes = file.suffixes
    if isinstance(BoldPath, file):
        if suffixes[0] == '.nii':
            match = re.fullmatch(_BOLD_NII_FILENAME_RE, file.name)
        elif suffixes[0] == '.json':
            match = re.fullmatch(_BOLD_JSON_FILENAME_RE, file.name)
            
        if match:
            if is_subject_code(match.group("sub_code")):
                sub_code: SubjectCode = match.group("sub_code")

            run_code = is_run_code(match.group("run_code"))
            task_code = "task-semjudge"
            acq_code = is_acq_code(match.group("acq_code"))
            echo_code = is_echo_code(match.group("echo_code"))
            new_name = f"{sub_code}_{task_code}_{acq_code}_{run_code}_{echo_code}_bold.nii.gz"

def rename_file(old_path: Path, new_name: str) -> None:
    if not old_path.exists():
        raise FileNotFoundError(f"'{old_path}' does not exist.")

    if old_path.is_dir():
        raise IsADirectoryError(f"'{old_path}' is a directory, not a file.")

    new_path = old_path.with_name(new_name)

    if new_path.exists():
        raise IOError(f"A file named '{new_path}' already exists.")

    old_path.rename(new_path)


def rename_bold_nii(rootdir: Path) -> None:
    for file in find_bold_nii(rootdir):
        match = re.search(_BOLD_NII_FILENAME_RE, file.name)
        if match:
            if is_subject_code(match.group("sub_code")):
                sub_code: SubjectCode = match.group("sub_code")

            run_code = is_run_code(match.group("run_code"))
            task_code = "task-semjudge"
            acq_code = is_acq_code(match.group("acq_code"))
            echo_code = is_echo_code(match.group("echo_code"))
            new_name = f"{sub_code}_{task_code}_{acq_code}_{run_code}_{echo_code}_bold.nii.gz"
            rename_file(file, new_name)
        

def rename_events_tsv(rootdir: Path) -> None:
    for file in find_events_tsv(rootdir):
        match = re.search(_EVENTS_FILENAME_RE, file.name)
        if match:
            sub_code,acq_code,run_code,task_code = match.groups()
            new_name = f"{sub_code}_{task_code}_{acq_code}_{run_code}_events.tsv"
            rename_file(file, new_name)
        

def rename_bold_json(rootdir: Path) -> None:
    for file in find_bold_json(rootdir):
        match = re.search(_BOLD_JSON_FILENAME_RE, file.name)
        if match:
            sub_code,run_code,echo_code = match.groups()
            new_name = f"{sub_code}_task-semjudge_{run_code}_{echo_code}_bold.json"
            rename_file(file, new_name)
        else:
            raise Exception("regex did not match")
        

if __name__ == "__main__":
    args = parse_args()

    try:
        rename_bold_json(args.dataset_root)
    except Exception as e:
        print(e)
