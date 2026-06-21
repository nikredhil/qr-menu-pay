"""Order placement + status. Customers place/track their own orders; staff see
the full board and advance the kitchen status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_customer_service, get_order_service
from app.core.security import get_current_customer, require_admin
from app.models.schemas.order import (
    Order,
    OrderCreate,
    OrderList,
    OrderStatusUpdate,
)
from app.services.customer_service import CustomerService
from app.services.order_service import (
    OrderNotFoundError,
    OrderService,
    OrderValidationError,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    phone: str = Depends(get_current_customer),
    service: OrderService = Depends(get_order_service),
    customers: CustomerService = Depends(get_customer_service),
) -> Order:
    record = await customers.get(phone)
    name = record.get("name") if record else None
    try:
        return await service.create(payload, phone=phone, name=name)
    except OrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/mine", response_model=OrderList)
async def my_orders(
    phone: str = Depends(get_current_customer),
    service: OrderService = Depends(get_order_service),
) -> OrderList:
    return OrderList(items=await service.list(phone=phone))


@router.get("/{order_id}", response_model=Order)
async def get_my_order(
    order_id: str,
    phone: str = Depends(get_current_customer),
    service: OrderService = Depends(get_order_service),
) -> Order:
    try:
        return await service.get_for_customer(order_id, phone)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


# ---- staff board ----

@router.get("", response_model=OrderList)
async def all_orders(
    outlet: str | None = None,
    status: str | None = None,
    _: str = Depends(require_admin),
    service: OrderService = Depends(get_order_service),
) -> OrderList:
    """Staff order board. Optionally scope by ``outlet`` and filter by one or
    more comma-separated ``status`` values (e.g. ``placed,preparing``) — the
    live kitchen board polls this to show only active tickets."""
    statuses = [s.strip() for s in status.split(",") if s.strip()] if status else None
    return OrderList(items=await service.list(outlet_id=outlet, statuses=statuses))


@router.patch("/{order_id}/status", response_model=Order)
async def update_status(
    order_id: str,
    patch: OrderStatusUpdate,
    _: str = Depends(require_admin),
    service: OrderService = Depends(get_order_service),
) -> Order:
    try:
        return await service.set_status(order_id, patch.status)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
