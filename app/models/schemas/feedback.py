"""Post-payment guest feedback: a quick star rating plus an optional comment."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    order_id: str
    rating: int = Field(ge=1, le=5)                 # overall experience
    food_rating: int | None = Field(default=None, ge=1, le=5)
    service_rating: int | None = Field(default=None, ge=1, le=5)
    comment: str = Field(default="", max_length=600)


class Feedback(BaseModel):
    id: str
    order_id: str
    order_code: str
    table_label: str
    phone: str
    customer_name: str | None = None
    rating: int
    food_rating: int | None = None
    service_rating: int | None = None
    comment: str = ""
    created_at: str


class FeedbackList(BaseModel):
    items: list[Feedback]


class FeedbackSummary(BaseModel):
    count: int
    average_rating: float
    average_food: float | None = None
    average_service: float | None = None
