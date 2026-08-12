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
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db),
) -> models.Device:
    """
    Validates the X-API-Key header and returns the authenticated device.

    Iterates active devices and verifies the key against stored bcrypt hashes.
    Raises 401 if no matching key is found.
    Raises 403 if the device is inactive.
    """
    devices = db.query(models.Device).filter(models.Device.is_active == True).all()

    for device in devices:
        if verify_password(api_key, device.api_key_hash):
            return device

    # Check if key exists but device is inactive
    all_devices = db.query(models.Device).all()
    for device in all_devices:
        if verify_password(api_key, device.api_key_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device is inactive",
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )