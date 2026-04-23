"""
backend/app/core/auth.py
JWT utilities: create_token, verify_token, get_current_user dependency.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

_bearer_scheme = HTTPBearer()


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload dict — must include at least ``sub`` (user id) and ``role``.
        expires_delta: Custom expiry; defaults to ACCESS_TOKEN_EXPIRE_HOURS.

    Returns:
        Encoded JWT string.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None
        else timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    payload["exp"] = expire
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Args:
        token: Raw JWT string.

    Returns:
        Decoded payload dict.

    Raises:
        HTTPException 401: If the token is invalid, expired, or missing ``sub``.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kedaluwarsa",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    if payload.get("sub") is None:
        raise credentials_exception

    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """FastAPI dependency — extract and validate the current user from Bearer token.

    Args:
        credentials: Injected by HTTPBearer; contains the raw token.
        db: SQLAlchemy session injected by get_db.

    Returns:
        Active User ORM instance.

    Raises:
        HTTPException 401: If token is invalid, user not found, or user is inactive.
    """
    # Lazy import to avoid circular dependency at module load time
    from app.models.user import User  # noqa: PLC0415

    payload = verify_token(credentials.credentials)
    user_id: str = payload["sub"]

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan atau tidak aktif",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
