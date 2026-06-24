"""
Ingest router.

Receives telemetry from Arduino devices, persists the event,
updates the device last_seen_at timestamp, and runs the alert engine
to detect consecutive non-charging events.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_device
from app.schemas import IngestPayload, IngestResponse
from app import models

router = APIRouter(tags=["ingest"])


def _check_and_create_alert(station_id: str, db: Session) -> bool:
    """
    Runs the alert engine after a non-charging event is received.

    Retrieves the two most recent events for the station. If both
    report is_charging=False and there is no open alert already,
    a new alert is created.

    Returns True if a new alert was created, False otherwise.
    """
    recent = (
        db.query(models.StationEvent)
        .filter(models.StationEvent.station_id == station_id)
        .order_by(models.StationEvent.received_at.desc())
        .limit(2)
        .all()
    )

    if len(recent) < 2:
        return False

    both_not_charging = all(not e.is_charging for e in recent)
    if not both_not_charging:
        return False

    existing_alert = (
        db.query(models.Alert)
        .filter(
            models.Alert.station_id == station_id,
            models.Alert.status == models.AlertStatus.open,
        )
        .first()
    )

    if existing_alert:
        return False

    alert = models.Alert(station_id=station_id)
    db.add(alert)
    db.commit()
    return True


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
def ingest(
    payload: IngestPayload,
    db: Session = Depends(get_db),
    device: models.Device = Depends(get_current_device),
):
    """
    Receives a telemetry payload from a registered Arduino device.

    Validates that the station_id in the payload matches a registered
    device, persists the event, updates last_seen_at, and runs the
    alert engine if the station reports not charging.

    Raises 404 if the station_id is not registered in the devices table.
    """
    registered = db.query(models.Device).filter(
        models.Device.station_id == payload.station_id
    ).first()

    if not registered:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} is not registered",
        )

    event = models.StationEvent(
        station_id=payload.station_id,
        is_charging=payload.is_charging,
        voltage=payload.voltage,
        amperage=payload.amperage,
        gps_lat=payload.gps_lat,
        gps_lng=payload.gps_lng,
    )
    db.add(event)

    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)

    alert_created = False
    if not payload.is_charging:
        alert_created = _check_and_create_alert(payload.station_id, db)

    return IngestResponse(
        id=event.id,
        station_id=event.station_id,
        is_charging=event.is_charging,
        received_at=event.received_at,
        alert_created=alert_created,
    )