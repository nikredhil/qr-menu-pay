"""Customer phone-OTP sign-in and staff password sign-in."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.dependencies import get_customer_service, get_otp_service
from app.core.security import create_admin_token, create_customer_token
from app.models.schemas.auth import (
    AdminLogin,
    AdminToken,
    CustomerToken,
    OtpRequest,
    OtpRequestResult,
    OtpVerify,
)
from app.services.customer_service import CustomerService
from app.services.otp_service import OtpError, OtpService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/request", response_model=OtpRequestResult)
async def request_otp(
    payload: OtpRequest,
    otp: OtpService = Depends(get_otp_service),
) -> OtpRequestResult:
    try:
        ttl, debug_otp = await otp.request(payload.phone, payload.name)
    except OtpError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return OtpRequestResult(phone=payload.phone, expires_in=ttl, debug_otp=debug_otp)


@router.post("/otp/verify", response_model=CustomerToken)
async def verify_otp(
    payload: OtpVerify,
    settings: Settings = Depends(get_settings),
    otp: OtpService = Depends(get_otp_service),
    customers: CustomerService = Depends(get_customer_service),
) -> CustomerToken:
    try:
        name = otp.verify(payload.phone, payload.code)
    except OtpError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    record = await customers.upsert(payload.phone, name)
    token = create_customer_token(payload.phone, settings)
    return CustomerToken(access_token=token, phone=payload.phone, name=record.get("name"))


@router.post("/admin/login", response_model=AdminToken)
async def admin_login(
    payload: AdminLogin,
    settings: Settings = Depends(get_settings),
) -> AdminToken:
    import secrets

    if not secrets.compare_digest(payload.password, settings.admin_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect staff password"
        )
    return AdminToken(access_token=create_admin_token(settings))
