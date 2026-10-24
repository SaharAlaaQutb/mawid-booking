import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_reports_database_status(client: Client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


@pytest.mark.django_db
def test_health_echoes_request_id(client: Client) -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-request-id"})

    assert response["X-Request-ID"] == "test-request-id"


@pytest.mark.django_db
def test_health_generates_request_id(client: Client) -> None:
    response = client.get("/health")

    assert response["X-Request-ID"]
