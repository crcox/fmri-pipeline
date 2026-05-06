from .domain import T1wCodes, BoldCodes, EventsCodes

def build_T1w_filename(codes: T1wCodes, *, suffix: str) -> str:
    return f"{codes.subject}_T1w.{suffix}"

def build_bold_filename(codes: BoldCodes, *, suffix: str) -> str:
    return (
        f"{codes.subject}_"
        f"{codes.task}_"
        f"{codes.acq}_"
        f"{codes.run}_"
        f"{codes.echo}_"
        f"bold.{suffix}"
    )

def build_events_filename(codes: EventsCodes, *, suffix: str) -> str:
    return (
        f"{codes.subject}_"
        f"{codes.task}_"
        f"{codes.acq}_"
        f"{codes.run}_"
        f"events.{suffix}"
    )
