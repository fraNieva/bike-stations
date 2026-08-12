"""
Authentication router.

Provides the login endpoint that validates credentials and returns
a JWT access token for use in subsequent authenticated requests.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import verify_password, create_access_token
from app.schemas import LoginRequest, TokenResponse
from app import models

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Validates email and password and returns a JWT access token.

    Raises 401 if the email is not found, the password is wrong,
    or the user account has been deactivated.
    """
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token)