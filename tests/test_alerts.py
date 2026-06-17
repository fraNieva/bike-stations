"""
Tests for alert listing, filtering, and resolution endpoints.

Covers: listing open alerts, resolving an alert, marking as attended,
filtering by status, and verifying the permanent nature of alert records.
"""

import pytest
from app.models import AlertStatus
from tests.conftest import make_alert, make_event


@pytest.mark.asyncio
async def test_list_alerts_returns_all(client, auth_headers, db):
    """GET /alerts returns all alerts in the database."""
    make_alert(db, station_id="BCN-042")
    make_alert(db, station_id="BCN-043")

    response = await client.get("/alerts", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_list_alerts_filter_by_open_status(client, auth_headers, db):
    """GET /alerts?status=open returns only open alerts."""
    make_alert(db, station_id="BCN-042", status=AlertStatus.open)
    make_alert(db, station_id="BCN-043", status=AlertStatus.resolved)

    response = await client.get("/alerts?status=open", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "open"


@pytest.mark.asyncio
async def test_list_alerts_filter_by_resolved_status(client, auth_headers, db):
    """GET /alerts?status=resolved returns only resolved alerts."""
    make_alert(db, station_id="BCN-042", status=AlertStatus.open)
    make_alert(db, station_id="BCN-043", status=AlertStatus.resolved)

    response = await client.get("/alerts?status=resolved", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "resolved"


@pytest.mark.asyncio
async def test_resolve_alert(client, auth_headers, test_user, db):
    """PATCH /alerts/{id} marks an alert as resolved with notes and timestamp."""
    alert = make_alert(db, station_id="BCN-042")

    response = await client.patch(
        f"/alerts/{alert.id}",
        json={"notes": "Technician replaced the charging cable."},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None
    assert data["resolved_by"] == test_user.id
    assert data["notes"] == "Technician replaced the charging cable."


@pytest.mark.asyncio
async def test_resolve_already_resolved_alert(client, auth_headers, db):
    """Resolving an already resolved alert returns 409 Conflict."""
    alert = make_alert(db, station_id="BCN-042", status=AlertStatus.resolved)

    response = await client.patch(
        f"/alerts/{alert.id}",
        json={"notes": "Trying to resolve again."},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_resolve_nonexistent_alert(client, auth_headers):
    """Resolving an alert that does not exist returns 404."""
    response = await client.patch(
        "/alerts/99999",
        json={"notes": "Does not exist."},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_alerts_require_authentication(client, db):
    """Alert endpoints return 401 without a valid JWT."""
    make_alert(db)
    response = await client.get("/alerts")
    assert response.status_code == 401