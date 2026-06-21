"""Staff sales-analytics dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.security import require_admin
from app.models.schemas.stats import DashboardStats
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=DashboardStats)
async def dashboard(
    request: Request,
    _: str = Depends(require_admin),
) -> DashboardStats:
    service: AnalyticsService = request.app.state.analytics_service
    return await service.dashboard()
