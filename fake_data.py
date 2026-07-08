"""
Local dev-only fixture generator — NOT for staging or production use.

Wipes all existing data (users, devices, station_events, alerts), then
creates one dashboard user and 5 demo stations (devices), backfilling each
station with a realistic history of telemetry events so the frontend has
something meaningful to render (status list, station detail, alerts).

Every run starts from a clean, empty database.

Usage:
    docker-compose exec app python fake_data.py

Environment:
    DATABASE_URL must be set (set automatically inside Docker).
"""

import os
import random
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sqlalchemy import text

from app import models
from app.security import hash_password

load_dotenv()

USER_EMAIL = "user@test.com"
USER_PASSWORD = "Test1234!"

NUM_STATIONS = 5
BASE_LAT = 41.3874
BASE_LNG = 2.1686

EVENT_INTERVAL_MINUTES = 15
HISTORY_HOURS = 48


def get_engine():
    """Create a SQLAlchemy engine from DATABASE_URL."""
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)
    return create_engine(url)


def wipe_database(session: Session) -> None:
    """Delete all rows from every table so the database starts empty."""
    print("Wiping existing data (users, devices, station_events, alerts)...")
    session.execute(
        text("TRUNCATE TABLE alerts, station_events, devices, users RESTART IDENTITY CASCADE")
    )
    session.commit()
    print("  [ok]   Database is now empty.\n")


def upsert_user(session: Session) -> models.User:
    """Return the demo user, creating it if it doesn't exist yet."""
    user = session.query(models.User).filter(models.User.email == USER_EMAIL).first()
    if user:
        print(f"  [skip] User '{USER_EMAIL}' already exists (id={user.id}).")
        return user

    user = models.User(
        email=USER_EMAIL,
        password_hash=hash_password(USER_PASSWORD),
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"  [ok]   User '{USER_EMAIL}' created (password: {USER_PASSWORD}).")
    return user


def upsert_device(session: Session, station_id: str, api_key: str) -> models.Device:
    """Create or update a device so its api_key matches the given value."""
    device = session.query(models.Device).filter(models.Device.station_id == station_id).first()
    api_key_hash = hash_password(api_key)

    if device:
        device.api_key_hash = api_key_hash
        device.is_active = True
        session.commit()
        print(f"  [ok]   Device '{station_id}' updated (api_key: {api_key}).")
        return device

    device = models.Device(
        station_id=station_id,
        api_key_hash=api_key_hash,
        is_active=True,
        registered_at=datetime.now(timezone.utc) - timedelta(hours=HISTORY_HOURS),
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    print(f"  [ok]   Device '{station_id}' created (api_key: {api_key}).")
    return device


def generate_events(station_id: str, scenario: str, index: int) -> list[dict]:
    """
    Build a chronological list of fake telemetry readings for one station.

    Scenarios:
      healthy   - always charging, normal readings.
      open      - charging normally, then the last 2 readings go offline
                  (should trigger an open alert on ingest-equivalent logic).
      resolved  - a non-charging streak in the middle of the window that
                  later recovers (paired with a manually resolved alert).
      blip      - a single isolated non-charging reading, no alert.
      stale     - stopped reporting ~30 hours ago (no recent data).
    """
    now = datetime.now(timezone.utc)
    lat = BASE_LAT + index * 0.003
    lng = BASE_LNG + index * 0.003

    total_events = (HISTORY_HOURS * 60) // EVENT_INTERVAL_MINUTES
    events = []

    for i in range(total_events):
        received_at = now - timedelta(minutes=EVENT_INTERVAL_MINUTES * (total_events - i))
        is_charging = True

        if scenario == "open" and i >= total_events - 2:
            is_charging = False
        elif scenario == "resolved" and total_events // 2 <= i < total_events // 2 + 3:
            is_charging = False
        elif scenario == "blip" and i == total_events // 3:
            is_charging = False

        if scenario == "stale" and received_at > now - timedelta(hours=30):
            continue

        events.append(
            {
                "station_id": station_id,
                "is_charging": is_charging,
                "voltage": round(random.uniform(11.8, 12.6), 2) if is_charging else 0.0,
                "amperage": round(random.uniform(0.8, 2.0), 2) if is_charging else 0.0,
                "gps_lat": lat,
                "gps_lng": lng,
                "received_at": received_at,
            }
        )

    return events


def insert_events(session: Session, device: models.Device, events: list[dict]) -> None:
    """Persist a batch of events for a device and update its last_seen_at."""
    for e in events:
        session.add(models.StationEvent(**e))

    if events:
        device.last_seen_at = max(e["received_at"] for e in events)

    session.commit()
    print(f"  [ok]   {len(events)} events inserted for '{device.station_id}'.")


def maybe_create_alert(session: Session, station_id: str, scenario: str, user: models.User) -> None:
    """Create an alert matching the scenario, mirroring the ingest alert engine."""
    now = datetime.now(timezone.utc)

    if scenario == "open":
        existing = (
            session.query(models.Alert)
            .filter(models.Alert.station_id == station_id, models.Alert.status == models.AlertStatus.open)
            .first()
        )
        if existing:
            print(f"  [skip] Open alert already exists for '{station_id}'.")
            return
        alert = models.Alert(
            station_id=station_id,
            created_at=now - timedelta(minutes=EVENT_INTERVAL_MINUTES),
            status=models.AlertStatus.open,
        )
        session.add(alert)
        session.commit()
        print(f"  [ok]   Open alert created for '{station_id}'.")

    elif scenario == "resolved":
        existing = session.query(models.Alert).filter(models.Alert.station_id == station_id).first()
        if existing:
            print(f"  [skip] Alert already exists for '{station_id}'.")
            return
        created_at = now - timedelta(hours=HISTORY_HOURS // 2)
        alert = models.Alert(
            station_id=station_id,
            created_at=created_at,
            status=models.AlertStatus.resolved,
            resolved_at=created_at + timedelta(hours=1),
            resolved_by=user.id,
            notes="Reconnected after maintenance visit.",
        )
        session.add(alert)
        session.commit()
        print(f"  [ok]   Resolved alert created for '{station_id}'.")


def main() -> None:
    """Entry point — seed a demo user, 5 stations, and their telemetry history."""
    print("\n=== Bike Stations — Demo Data (local only) ===\n")

    engine = get_engine()
    with Session(engine) as session:
        wipe_database(session)
        user = upsert_user(session)

        scenarios = ["healthy", "open", "resolved", "blip", "stale"]
        print("\nRegistering stations:")
        for i, scenario in enumerate(scenarios, start=1):
            station_id = str(i)
            api_key = f"arduino-key-{i}"
            device = upsert_device(session, station_id, api_key)

            events = generate_events(station_id, scenario, i)
            insert_events(session, device, events)
            maybe_create_alert(session, station_id, scenario, user)
            print(f"  station '{station_id}' -> scenario: {scenario}\n")

    print("Done. Log in with:")
    print(f"  email:    {USER_EMAIL}")
    print(f"  password: {USER_PASSWORD}\n")


if __name__ == "__main__":
    main()
