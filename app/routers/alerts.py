"""
Alerts router.

Exposes endpoints for listing, filtering, and resolving alerts.
All endpoints require JWT authentication.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas import AlertResponse, AlertResolve
from app import models

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    status: Optional[models.AlertStatus] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns all alerts, optionally filtered by status.

    Query params:
        status: 'open' or 'resolved' — omit to return all alerts.
    """
    query = db.query(models.Alert)
    if status:
        query = query.filter(models.Alert.status == status)
    return query.order_by(models.Alert.created_at.desc()).all()


@router.patch("/{alert_id}", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    payload: AlertResolve,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Marks an alert as resolved.

    Records who resolved it and when. Raises 409 if the alert
    is already resolved, and 404 if it does not exist.
    """
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    if alert.status == models.AlertStatus.resolved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alert is already resolved",
        )

    alert.status = models.AlertStatus.resolved
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = current_user.id
    alert.notes = payload.notes
    db.commit()
    db.refresh(alert)
    return alert