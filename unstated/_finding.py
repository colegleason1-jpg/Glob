"""What a check returns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    """One precondition, violated by the caller's own data.

    A finding is measured, not predicted: ``observed`` holds what was found in the data
    that was passed in, so the report says "37.2% of these 2,000 values" rather than
    "this can happen".
    """

    library: str
    component: str
    assumption: str          #: what the component takes for granted
    signal: str              #: what the library does to tell you — usually "nothing"
    remedy: str              #: the concrete fix, in code
    observed: dict[str, Any] = field(default_factory=dict)
    severity: str = "high"   #: high when the wrong answer is silent and plausible

    def summary(self) -> str:
        measured = ", ".join(f"{k}={v}" for k, v in self.observed.items())
        return (
            f"[{self.severity}] {self.library}.{self.component}\n"
            f"  assumes : {self.assumption}\n"
            f"  tells you: {self.signal}\n"
            f"  measured : {measured}\n"
            f"  remedy  : {self.remedy}"
        )

    def __bool__(self) -> bool:
        return True
