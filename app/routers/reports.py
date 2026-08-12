"""
Reports router.

Exposes aggregated alert history for analysis by the maintenance team.
All endpoints require JWT authentication.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas import AlertsReportResponse, StationAlertSummary, ReportPeriod

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/alerts", response_model=AlertsReportResponse)
def get_alerts_report(
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    station_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """
    Return aggregated alert history with optional filters.

    Filters:
    - from / to: restrict to alerts created within a date range.
    - station_id: restrict to a single station (omits by_station breakdown).

    The avg_resolution_minutes field only considers resolved alerts;
    open alerts have no resolution time and are excluded from the average.
    """
    query = db.query(models.Alert)

    if from_date:
        query = query.filter(models.Alert.created_at >= from_date)
    if to_date:
        query = query.filter(models.Alert.created_at <= to_date)
    if station_id:
        query = query.filter(models.Alert.station_id == station_id)

    alerts = query.all()

    total = len(alerts)
    open_count = sum(1 for a in alerts if a.status == models.AlertStatus.open)
    resolved_count = total - open_count

    # Determine the actual period covered by the results.
    created_dates = [a.created_at for a in alerts]
    period = ReportPeriod(
        from_date=min(created_dates) if created_dates else from_date,
        to_date=max(created_dates) if created_dates else to_date,
    )

    # Build per-station breakdown only when not filtering by a single station.
    by_station = None
    if not station_id:
        by_station = _build_station_breakdown(alerts)

    # When filtering by station, compute avg_resolution_minutes at the top level.
    avg_resolution_minutes = None
    if station_id:
        avg_resolution_minutes = _compute_avg_resolution(alerts)

    return AlertsReportResponse(
        total=total,
        open=open_count,
        resolved=resolved_count,
        avg_resolution_minutes=avg_resolution_minutes,
        by_station=by_station,
        period=period,
    )


def _compute_avg_resolution(alerts: list[models.Alert]) -> Optional[float]:
    """
    Compute average resolution time in minutes for a list of alerts.

    Only resolved alerts (those with a resolved_at timestamp) are included.
    Returns None if there are no resolved alerts.
    """
    resolved = [a for a in alerts if a.resolved_at is not None]
    if not resolved:
        return None
    total_minutes = sum(
        (a.resolved_at - a.created_at).total_seconds() / 60
        for a in resolved
    )
    return round(total_minutes / len(resolved), 1)


def _build_station_breakdown(alerts: list[models.Alert]) -> list[StationAlertSummary]:
    """
    Group alerts by station_id and compute per-station metrics.

    Returns a list sorted by total alerts descending (most problematic stations first).
    """
    grouped: dict[str, list[models.Alert]] = {}
    for alert in alerts:
        grouped.setdefault(alert.station_id, []).append(alert)

    summaries = []
    for station_id, station_alerts in grouped.items():
        total = len(station_alerts)
        open_count = sum(1 for a in station_alerts if a.status == models.AlertStatus.open)
        summaries.append(
            StationAlertSummary(
                station_id=station_id,
                total=total,
                open=open_count,
                resolved=total - open_count,
                avg_resolution_minutes=_compute_avg_resolution(station_alerts),
            )
        )

    summaries.sort(key=lambda s: s.total, reverse=True)
    return summaries