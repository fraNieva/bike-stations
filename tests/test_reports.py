"""
Tests for the reports endpoint.

Covers: totals without filters, filtering by date range, filtering by station,
by_station breakdown, avg_resolution_minutes calculation, auth requirement,
and edge cases (no data, all open, all resolved).
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models import AlertStatus
from tests.conftest import make_alert


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def test_reports_require_authentication(client):
    """GET /reports/alerts returns 403 without a valid JWT."""
    response = await client.get("/reports/alerts")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Basic response shape
# ---------------------------------------------------------------------------

async def test_reports_empty_database(client, auth_headers):
    """Returns zeroes and empty by_station when there are no alerts."""
    response = await client.get("/reports/alerts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["open"] == 0
    assert data["resolved"] == 0
    assert data["by_station"] == []


async def test_reports_totals(client, auth_headers, db):
    """Returns correct totals across all alerts."""
    make_alert(db, station_id="BCN-042", status=AlertStatus.open)
    make_alert(db, station_id="BCN-042", status=AlertStatus.resolved)
    make_alert(db, station_id="BCN-043", status=AlertStatus.open)

    response = await client.get("/reports/alerts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["open"] == 2
    assert data["resolved"] == 1


# ---------------------------------------------------------------------------
# by_station breakdown
# ---------------------------------------------------------------------------

async def test_reports_by_station_breakdown(client, auth_headers, db):
    """by_station groups alerts per station with correct counts."""
    make_alert(db, station_id="BCN-042", status=AlertStatus.open)
    make_alert(db, station_id="BCN-042", status=AlertStatus.resolved)
    make_alert(db, station_id="BCN-043", status=AlertStatus.open)

    response = await client.get("/reports/alerts", headers=auth_headers)
    data = response.json()

    by_station = {s["station_id"]: s for s in data["by_station"]}
    assert "BCN-042" in by_station
    assert "BCN-043" in by_station
    assert by_station["BCN-042"]["total"] == 2
    assert by_station["BCN-042"]["open"] == 1
    assert by_station["BCN-042"]["resolved"] == 1
    assert by_station["BCN-043"]["total"] == 1
    assert by_station["BCN-043"]["open"] == 1


async def test_reports_by_station_sorted_by_total_descending(client, auth_headers, db):
    """by_station is sorted with the most problematic station first."""
    make_alert(db, station_id="BCN-001")
    make_alert(db, station_id="BCN-002")
    make_alert(db, station_id="BCN-002")
    make_alert(db, station_id="BCN-002")

    response = await client.get("/reports/alerts", headers=auth_headers)
    data = response.json()

    assert data["by_station"][0]["station_id"] == "BCN-002"
    assert data["by_station"][1]["station_id"] == "BCN-001"


# ---------------------------------------------------------------------------
# avg_resolution_minutes
# ---------------------------------------------------------------------------

async def test_avg_resolution_minutes_for_station_filter(client, auth_headers, db):
    """When filtering by station_id, avg_resolution_minutes is returned at top level."""
    alert = make_alert(db, station_id="BCN-042", status=AlertStatus.resolved)

    # Manually set resolved_at 60 minutes after created_at.
    alert.resolved_at = alert.created_at + timedelta(minutes=60)
    db.commit()

    response = await client.get(
        "/reports/alerts?station_id=BCN-042", headers=auth_headers
    )
    data = response.json()
    assert data["avg_resolution_minutes"] == 60.0


async def test_avg_resolution_minutes_only_counts_resolved(client, auth_headers, db):
    """Open alerts are excluded from avg_resolution_minutes."""
    alert = make_alert(db, station_id="BCN-042", status=AlertStatus.resolved)
    alert.resolved_at = alert.created_at + timedelta(minutes=120)
    db.commit()
    make_alert(db, station_id="BCN-042", status=AlertStatus.open)

    response = await client.get(
        "/reports/alerts?station_id=BCN-042", headers=auth_headers
    )
    data = response.json()
    # Only the resolved alert (120 min) should be averaged.
    assert data["avg_resolution_minutes"] == 120.0


async def test_avg_resolution_minutes_is_none_when_no_resolved(client, auth_headers, db):
    """avg_resolution_minutes is null when there are no resolved alerts."""
    make_alert(db, station_id="BCN-042", status=AlertStatus.open)

    response = await client.get(
        "/reports/alerts?station_id=BCN-042", headers=auth_headers
    )
    data = response.json()
    assert data["avg_resolution_minutes"] is None


# ---------------------------------------------------------------------------
# station_id filter
# ---------------------------------------------------------------------------

async def test_filter_by_station_id(client, auth_headers, db):
    """?station_id returns only alerts for that station."""
    make_alert(db, station_id="BCN-042")
    make_alert(db, station_id="BCN-043")

    response = await client.get(
        "/reports/alerts?station_id=BCN-042", headers=auth_headers
    )
    data = response.json()
    assert data["total"] == 1
    assert data["by_station"] is None


async def test_filter_by_station_id_no_results(client, auth_headers, db):
    """?station_id with unknown station returns zeroes."""
    make_alert(db, station_id="BCN-042")

    response = await client.get(
        "/reports/alerts?station_id=BCN-999", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Date range filters
# ---------------------------------------------------------------------------

async def test_filter_by_from_date(client, auth_headers, db):
    """?from excludes alerts created before that date."""
    old_alert = make_alert(db, station_id="BCN-042")
    old_alert.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db.commit()

    recent_alert = make_alert(db, station_id="BCN-042")
    recent_alert.created_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    db.commit()

    response = await client.get(
        "/reports/alerts?from=2026-03-01T00:00:00Z", headers=auth_headers
    )
    data = response.json()
    assert data["total"] == 1


async def test_filter_by_to_date(client, auth_headers, db):
    """?to excludes alerts created after that date."""
    old_alert = make_alert(db, station_id="BCN-042")
    old_alert.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db.commit()

    recent_alert = make_alert(db, station_id="BCN-042")
    recent_alert.created_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    db.commit()

    response = await client.get(
        "/reports/alerts?to=2026-03-01T00:00:00Z", headers=auth_headers
    )
    data = response.json()
    assert data["total"] == 1


async def test_filter_by_date_range(client, auth_headers, db):
    """Combining ?from and ?to returns only alerts within the range."""
    for month in [1, 3, 6]:
        alert = make_alert(db, station_id="BCN-042")
        alert.created_at = datetime(2026, month, 1, tzinfo=timezone.utc)
        db.commit()

    response = await client.get(
        "/reports/alerts?from=2026-02-01T00:00:00Z&to=2026-05-01T00:00:00Z",
        headers=auth_headers,
    )
    data = response.json()
    assert data["total"] == 1