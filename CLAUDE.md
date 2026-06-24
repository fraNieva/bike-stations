# CLAUDE.md — Project Context for AI Agents

This file provides context for AI coding agents working on this project.
Read this file first before making any changes.

## What This Project Does

REST API backend for monitoring electric bike charging stations in Barcelona.
Arduino boards installed at stations send telemetry (charging status, voltage, amperage, GPS)
every 10–15 minutes via 4G. The server processes the data, detects charging failures,
generates alerts, and exposes everything to a maintenance dashboard.

## Current Status

- Phase: POC (Proof of Concept) — one station being tested
- Target: 40–50 stations in pilot, 256 total
- Backend: complete and deployed on Railway
- Dashboard: not yet built (planned in React/Next.js)

## Tech Stack

- **Python 3.12** with **FastAPI** — REST API
- **PostgreSQL 15** — database
- **SQLAlchemy 2** — ORM
- **Alembic** — migrations (always use Alembic, never `create_all()` in production)
- **bcrypt** — password and API key hashing (do NOT use passlib — incompatible with current bcrypt version)
- **python-jose** — JWT tokens
- **pytest + httpx** — integration tests (run inside Docker: `docker-compose exec app pytest -v`)

## Key Business Rules

1. **Alert trigger**: two consecutive `is_charging: false` events for the same station → create alert
2. **No duplicate alerts**: if an open alert already exists for a station, do not create another
3. **Event TTL**: station events are deleted after 7 days by the cleanup job
4. **Alerts are permanent**: alerts are never deleted, only resolved
5. **Device authentication**: each Arduino board sends an `X-API-Key` header — validated against bcrypt hash in `devices` table
6. **User authentication**: dashboard uses JWT Bearer tokens — 8 hour expiry

## Database Tables

- `users` — dashboard administrators
- `devices` — registered Arduino boards (one per station)
- `station_events` — raw telemetry (TTL: 7 days)
- `alerts` — charging failure incidents (permanent)

See [docs/DATA_MODEL.md](docs/DATA_MODEL.md) for full schema.

## API Structure

- `POST /auth/login` — returns JWT
- `POST /ingest` — Arduino endpoint (X-API-Key auth)
- `GET /stations` — current status of all stations (JWT)
- `GET /stations/{id}` — station detail + last 10 events (JWT)
- `GET /alerts` — list alerts with optional status filter (JWT)
- `PATCH /alerts/{id}` — resolve an alert (JWT)
- `POST /admin/devices` — register new Arduino board (JWT)
- `GET /admin/devices` — list devices (JWT)
- `PATCH /admin/devices/{id}` — activate/deactivate device (JWT)
- `POST /admin/users` — create user (JWT)
- `GET /admin/users` — list users (JWT)
- `PATCH /admin/users/{id}` — activate/deactivate user (JWT)
- `POST /admin/cleanup` — delete events older than 7 days (JWT)
- `GET /health` — health check (no auth)

See [docs/API.md](docs/API.md) for full request/response contracts.

## Development Workflow

1. Make changes to code locally
2. Run `docker-compose up --build -d` to rebuild
3. Run `docker-compose exec app pytest -v` to verify all 46 tests pass
4. Commit and push — Railway deploys automatically from GitHub

## What Is Pending

- Notifications (Telegram + email) when alert is created
- Automatic daily cleanup scheduler (currently manual endpoint)
- First user seed script (currently requires manual DB insert)
- Reports endpoint (`GET /reports/alerts`)
- Dashboard frontend (React/Next.js — separate project)

## Important Constraints

- Do NOT use `passlib` — use `bcrypt` directly (see `app/security.py`)
- Do NOT call `Base.metadata.create_all()` — use Alembic migrations
- All new database changes require a new migration file in `alembic/versions/`
- All code and comments must be in English
- Every function must have a docstring
- Tests run against a separate `bike_stations_test` database inside Docker