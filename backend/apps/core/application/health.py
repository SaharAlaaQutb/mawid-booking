from dataclasses import dataclass, field
from typing import Protocol


class HealthProbe(Protocol):
    name: str

    def check(self) -> None:
        """Raise an exception when the dependency is unavailable."""
        ...


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {"status": self.status, "checks": self.checks}


class HealthService:
    def __init__(self, probes: list[HealthProbe]) -> None:
        self._probes = probes

    def check(self) -> HealthReport:
        checks: dict[str, str] = {}
        healthy = True

        for probe in self._probes:
            try:
                probe.check()
            except Exception:
                checks[probe.name] = "error"
                healthy = False
            else:
                checks[probe.name] = "ok"

        return HealthReport(status="ok" if healthy else "error", checks=checks)
