import argparse
from pathlib import Path
from .design import load_design
from .rename import rename_T1w_files, rename_bold_files, rename_events_files

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = "Normalize BIDS filenames"
    )
    parser.add_argument(
        "dataset_root",
        type=Path,
        help="Root of BIDS dataset"
    )
    parser.add_argument(
        "--design-file",
        type=Path,
        help="File containing subject->run->acq mapping"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned renames without modifying files"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    design = load_design(args.design_file)
    rename_T1w_files(args.dataset_root, dry_run=args.dry_run)
    rename_bold_files(args.dataset_root, design=design, dry_run=args.dry_run)
    rename_events_files(args.dataset_root, design=design, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
