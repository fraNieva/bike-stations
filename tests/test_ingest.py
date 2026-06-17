"""
Tests for the /ingest endpoint and the alert engine.

Covers: valid telemetry ingestion, API key validation, data persistence,
and the core business rule — two consecutive non-charging events
must generate an alert.
"""

import pytest
from tests.conftest import make_event


VALID_PAYLOAD = {
    "station_id": "BCN-042",
    "is_charging": True,
    "voltage": 48.2,
    "amperage": 3.1,
    "gps_lat": 41.3851,
    "gps_lng": 2.1734,
}


@pytest.mark.asyncio
async def test_ingest_success(client, test_device, device_headers):
    """Valid payload with correct API key returns 201 and persists the event."""
    response = await client.post("/ingest", json=VALID_PAYLOAD, headers=device_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["station_id"] == "BCN-042"
    assert data["is_charging"] is True
    assert "received_at" in data
    assert data["alert_created"] is False


@pytest.mark.asyncio
async def test_ingest_missing_api_key(client, test_device):
    """Request without X-API-Key header returns 401."""
    response = await client.post("/ingest", json=VALID_PAYLOAD)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_invalid_api_key(client, test_device):
    """Request with wrong API key returns 401."""
    response = await client.post(
        "/ingest",
        json=VALID_PAYLOAD,
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_inactive_device(client, test_device, device_headers, db):
    """Deactivated device is rejected even with the correct API key."""
    test_device.is_active = False
    db.commit()

    response = await client.post("/ingest", json=VALID_PAYLOAD, headers=device_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ingest_unknown_station(client, test_device, device_headers):
    """station_id not registered in devices table returns 404."""
    payload = {**VALID_PAYLOAD, "station_id": "BCN-999"}
    response = await client.post("/ingest", json=payload, headers=device_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ingest_updates_last_seen_at(client, test_device, device_headers, db):
    """Successful ingest updates the device last_seen_at timestamp."""
    assert test_device.last_seen_at is None

    await client.post("/ingest", json=VALID_PAYLOAD, headers=device_headers)

    db.refresh(test_device)
    assert test_device.last_seen_at is not None


@pytest.mark.asyncio
async def test_ingest_minimal_payload(client, test_device, device_headers):
    """Payload with only required fields (no optional sensor data) is accepted."""
    response = await client.post("/ingest", json={
        "station_id": "BCN-042",
        "is_charging": False,
    }, headers=device_headers)
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# Alert engine
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_alert_on_first_non_charging(client, test_device, device_headers):
    """First non-charging event does not trigger an alert."""
    payload = {**VALID_PAYLOAD, "is_charging": False}
    response = await client.post("/ingest", json=payload, headers=device_headers)
    assert response.status_code == 201
    assert response.json()["alert_created"] is False


@pytest.mark.asyncio
async def test_alert_created_on_two_consecutive_non_charging(
    client, test_device, device_headers, db
):
    """
    Two consecutive non-charging events must create an alert.

    This is the core business rule: the system considers a station
    to have a problem after two consecutive reports without charging.
    """
    make_event(db, station_id="BCN-042", is_charging=False)

    payload = {**VALID_PAYLOAD, "is_charging": False}
    response = await client.post("/ingest", json=payload, headers=device_headers)

    assert response.status_code == 201
    assert response.json()["alert_created"] is True


@pytest.mark.asyncio
async def test_no_alert_when_charging_resets_sequence(
    client, test_device, device_headers, db
):
    """
    A charging event between two non-charging events resets the counter.

    Sequence: not charging → charging → not charging → no alert.
    """
    make_event(db, station_id="BCN-042", is_charging=False)
    make_event(db, station_id="BCN-042", is_charging=True)

    payload = {**VALID_PAYLOAD, "is_charging": False}
    response = await client.post("/ingest", json=payload, headers=device_headers)

    assert response.status_code == 201
    assert response.json()["alert_created"] is False


@pytest.mark.asyncio
async def test_no_duplicate_alert_when_already_open(
    client, test_device, device_headers, db
):
    """
    No new alert is created if there is already an open alert for this station.

    Avoids flooding the alerts table when a station stays broken.
    """
    from tests.conftest import make_alert
    make_event(db, station_id="BCN-042", is_charging=False)
    make_alert(db, station_id="BCN-042")

    payload = {**VALID_PAYLOAD, "is_charging": False}
    response = await client.post("/ingest", json=payload, headers=device_headers)

    assert response.status_code == 201
    assert response.json()["alert_created"] is False