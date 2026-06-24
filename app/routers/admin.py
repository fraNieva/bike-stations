"""
Admin router.

Provides endpoints for managing devices, users, and running
the cleanup job. All endpoints require JWT authentication.
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.security import hash_password
from app.schemas import (
    DeviceCreate, DeviceUpdate, DeviceResponse,
    UserCreate, UserUpdate, UserResponse,
)
from app import models

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

@router.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def register_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Registers a new Arduino device.

    The api_key is hashed before storage and never returned.
    Raises 409 if a device with the same station_id already exists.
    """
    existing = db.query(models.Device).filter(
        models.Device.station_id == payload.station_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device with station_id {payload.station_id} already exists",
        )

    device = models.Device(
        station_id=payload.station_id,
        api_key_hash=hash_password(payload.api_key),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/devices", response_model=list[DeviceResponse])
def list_devices(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Returns all registered devices ordered by registration date."""
    return db.query(models.Device).order_by(models.Device.registered_at.desc()).all()


@router.patch("/devices/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Updates a device — currently supports activating or deactivating it.

    Raises 404 if the device does not exist.
    """
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    if payload.is_active is not None:
        device.is_active = payload.is_active

    db.commit()
    db.refresh(device)
    return device


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Creates a new dashboard user.

    The password is hashed before storage and never returned.
    Raises 409 if the email is already registered.
    """
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Returns all registered users."""
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Updates a user — currently supports activating or deactivating them.

    Raises 404 if the user does not exist.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Cleanup job
# ---------------------------------------------------------------------------

@router.post("/cleanup")
def run_cleanup(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Deletes station events older than 7 days.

    Alerts are never deleted — they are permanent historical records.
    Returns the count of deleted events.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    deleted = (
        db.query(models.StationEvent)
        .filter(models.StationEvent.received_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted_events": deleted}