"""
Tests for the dashboard station endpoints.

Covers: listing all stations with their current status, retrieving
a single station's detail and event history, and handling stations
with no recent data.
"""

import pytest
from tests.conftest import make_event


@pytest.mark.asyncio
async def test_list_stations_empty(client, auth_headers):
    """GET /stations returns an empty list when no events exist."""
    response = await client.get("/stations", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_stations_shows_current_status(client, auth_headers, db):
    """GET /stations returns the latest charging status for each station."""
    make_event(db, station_id="BCN-042", is_charging=False)
    make_event(db, station_id="BCN-042", is_charging=True)
    make_event(db, station_id="BCN-043", is_charging=False)

    response = await client.get("/stations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    bcn_042 = next(s for s in data if s["station_id"] == "BCN-042")
    bcn_043 = next(s for s in data if s["station_id"] == "BCN-043")

    assert bcn_042["is_charging"] is True
    assert bcn_043["is_charging"] is False


@pytest.mark.asyncio
async def test_get_station_detail(client, auth_headers, db):
    """GET /stations/{id} returns the last 10 events for the station."""
    for i in range(12):
        make_event(db, station_id="BCN-042", is_charging=i % 2 == 0)

    response = await client.get("/stations/BCN-042", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 10


@pytest.mark.asyncio
async def test_get_station_not_found(client, auth_headers):
    """GET /stations/{id} returns 404 for an unknown station."""
    response = await client.get("/stations/BCN-999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_station_endpoints_require_authentication(client):
    """Endpoints return 403 when no JWT is provided (FastAPI default)."""
    response = await client.get("/stations")
    assert response.status_code == 403