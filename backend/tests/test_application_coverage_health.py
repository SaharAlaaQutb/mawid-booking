
from apps.core.application.health import HealthProbe, HealthReport, HealthService


class _FailingProbe(HealthProbe):
    name = "failing"

    def check(self) -> None:
        raise RuntimeError("boom")


class _OkProbe(HealthProbe):
    name = "ok"

    def check(self) -> None:
        return None


def test_health_report_as_dict() -> None:
    report = HealthReport(status="ok", checks={"db": "ok"})
    assert report.as_dict() == {"status": "ok", "checks": {"db": "ok"}}


def test_health_service_marks_failing_probe_as_error() -> None:
    service = HealthService(probes=[_OkProbe(), _FailingProbe()])
    report = service.check()
    assert report.status == "error"
    assert report.checks == {"ok": "ok", "failing": "error"}
