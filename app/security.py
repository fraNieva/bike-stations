"""
Security utilities for password hashing and JWT token management.

Centralises all cryptographic operations so they can be reused
across routers without duplication.
"""

import os
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-dev-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours


def hash_password(plain: str) -> str:
    """Returns the bcrypt hash of a plain text password or API key."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Returns True if the plain text matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    """
    Creates a signed JWT token with an expiry of 8 hours.

    Args:
        data: Payload to encode — typically {"sub": user_email}.

    Returns:
        Signed JWT string.
    """
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Decodes and validates a JWT token.

    Returns the payload dict if valid, or None if expired or tampered.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None