from pathlib import Path
import yaml

from .domain import SubjectCode, RunCode, AcqCode
from .parse import (
    parse_subject,
    parse_run,
    parse_acq,
    FilenameParseError
)

class DesignLoadError(ValueError):
    """Raised when the experiment design file is malformed"""

DesignMap = dict[SubjectCode, dict[RunCode, AcqCode]]

def load_design(path: Path) -> DesignMap:
    """
    Load and validate a subject->run->acquisition mapping.

    The design file is treates as authoritative experimental metadata.
    Any structural or semantic error is fatal.
    """
    if not path.exists():
        raise FileNotFoundError(f"Design file not found: {path}")

    if not path.is_file():
        raise DesignLoadError(f"Design path is not a file: {path}")

    with path.open('r', encoding='utf-8') as f:
        try:
            raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise DesignLoadError(f"Invalid YAML in {path}") from e

    if raw is None:
        raise DesignLoadError("Design file is empty")

    if not isinstance(raw, dict):
        raise DesignLoadError("Design file must be a mapping of subject to run mappings")

    design: DesignMap = {}

    for raw_subject, raw_runs in raw.items():
        try:
            subject = parse_subject(raw_subject)
        except FilenameParseError as e:
            raise DesignLoadError(
                f"Invalid subject code for {raw_subject!r}"
            ) from e

        if not isinstance(raw_runs, dict):
            raise DesignLoadError(
                f"Runs for {raw_subject} must be a mapping"
            )

        run_map: dict[RunCode, AcqCode] = {}

        for raw_run, raw_acq in raw_runs.items():
            try:
                run = parse_run(raw_run)
            except FilenameParseError as e:
                raise DesignLoadError(
                    f"Invalid run code for {raw_subject}: {raw_run!r}"
                ) from e

            try:
                acq = parse_acq(raw_acq)
            except FilenameParseError as e:
                raise DesignLoadError(
                    f"Invalid acq code for {raw_subject} {raw_run}: {raw_acq!r}"
                ) from e

            if run in run_map:
                raise DesignLoadError(
                    f"Duplicate run {run} for subject {subject}"
                )

            run_map[run] = acq

        if not run_map:
            raise DesignLoadError(
                f"Subject {subject} has no runs defined"
            )

        design[subject] = run_map

    if not design:
        raise DesignLoadError("Design file defines no subjects")

    return design
