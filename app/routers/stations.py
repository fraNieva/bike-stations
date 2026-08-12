"""
Stations router.

Provides dashboard endpoints to view the current status of all
monitored stations and the event history for a specific station.
All endpoints require JWT authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.dependencies import get_current_user
from app import models

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("")
def list_stations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns the latest telemetry event for each known station.

    Uses a subquery to find the most recent received_at per station,
    then fetches the full event for that timestamp. This gives the
    dashboard the current charging status of every station at a glance.
    """
    latest_per_station = (
        db.query(
            models.StationEvent.station_id,
            func.max(models.StationEvent.id).label("max_id"),
        )
        .group_by(models.StationEvent.station_id)
        .subquery()
    )

    events = (
        db.query(models.StationEvent)
        .join(
            latest_per_station,
            (models.StationEvent.station_id == latest_per_station.c.station_id)
            & (models.StationEvent.id == latest_per_station.c.max_id),
        )
        .all()
    )

    return [
        {
            "station_id": e.station_id,
            "is_charging": e.is_charging,
            "voltage": e.voltage,
            "amperage": e.amperage,
            "gps_lat": e.gps_lat,
            "gps_lng": e.gps_lng,
            "last_seen_at": e.received_at,
        }
        for e in events
    ]


@router.get("/{station_id}")
def get_station(
    station_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns the detail and last 10 events for a specific station.

    Raises 404 if no events exist for the given station_id.
    """
    events = (
        db.query(models.StationEvent)
        .filter(models.StationEvent.station_id == station_id)
        .order_by(models.StationEvent.received_at.desc())
        .limit(10)
        .all()
    )

    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for station {station_id}",
        )

    return {
        "station_id": station_id,
        "current_status": events[0].is_charging,
        "events": [
            {
                "id": e.id,
                "is_charging": e.is_charging,
                "voltage": e.voltage,
                "amperage": e.amperage,
                "received_at": e.received_at,
            }
            for e in events
        ],
    }