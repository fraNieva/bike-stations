# API Reference

Base URL (production): `https://bike-stations-production.up.railway.app`
Base URL (local): `http://localhost:8000`

Interactive docs: `{base_url}/docs`

## Authentication

### POST /auth/login

Obtain a JWT access token.

**Request**
```json
{
  "email": "mariano@bicing.com",
  "password": "yourpassword"
}
```

**Response 200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**: `401` invalid credentials or inactive user.

Use the token in subsequent requests:
```
Authorization: Bearer <access_token>
```

---

## Ingest (Arduino)

### POST /ingest

Receives telemetry from a registered Arduino device.

**Auth**: `X-API-Key: <device_api_key>` header.

**Request**
```json
{
  "station_id": "BCN-042",
  "is_charging": true,
  "voltage": 48.2,
  "amperage": 3.1,
  "gps_lat": 41.3851,
  "gps_lng": 2.1734,
  "timestamp": "2026-06-16T10:30:00Z"
}
```

All fields except `station_id` and `is_charging` are optional.

**Response 201**
```json
{
  "id": 42,
  "station_id": "BCN-042",
  "is_charging": true,
  "received_at": "2026-06-16T10:30:01.123Z",
  "alert_created": false
}
```

`alert_created: true` means two consecutive non-charging events were detected
and a new alert was created.

**Errors**: `401` missing/invalid API key, `403` inactive device, `404` unknown station_id.

---

## Stations (Dashboard)

### GET /stations

Returns the latest telemetry event for each known station.

**Auth**: JWT required.

**Response 200**
```json
[
  {
    "station_id": "BCN-042",
    "is_charging": true,
    "voltage": 48.2,
    "amperage": 3.1,
    "gps_lat": 41.3851,
    "gps_lng": 2.1734,
    "last_seen_at": "2026-06-16T10:30:01.123Z"
  }
]
```

### GET /stations/{station_id}

Returns station detail and last 10 events.

**Auth**: JWT required.

**Response 200**
```json
{
  "station_id": "BCN-042",
  "current_status": true,
  "events": [
    {
      "id": 42,
      "is_charging": true,
      "voltage": 48.2,
      "amperage": 3.1,
      "received_at": "2026-06-16T10:30:01.123Z"
    }
  ]
}
```

**Errors**: `404` no events found for that station_id.

---

## Alerts (Dashboard)

### GET /alerts

Returns all alerts. Optionally filter by status.

**Auth**: JWT required.

**Query params**: `?status=open` or `?status=resolved`

**Response 200**
```json
[
  {
    "id": 1,
    "station_id": "BCN-042",
    "created_at": "2026-06-16T10:45:00.000Z",
    "status": "open",
    "resolved_at": null,
    "resolved_by": null,
    "notes": null
  }
]
```

### PATCH /alerts/{alert_id}

Marks an alert as resolved.

**Auth**: JWT required.

**Request**
```json
{
  "notes": "Technician replaced the charging cable."
}
```

**Response 200**
```json
{
  "id": 1,
  "station_id": "BCN-042",
  "created_at": "2026-06-16T10:45:00.000Z",
  "status": "resolved",
  "resolved_at": "2026-06-16T14:00:00.000Z",
  "resolved_by": 1,
  "notes": "Technician replaced the charging cable."
}
```

**Errors**: `404` alert not found, `409` already resolved.

---

## Admin — Devices

### POST /admin/devices

Registers a new Arduino device.

**Auth**: JWT required.

**Request**
```json
{
  "station_id": "BCN-099",
  "api_key": "a-strong-random-api-key-min-32-chars"
}
```

**Response 201**
```json
{
  "id": 2,
  "station_id": "BCN-099",
  "is_active": true,
  "registered_at": "2026-06-16T09:00:00.000Z",
  "last_seen_at": null
}
```

**Errors**: `409` station_id already registered.

### GET /admin/devices

Lists all registered devices.

**Auth**: JWT required.

**Response 200**: array of device objects (same shape as POST response).

### PATCH /admin/devices/{device_id}

Activates or deactivates a device.

**Auth**: JWT required.

**Request**
```json
{ "is_active": false }
```

**Response 200**: updated device object.

**Errors**: `404` device not found.

---

## Admin — Users

### POST /admin/users

Creates a new dashboard user.

**Auth**: JWT required.

**Request**
```json
{
  "email": "operator@bicing.com",
  "password": "strongpassword456"
}
```

**Response 201**
```json
{
  "id": 2,
  "email": "operator@bicing.com",
  "is_active": true,
  "created_at": "2026-06-16T09:00:00.000Z"
}
```

**Errors**: `409` email already registered.

### GET /admin/users

Lists all users.

**Auth**: JWT required.

**Response 200**: array of user objects (same shape as POST response).

### PATCH /admin/users/{user_id}

Activates or deactivates a user.

**Auth**: JWT required.

**Request**
```json
{ "is_active": false }
```

**Response 200**: updated user object.

**Errors**: `404` user not found.

---

## Admin — Cleanup

### POST /admin/cleanup

Deletes station events older than 7 days. Alerts are never deleted.

**Auth**: JWT required.

**Response 200**
```json
{ "deleted_events": 142 }
```

---

## System

### GET /health

Health check — no authentication required.

**Response 200**
```json
{ "status": "ok" }
```