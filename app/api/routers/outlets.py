"""Outlets (branches). Listing is public so the SPA can show a branch name;
create/update/delete is staff-only."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.dependencies import get_outlet_service
from app.core.security import require_admin
from app.models.schemas.outlet import (
    Outlet,
    OutletCreate,
    OutletList,
    OutletUpdate,
)
from app.services.outlet_service import OutletNotFoundError, OutletService

router = APIRouter(prefix="/outlets", tags=["outlets"])


@router.get("", response_model=OutletList)
async def list_outlets(service: OutletService = Depends(get_outlet_service)) -> OutletList:
    return OutletList(items=await service.list())


@router.get("/{outlet_id}", response_model=Outlet)
async def get_outlet(
    outlet_id: str,
    service: OutletService = Depends(get_outlet_service),
) -> Outlet:
    try:
        return await service.get(outlet_id)
    except OutletNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")


@router.post("", response_model=Outlet, status_code=status.HTTP_201_CREATED)
async def create_outlet(
    payload: OutletCreate,
    _: str = Depends(require_admin),
    service: OutletService = Depends(get_outlet_service),
) -> Outlet:
    return await service.create(payload)


@router.patch("/{outlet_id}", response_model=Outlet)
async def update_outlet(
    outlet_id: str,
    patch: OutletUpdate,
    _: str = Depends(require_admin),
    service: OutletService = Depends(get_outlet_service),
) -> Outlet:
    try:
        return await service.update(outlet_id, patch)
    except OutletNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")


@router.delete("/{outlet_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_outlet(
    outlet_id: str,
    _: str = Depends(require_admin),
    service: OutletService = Depends(get_outlet_service),
) -> Response:
    try:
        await service.delete(outlet_id)
    except OutletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
