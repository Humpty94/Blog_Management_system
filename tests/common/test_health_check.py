import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_check_endpoint_returns_ok():
    client = APIClient()
    response = client.get("/api/v1/health/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ok"
    assert response.data["database"] == "connected"
    assert "X-Request-ID" in response.headers


def test_health_check_endpoint_returns_503_on_db_error(monkeypatch):
    from unittest.mock import MagicMock

    from django.db import connection

    mock_cursor = MagicMock(side_effect=Exception("Database connection refused"))
    monkeypatch.setattr(connection, "cursor", mock_cursor)

    client = APIClient()
    response = client.get("/api/v1/health/")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data["status"] == "unhealthy"
    assert response.data["database"] == "disconnected"
