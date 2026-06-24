"""
Tests for device registration and management endpoints.

Covers: registering a new device, listing devices, activating and
deactivating a device, and duplicate station_id validation.
"""

import pytest


@pytest.mark.asyncio
async def test_register_device(client, auth_headers):
    """POST /admin/devices creates a new device and returns it."""
    response = await client.post("/admin/devices", json={
        "station_id": "BCN-099",
        "api_key": "a-strong-random-api-key",
    }, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["station_id"] == "BCN-099"
    assert data["is_active"] is True
    assert "api_key_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_station_id(client, auth_headers, test_device):
    """Registering a device with an existing station_id returns 409 Conflict."""
    response = await client.post("/admin/devices", json={
        "station_id": "BCN-042",
        "api_key": "another-key",
    }, headers=auth_headers)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_devices(client, auth_headers, test_device):
    """GET /admin/devices returns all registered devices."""
    response = await client.get("/admin/devices", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(d["station_id"] == "BCN-042" for d in data)


@pytest.mark.asyncio
async def test_deactivate_device(client, auth_headers, test_device):
    """PATCH /admin/devices/{id} with is_active=false deactivates the device."""
    response = await client.patch(
        f"/admin/devices/{test_device.id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_activate_device(client, auth_headers, test_device, db):
    """PATCH /admin/devices/{id} with is_active=true reactivates a device."""
    test_device.is_active = False
    db.commit()

    response = await client.patch(
        f"/admin/devices/{test_device.id}",
        json={"is_active": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_device_endpoints_require_authentication(client):
    """Endpoints return 403 when no JWT is provided (FastAPI default)."""
    response = await client.get("/admin/devices")
    assert response.status_code == 403