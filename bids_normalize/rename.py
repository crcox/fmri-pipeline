from pathlib import Path

from .design import DesignMap
from .locate import find_T1w_files, find_bold_files, find_events_files
from .parse import parse_T1w_codes, parse_bold_codes, parse_events_codes
from .build import build_T1w_filename, build_bold_filename, build_events_filename

def rename_file(old: Path, new_name: str, *, dry_run: bool) -> None:
    new_path = old.with_name(new_name)

    if new_path.exists():
        raise FileExistsError(f"'{new_path}' already exists")

    if dry_run:
        print(f"[DRY-RUN] {old} -> {new_path}")
        return

    old.rename(new_path)

def rename_T1w_files(root: Path, *, dry_run: bool) -> None:
    for path in find_T1w_files(root):
        codes = parse_T1w_codes(path)
        suffix = "nii.gz" if path.name.endswith(".nii.gz") else "json"
        new_name = build_T1w_filename(codes, suffix=suffix)
        rename_file(path, new_name, dry_run = dry_run)

def rename_bold_files(root: Path, *, design: DesignMap, dry_run: bool) -> None:
    for path in find_bold_files(root):
        codes = parse_bold_codes(path)
        acq = design[codes.subject][codes.run]
        codes = codes.with_acq(acq)
        suffix = "nii.gz" if path.name.endswith(".nii.gz") else "json"
        new_name = build_bold_filename(codes, suffix=suffix)
        rename_file(path, new_name, dry_run = dry_run)

def rename_events_files(root: Path, *, design: DesignMap, dry_run: bool) -> None:
    for path in find_events_files(root):
        codes = parse_events_codes(path)
        acq = design[codes.subject][codes.run]
        codes = codes.with_acq(acq)
        suffix = "tsv"
        new_name = build_events_filename(codes, suffix=suffix)
        rename_file(path, new_name, dry_run = dry_run)
