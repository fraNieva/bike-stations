"""
Tests for the automatic cleanup of station events older than 7 days.

Verifies that:
- Events older than 7 days are deleted by the cleanup job
- Recent events are preserved
- Alerts are never deleted regardless of age
"""

import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import make_event, make_alert
from app.models import StationEvent, Alert


def make_old_event(db, days_old, station_id="BCN-042"):
    """Creates an event with a backdated received_at timestamp."""
    old_date = datetime.now(timezone.utc) - timedelta(days=days_old)
    return make_event(db, station_id=station_id, received_at=old_date)


@pytest.mark.asyncio
async def test_cleanup_deletes_events_older_than_7_days(client, auth_headers, db):
    """Events older than 7 days are removed by the cleanup job."""
    make_old_event(db, days_old=8)
    make_old_event(db, days_old=10)
    make_old_event(db, days_old=30)

    response = await client.post("/admin/cleanup", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["deleted_events"] == 3

    remaining = db.query(StationEvent).all()
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_cleanup_preserves_recent_events(client, auth_headers, db):
    """Events from the last 7 days are not deleted."""
    make_old_event(db, days_old=6)
    make_old_event(db, days_old=3)
    make_event(db)

    response = await client.post("/admin/cleanup", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["deleted_events"] == 0

    remaining = db.query(StationEvent).all()
    assert len(remaining) == 3


@pytest.mark.asyncio
async def test_cleanup_mixed_events(client, auth_headers, db):
    """Only old events are deleted; recent ones survive."""
    make_old_event(db, days_old=8)
    make_old_event(db, days_old=9)
    make_old_event(db, days_old=6)
    make_event(db)

    response = await client.post("/admin/cleanup", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["deleted_events"] == 2

    remaining = db.query(StationEvent).all()
    assert len(remaining) == 2


@pytest.mark.asyncio
async def test_cleanup_never_deletes_alerts(client, auth_headers, db):
    """
    Alerts are permanent records and must never be deleted by the cleanup job,
    regardless of how old they are.
    """
    from datetime import datetime, timedelta, timezone
    old_date = datetime.now(timezone.utc) - timedelta(days=30)

    alert = make_alert(db, station_id="BCN-042")
    alert.created_at = old_date
    db.commit()

    response = await client.post("/admin/cleanup", headers=auth_headers)
    assert response.status_code == 200

    alerts = db.query(Alert).all()
    assert len(alerts) == 1


@pytest.mark.asyncio
async def test_cleanup_returns_correct_count(client, auth_headers, db):
    """The cleanup response reports exactly how many events were deleted."""
    make_old_event(db, days_old=10)
    make_old_event(db, days_old=15)
    make_old_event(db, days_old=20)
    make_event(db)

    response = await client.post("/admin/cleanup", headers=auth_headers)
    assert response.json()["deleted_events"] == 3