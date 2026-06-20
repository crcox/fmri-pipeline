import pandas as pd

from typing import Any
from dataclasses import dataclass
from glm_prep.errors import DataContractError
from glm_prep.models import HRFModel
from glm_prep.artifacts import Regressor, RegressorInfo 
from nilearn.glm.first_level import make_first_level_design_matrix

_REQUIRED_COLUMNS: tuple[str, ...] = (
    "onset",
    "duration",
    "stimulus"
)

@dataclass(frozen=True)
class Event:
    onset: float
    duration: float
    stimulus: str


def _parse_event(row: dict[str, Any]) -> Event:
    try:
        onset = float(row["onset"])
        duration = float(row["duration"])
        stimulus = str(row["stimulus"])
    except (TypeError, ValueError) as e:
        raise DataContractError("Invalid event row") from e

    if onset < 0:
        raise DataContractError(f"Invalid onset: {onset!r}")

    if duration < 0:
        raise DataContractError(f"Invalid duration: {duration!r}")

    if not stimulus:
        raise DataContractError("Empty stimulus label")

    return Event(onset=onset, duration=duration, stimulus=stimulus)

def parse_events(df: pd.DataFrame) -> list[Event]:
    missing = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise DataContractError(
            "Missing required event columns:\n"
            + "\n".join(f"  - {col!r}" for col in missing)
        )

    events: list[Event] = []

    rows = df.to_dict(orient="records")

    for row in rows:
        events.append(_parse_event(row))

    return events


def build_stimulus_simple(policy: DesignPolicy, events: list[Event], frame_times: np.ndarray, hrf_model: HRFModel) -> list[Regressor]:
    events_df = pd.DataFrame({
        "onset": [e.onset for e in events],
        "duration": [e.duration for e in events],
        "trial_type": [e.stimulus for e in events]
    })

    design_matrix = make_first_level_design_matrix(
        frame_times,
        events_df,
        hrf_model=hrf_model,
        drift=None
    )
    if not isinstance(design_matrix, pd.DataFrame):
        DataContractError(f"Expected nilearn.glm.make_first_level_design_matrix to return a pd.DataFrame. Received: {type(design_matrix)!r}")

    stimulus_names = sorted({e.stimulus for e in events}) 

    stimulus_columns = [
        col for col in design_matrix.columns
        if col in stimulus_names
    ]

    regressors: list[Regressor] = []

    for col in stimulus_columns:
        values = ensure_1d(design_matrix[col].to_numpy(dtype=np.float64))

        regressors.append(
            Regressor(
                values=values,
                info=RegressorInfo(
                    name=col,
                    source=RegressorSource.STIMULUS,
                    column=-1,
                    metadata={
                        "stimulus": col,
                        "hrf_model": hrf_model,
                    },
                ),
            )
        )
