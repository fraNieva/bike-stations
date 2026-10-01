"""
FastAPI dependencies shared across routers.

Provides reusable injectable functions for JWT authentication
and API key validation, used via FastAPI's Depends() mechanism.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import decode_access_token, verify_password
from app import models
from app.schemas import IngestPayload

bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Validates the JWT Bearer token and returns the authenticated user.

    Raises 401 if the token is missing, invalid, or expired.
    Raises 401 if the user no longer exists or has been deactivated.
    """
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    email = payload.get("sub")
    user = db.query(models.User).filter(
        models.User.email == email,
        models.User.is_active == True,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def get_current_device(
    payload: IngestPayload,
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db),
) -> models.Device:
    """
    Validates the X-API-Key header against the device named in the payload.

    Looks up the single device registered for payload.station_id and verifies
    the key against that device's bcrypt hash only. This binds each key to its
    own station and keeps authentication cost constant as devices are added.

    Raises 404 if the station_id is not registered.
    Raises 401 if the key does not belong to that station.
    Raises 403 if the device is inactive.
    """
    device = db.query(models.Device).filter(
        models.Device.station_id == payload.station_id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {payload.station_id} is not registered",
        )

    if not verify_password(api_key, device.api_key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is inactive",
        )

    return device
