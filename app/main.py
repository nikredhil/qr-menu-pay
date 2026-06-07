"""Application entry point: lifespan wiring, CORS, router registration."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, health, menu, orders, payments, tables
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.repositories import CONTAINERS
from app.db.repositories.base import BaseRepository
from app.db.repositories.file_store import JsonFileRepository
from app.db.repositories.memory import InMemoryRepository
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.otp_service import OtpService
from app.services.payment_service import PaymentService
from app.services.sms import build_sms_sender
from app.services.table_service import TableService

logger = get_logger(__name__)


def _build_backends() -> dict[str, BaseRepository]:
    settings = get_settings()
    if settings.db_backend == "file":
        os.makedirs(settings.data_dir, exist_ok=True)
        return {
            name: JsonFileRepository(os.path.join(settings.data_dir, f"{name}.json"))
            for name, _pk in CONTAINERS
        }
    return {name: InMemoryRepository() for name, _pk in CONTAINERS}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "startup",
        app=settings.app_name,
        db_backend=settings.db_backend,
        payments="razorpay" if settings.razorpay_enabled else "demo",
        otp="demo" if settings.otp_demo_mode else settings.otp_provider,
    )

    backends = _build_backends()

    menu_service = MenuService(backends["menu_items"])
    table_service = TableService(backends["tables"])
    order_service = OrderService(backends["orders"], menu_service, table_service)
    customer_service = CustomerService(backends["customers"])
    sms_sender = build_sms_sender(settings)
    otp_service = OtpService(settings, sms_sender)
    payment_service = PaymentService(settings, order_service)

    app.state.menu_service = menu_service
    app.state.table_service = table_service
    app.state.order_service = order_service
    app.state.customer_service = customer_service
    app.state.otp_service = otp_service
    app.state.payment_service = payment_service

    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "HSR Club Dine — scan a table QR, verify your phone with an OTP, browse "
            "the menu, order, and pay by UPI / card (Razorpay) or cash."
        ),
        lifespan=lifespan,
    )

    raw = settings.cors_origins.strip()
    origins = ["*"] if raw == "*" else [o.strip() for o in raw.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(menu.router)
    app.include_router(tables.router)
    app.include_router(orders.router)
    app.include_router(payments.router)
    return app


app = create_app()
