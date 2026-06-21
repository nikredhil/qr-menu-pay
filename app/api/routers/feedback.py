"""Post-payment guest feedback. Diners rate their own (paid) order; staff read."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_feedback_service, get_order_service
from app.core.security import get_current_customer, require_admin
from app.models.schemas.feedback import (
    Feedback,
    FeedbackCreate,
    FeedbackList,
    FeedbackSummary,
)
from app.services.feedback_service import FeedbackError, FeedbackService
from app.services.order_service import OrderNotFoundError, OrderService

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=Feedback, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    phone: str = Depends(get_current_customer),
    orders: OrderService = Depends(get_order_service),
    feedback: FeedbackService = Depends(get_feedback_service),
) -> Feedback:
    try:
        order = await orders.get_for_customer(payload.order_id, phone)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        return await feedback.create(payload, order)
    except FeedbackError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/mine/{order_id}", response_model=Feedback | None)
async def my_feedback(
    order_id: str,
    phone: str = Depends(get_current_customer),
    orders: OrderService = Depends(get_order_service),
    feedback: FeedbackService = Depends(get_feedback_service),
) -> Feedback | None:
    """Lets the order page know whether the diner already left feedback."""
    try:
        await orders.get_for_customer(order_id, phone)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return await feedback.for_order(order_id)


@router.get("", response_model=FeedbackList)
async def list_feedback(
    _: str = Depends(require_admin),
    feedback: FeedbackService = Depends(get_feedback_service),
) -> FeedbackList:
    return FeedbackList(items=await feedback.list())


@router.get("/summary", response_model=FeedbackSummary)
async def feedback_summary(
    _: str = Depends(require_admin),
    feedback: FeedbackService = Depends(get_feedback_service),
) -> FeedbackSummary:
    return await feedback.summary()
