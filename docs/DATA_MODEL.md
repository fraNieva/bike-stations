# Data Model

## Tables

### users

Dashboard administrators who can log in and manage the system.

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| email | String | Unique, indexed |
| password_hash | String | bcrypt hash — never store plain text |
| is_active | Boolean | False blocks login |
| created_at | DateTime (tz) | Set by database on insert |

### devices

Registered Arduino boards. One device per station.

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| station_id | String | Unique — matches Nextbike station ID (e.g. "BCN-042") |
| api_key_hash | String | bcrypt hash of the key flashed into the board |
| is_active | Boolean | False blocks ingest requests |
| registered_at | DateTime (tz) | Set by database on insert |
| last_seen_at | DateTime (tz) | Updated on every successful ingest |

### station_events

Raw telemetry received from each device. Deleted after 7 days.

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| station_id | String | Indexed — logical FK to devices.station_id |
| is_charging | Boolean | Core sensor reading |
| voltage | Float | Optional — volts |
| amperage | Float | Optional — amps |
| gps_lat | Float | Optional |
| gps_lng | Float | Optional |
| received_at | DateTime (tz) | Set by database on insert |

**Retention**: deleted by `POST /admin/cleanup` (records older than 7 days).

### alerts

Charging failure incidents. Never deleted — permanent historical record.

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| station_id | String | Indexed |
| created_at | DateTime (tz) | Set by database on insert |
| status | Enum | `open` or `resolved` |
| resolved_at | DateTime (tz) | Set when resolved |
| resolved_by | Integer | FK → users.id |
| notes | Text | Optional notes from the operator |

## Relationships

```
users ──────────────────── alerts
(resolved_by FK)

devices ─── station_id ─── station_events
            (logical)
devices ─── station_id ─── alerts
            (logical)
```

Note: `station_id` is a string foreign key by convention, not a database-level FK constraint.
This allows events and alerts to exist even if the device record is later modified.

## Alert Lifecycle

```
[open] ──── PATCH /alerts/{id} ──── [resolved]
```

Once resolved, an alert cannot be re-opened. A new alert will be created
if the station continues to fail after the previous one was resolved.

## Migrations

All schema changes are managed with Alembic.

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after changing models.py
alembic revision --autogenerate -m "describe the change"

# Roll back one migration
alembic downgrade -1
```

Never use `Base.metadata.create_all()` in production — always use Alembic.