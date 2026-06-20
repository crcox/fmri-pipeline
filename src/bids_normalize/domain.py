from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import NewType, Literal

TaskCode = Literal["task-semjudge"]
RunCode = Literal["run-01", "run-02", "run-03", "run-04", "run-05", "run-06", "run-07", "run-08"]
AcqCode = Literal["acq-domain", "acq-danger", "acq-size", "acq-orthography"]
EchoCode = Literal["echo-1", "echo-2", "echo-3"]
SubjectCode = NewType("SubjectCode", str)

T1wPath = NewType("T1wPath", Path)
BoldPath = NewType("BoldPath", Path)
EventsPath = NewType("EventsPath", Path)

@dataclass(frozen=True)
class T1wCodes:
    subject: SubjectCode

@dataclass(frozen=True)
class BoldCodes:
    subject: SubjectCode
    task: TaskCode
    acq: AcqCode | None
    run: RunCode
    echo: EchoCode

    def with_acq(self, acq: AcqCode) -> BoldCodes:
        if self.acq is not None:
            raise ValueError("acq already set")
        return replace(self, acq=acq)

@dataclass(frozen=True)
class EventsCodes:
    subject: SubjectCode
    task: TaskCode
    acq: AcqCode | None
    run: RunCode

    def with_acq(self, acq: AcqCode) -> EventsCodes:
        if self.acq is not None:
            raise ValueError("acq already set")
        return replace(self, acq=acq)


