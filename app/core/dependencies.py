"""FastAPI dependency providers that pull singletons off ``app.state``."""
from __future__ import annotations

from fastapi import Request

from app.services.customer_service import CustomerService
from app.services.feedback_service import FeedbackService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.otp_service import OtpService
from app.services.outlet_service import OutletService
from app.services.payment_service import PaymentService
from app.services.table_service import TableService


def get_menu_service(request: Request) -> MenuService:
    return request.app.state.menu_service


def get_table_service(request: Request) -> TableService:
    return request.app.state.table_service


def get_order_service(request: Request) -> OrderService:
    return request.app.state.order_service


def get_otp_service(request: Request) -> OtpService:
    return request.app.state.otp_service


def get_payment_service(request: Request) -> PaymentService:
    return request.app.state.payment_service


def get_customer_service(request: Request) -> CustomerService:
    return request.app.state.customer_service


def get_feedback_service(request: Request) -> FeedbackService:
    return request.app.state.feedback_service


def get_outlet_service(request: Request) -> OutletService:
    return request.app.state.outlet_service
