"""Token minting + validation for the two account kinds this API serves.

Customers authenticate with a phone OTP and receive a token whose subject is
``customer:<phone>``. Staff authenticate with the admin password and receive a
token whose subject is ``admin``. Both are HS256 JWTs this API issues and
verifies itself — no external identity provider.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=True)

CUSTOMER_PREFIX = "customer:"
ADMIN_SUBJECT = "admin"


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_token(subject: str, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_customer_token(phone: str, settings: Settings) -> str:
    return create_token(f"{CUSTOMER_PREFIX}{phone}", settings)


def create_admin_token(settings: Settings) -> str:
    return create_token(ADMIN_SUBJECT, settings)


def _decode(token: str, settings: Settings) -> str:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise _unauthorized("Invalid or expired token") from exc
    subject = claims.get("sub")
    if not subject:
        raise _unauthorized("Token missing subject")
    return subject


def get_current_subject(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    """Return the raw token subject (``customer:<phone>`` or ``admin``)."""
    return _decode(credentials.credentials, settings)


def get_current_customer(subject: str = Depends(get_current_subject)) -> str:
    """Return the customer's phone number, or 401 if the token isn't a customer's."""
    if not subject.startswith(CUSTOMER_PREFIX):
        raise _unauthorized("Customer sign-in required")
    return subject[len(CUSTOMER_PREFIX) :]


def require_admin(subject: str = Depends(get_current_subject)) -> str:
    """Allow only the staff/admin token through."""
    if subject != ADMIN_SUBJECT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return subject
