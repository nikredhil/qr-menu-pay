"""Payment flow: create an intent, then confirm via Razorpay, the demo gateway,
or cash. All customer-facing endpoints scope to the caller's own order."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.core.dependencies import get_order_service, get_payment_service
from app.core.security import get_current_customer, require_admin
from app.models.schemas.payment import (
    CashConfirm,
    DemoConfirm,
    PaymentIntent,
    PaymentResult,
    RazorpayVerify,
)
from app.services.order_service import OrderNotFoundError, OrderService
from app.services.payment_service import PaymentError, PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


async def _customer_order(order_id: str, phone: str, orders: OrderService):
    try:
        return await orders.get_for_customer(order_id, phone)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


@router.post("/intent", response_model=PaymentIntent)
async def create_intent(
    order_id: str = Body(..., embed=True),
    phone: str = Depends(get_current_customer),
    orders: OrderService = Depends(get_order_service),
    payments: PaymentService = Depends(get_payment_service),
) -> PaymentIntent:
    order = await _customer_order(order_id, phone, orders)
    if order.payment_status == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already paid")
    try:
        return await payments.create_intent(order)
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.post("/razorpay/verify", response_model=PaymentResult)
async def verify_razorpay(
    payload: RazorpayVerify,
    phone: str = Depends(get_current_customer),
    orders: OrderService = Depends(get_order_service),
    payments: PaymentService = Depends(get_payment_service),
) -> PaymentResult:
    order = await _customer_order(payload.order_id, phone, orders)
    try:
        updated = await payments.confirm_razorpay(
            order,
            payload.razorpay_order_id,
            payload.razorpay_payment_id,
            payload.razorpay_signature,
        )
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return PaymentResult(
        order_id=updated.id,
        payment_status=updated.payment_status,
        payment_method=updated.payment_method or "razorpay",
        payment_ref=updated.payment_ref,
    )


@router.post("/demo/confirm", response_model=PaymentResult)
async def confirm_demo(
    payload: DemoConfirm,
    phone: str = Depends(get_current_customer),
    orders: OrderService = Depends(get_order_service),
    payments: PaymentService = Depends(get_payment_service),
) -> PaymentResult:
    """Complete a payment via the built-in demo gateway (no real money)."""
    order = await _customer_order(payload.order_id, phone, orders)
    try:
        updated = await payments.confirm_demo(order, payload.outcome)
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return PaymentResult(
        order_id=updated.id,
        payment_status=updated.payment_status,
        payment_method=updated.payment_method or "razorpay",
        payment_ref=updated.payment_ref,
    )


@router.post("/cash", response_model=PaymentResult)
async def confirm_cash(
    payload: CashConfirm,
    phone: str = Depends(get_current_customer),
    orders: OrderService = Depends(get_order_service),
    payments: PaymentService = Depends(get_payment_service),
) -> PaymentResult:
    """Choose to pay with cash at the counter; staff confirm collection later."""
    order = await _customer_order(payload.order_id, phone, orders)
    updated = await payments.confirm_cash(order)
    return PaymentResult(
        order_id=updated.id,
        payment_status=updated.payment_status,
        payment_method="cash",
        payment_ref=updated.payment_ref,
    )


@router.post("/{order_id}/cash-collected", response_model=PaymentResult)
async def mark_cash_collected(
    order_id: str,
    _: str = Depends(require_admin),
    orders: OrderService = Depends(get_order_service),
    payments: PaymentService = Depends(get_payment_service),
) -> PaymentResult:
    """Staff: record that a cash order was paid at the counter."""
    try:
        order = await orders.get(order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    updated = await payments.mark_cash_collected(order)
    return PaymentResult(
        order_id=updated.id,
        payment_status=updated.payment_status,
        payment_method="cash",
        payment_ref=updated.payment_ref,
    )
