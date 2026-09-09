from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path


class TaskCode(StrEnum):
    SEMJUDGE = "semjudge"


class AcqCode(StrEnum):
    DOMAIN = "domain"
    DANGER = "danger"
    SIZE = "size"
    ORTHOGRAPHY = "orthography"


@dataclass(frozen=True)
class RunKey:
    subject: int
    run: int


@dataclass(frozen=True)
class LocatedFile:
    key: RunKey
    path: Path


@dataclass(frozen=True)
class BoldCodes:
    subject: int
    run: int
    echo: int
    task: TaskCode
    acq: AcqCode | None

    def with_acq(self, acq: AcqCode) -> BoldCodes:
        if self.acq is not None:
            raise ValueError("acq already set")
        return replace(self, acq=acq)
