"""Health + public client config."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/config")
async def config(settings: Settings = Depends(get_settings)) -> dict:
    """Public, unauthenticated config the SPA reads on boot."""
    return {
        "app_name": settings.app_name,
        "currency": settings.currency,
        "payment_provider": "razorpay" if settings.razorpay_enabled else "demo",
        "otp_demo_mode": settings.otp_demo_mode,
    }
