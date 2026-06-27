# Architecture

## System Overview

```
[Arduino + SIM]          [Railway Cloud]                    [Future]
LilyGO T-A7670E-S3  →   FastAPI + PostgreSQL   →   React/Next.js Dashboard
(4G POST every 10-15m)   (bike-stations API)         (maintenance team)
```

## Layers

### Layer 1 — Device (not managed by this repo)

LilyGO T-A7670E-S3 board installed at each station:
- ESP32-S3 microcontroller
- A7670E integrated 4G modem
- Current sensor measuring the station's charging lines
- Sends a JSON POST to `/ingest` every 10–15 minutes continuously
- Has local memory to buffer events if 4G signal is lost and resend on reconnection

### Layer 2 — API (this repo)

FastAPI application running in a Docker container on Railway.

Responsibilities:
- Validate device identity via API key (bcrypt hash comparison)
- Persist telemetry events to PostgreSQL
- Run the alert engine after each non-charging event
- Expose data to the dashboard via JWT-protected endpoints
- Clean up events older than 7 days (manual endpoint + automatic daily scheduler)

### Layer 3 — Database

PostgreSQL 15 managed by Railway.

Two data lifecycles:
- `station_events` — raw telemetry, deleted after 7 days
- `alerts` — incident records, kept permanently

### Layer 4 — Dashboard (not yet built)

Planned React/Next.js frontend that will consume the REST API.
Will show station status in real time and allow alert management.

## Security Model

### Device authentication (Arduino → API)
- Each device has a unique API key hardcoded at flash time
- The key is stored as a bcrypt hash in the `devices` table
- Sent in the `X-API-Key` header on every request
- Deactivating a device in the database immediately blocks it

### User authentication (Dashboard → API)
- Email + password login returns a JWT (8 hour expiry)
- JWT sent as `Authorization: Bearer <token>` on protected requests
- Passwords stored as bcrypt hashes, never in plain text

## Alert Engine

After every `is_charging: false` event, the engine:
1. Fetches the 2 most recent events for that station
2. If both are `is_charging: false` → checks for existing open alert
3. If no open alert exists → creates one in the `alerts` table
4. Returns `alert_created: true` in the ingest response

This means a station must miss **two consecutive reports** (20–30 minutes) before an alert fires.

## Key Technical Decisions

**Why FastAPI over Django/Flask?**
Modern async framework with automatic OpenAPI docs, native Pydantic validation,
and a type system familiar to developers coming from TypeScript.

**Why bcrypt directly instead of passlib?**
passlib has a compatibility bug with bcrypt >= 4.x in Python 3.12. Using bcrypt directly
avoids the dependency and is more explicit.

**Why MAX(id) instead of MAX(received_at) for latest event query?**
Events inserted in rapid succession (e.g., in tests) can have identical `received_at`
timestamps due to database clock resolution. The auto-increment `id` is always strictly ordered.

**Why APScheduler instead of a cron service?**
For a single daily task (event cleanup), APScheduler integrated into the FastAPI lifespan is simpler
than a separate Railway service. If the container restarts, Railway brings it back up and the scheduler
starts automatically. The job runs at 03:00 UTC (low-traffic window for Barcelona). The manual
`POST /admin/cleanup` endpoint remains available for on-demand runs.

**Why a seed script instead of a migration for the first user?**
The operator's credentials (email, password, station ID, API key) are runtime choices, not deployment
artifacts. The interactive `seed.py` script is run once after the first deploy. It is idempotent —
running it again skips existing records without failing. Nothing is hardcoded.
The most likely failure points are the interactions between endpoint → validation → DB → response.
Mocking the database would miss these. All 46 tests run against a real PostgreSQL instance.

## Deployment

- **Platform**: Railway
- **Trigger**: push to `main` branch on GitHub
- **Build**: Railway detects `Dockerfile` and builds the image
- **Start**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Database**: PostgreSQL service provisioned by Railway, connected via `DATABASE_URL` env var
- **Scheduler**: APScheduler starts automatically inside the FastAPI lifespan — no separate process needed
- **First deploy**: run `docker-compose exec app python seed.py` once to create the first admin user