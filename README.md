# Bike Stations Monitoring API

Backend service that receives telemetry from Arduino devices installed at electric bike charging stations and exposes the data through a REST API to a monitoring dashboard.

## Context

The system monitors electric bike stations in Barcelona. Each station has an Arduino board (LilyGO T-A7670E-S3) with a 4G SIM that sends charging status every 10–15 minutes. The goal is to detect stations that have stopped charging and alert the maintenance team in real time.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| Containerization | Docker + Docker Compose |
| Hosting | Railway |
| Testing | pytest + httpx |

## Project Structure

```
bike-stations/
├── app/
│   ├── main.py          # FastAPI entry point, router registration
│   ├── database.py      # SQLAlchemy engine and session
│   ├── models.py        # ORM models (4 tables)
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── security.py      # Password hashing and JWT utilities
│   ├── dependencies.py  # FastAPI dependencies (auth guards)
│   └── routers/
│       ├── auth.py      # POST /auth/login
│       ├── ingest.py    # POST /ingest (Arduino endpoint)
│       ├── alerts.py    # GET/PATCH /alerts
│       ├── stations.py  # GET /stations
│       └── admin.py     # /admin/devices, /admin/users, /admin/cleanup
├── alembic/             # Database migrations
├── tests/               # Integration test suite (46 tests)
├── docs/                # Extended documentation
├── Dockerfile
├── docker-compose.yml   # Local development (app + postgres)
└── requirements.txt
```

## Getting Started

### Prerequisites

- Docker Desktop
- Git

### Run locally

```bash
git clone https://github.com/your-org/bike-stations.git
cd bike-stations

# Copy environment file and fill in values
cp .env.example .env

# Start the app and database
docker-compose up --build
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

### Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Random secret for JWT signing — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |

### Run tests

```bash
docker-compose exec app pytest -v
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — system design, layers, and technical decisions
- [API Reference](docs/API.md) — all endpoints, payloads, and response formats
- [Data Model](docs/DATA_MODEL.md) — database tables, fields, and relationships
- [Requirements](docs/REQUIREMENTS.md) — client requirements and business rules