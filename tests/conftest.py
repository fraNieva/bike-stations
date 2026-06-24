"""
Test configuration and shared fixtures.

Sets up an isolated PostgreSQL test database that is created fresh
before the test session and dropped after. Each test runs inside a
transaction that is rolled back at the end, keeping tests independent
and fast — no leftover data between tests.

Fixtures available to all test files:
- db        → SQLAlchemy session scoped to the test
- client    → HTTP client pointing to the FastAPI app with the test db
- auth_headers   → JWT headers for an authenticated admin user
- device_headers → API key headers for a registered Arduino device
"""

import os
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import bcrypt

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@db:5432/bike_stations_test"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

from app.main import app
from app.database import Base, get_db
from app import models

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "postgresql://postgres:postgres@db:5432/bike_stations_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_test_database():
    """Create the test database if it does not exist."""
    default_engine = create_engine(
        "postgresql://postgres:postgres@db:5432/postgres",
        isolation_level="AUTOCOMMIT",
    )
    with default_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname='bike_stations_test'")
        ).fetchone()
        if not exists:
            conn.execute(text("CREATE DATABASE bike_stations_test"))
    default_engine.dispose()


def drop_test_database():
    """Drop the test database after the session ends."""
    default_engine = create_engine(
        "postgresql://postgres:postgres@db:5432/postgres",
        isolation_level="AUTOCOMMIT",
    )
    with default_engine.connect() as conn:
        conn.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname='bike_stations_test'"
        ))
        conn.execute(text("DROP DATABASE IF EXISTS bike_stations_test"))
    default_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-scoped fixture that creates the test DB and all tables once,
    then drops everything after all tests have run.
    """
    create_test_database()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    drop_test_database()


# ---------------------------------------------------------------------------
# Per-test isolation
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    """
    Provides a database session that is rolled back after each test.

    This ensures every test starts with a clean state without needing
    to truncate tables or recreate the schema.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """
    Provides an async HTTP client pointed at the FastAPI app.

    Overrides the get_db dependency so every request in the test
    uses the same rolled-back session as the db fixture.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Reusable data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_user(db):
    """
    Creates an active admin user in the test database.

    Returns the user ORM object so tests can reference its id and email.
    """
    user = models.User(
        email="mariano@bicing.com",
        password_hash=bcrypt.hashpw("securepassword123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def test_device(db):
    """
    Creates a registered and active Arduino device in the test database.

    The raw API key is 'test-api-key-station-01' — tests use this value
    in the X-API-Key header. The hash stored in the db is what the server
    will validate against.
    """
    raw_api_key = "test-api-key-station-01"
    device = models.Device(
        station_id="BCN-042",
        api_key_hash=bcrypt.hashpw(raw_api_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        is_active=True,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    device.raw_api_key = raw_api_key
    return device


@pytest.fixture()
async def auth_headers(client, test_user):
    """
    Returns Authorization headers with a valid JWT for the test user.

    Use this fixture in any test that calls a JWT-protected endpoint.
    """
    response = await client.post("/auth/login", json={
        "email": "mariano@bicing.com",
        "password": "securepassword123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def device_headers(test_device):
    """
    Returns X-API-Key headers for the registered test device.

    Use this fixture in any test that calls the /ingest endpoint.
    """
    return {"X-API-Key": test_device.raw_api_key}


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_event(db, station_id="BCN-042", is_charging=True, received_at=None):
    """
    Inserts a StationEvent directly into the database.

    Useful for setting up state before testing alert logic or cleanup.
    Optionally accepts a custom received_at to simulate old records.
    """
    event = models.StationEvent(
        station_id=station_id,
        is_charging=is_charging,
        voltage=48.2,
        amperage=3.1,
        gps_lat=41.3851,
        gps_lng=2.1734,
    )
    if received_at:
        event.received_at = received_at
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def make_alert(db, station_id="BCN-042", status=models.AlertStatus.open):
    """
    Inserts an Alert directly into the database.

    Useful for testing resolution, listing, and filtering endpoints.
    """
    alert = models.Alert(
        station_id=station_id,
        status=status,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert