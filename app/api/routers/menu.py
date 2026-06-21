"""Public menu browsing + staff menu management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.dependencies import get_menu_service
from app.core.security import require_admin
from app.models.schemas.menu import (
    CATEGORIES,
    MenuItem,
    MenuItemCreate,
    MenuItemUpdate,
    MenuList,
)
from app.services.menu_service import MenuItemNotFoundError, MenuService

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("", response_model=MenuList)
async def list_menu(
    all_items: bool = False,
    outlet: str | None = None,
    service: MenuService = Depends(get_menu_service),
) -> MenuList:
    """List the menu. Diners see available items only; staff pass all=true.
    Pass ``outlet`` to scope to a single branch (diners derive it from their
    table; omit it and all outlets' items are returned)."""
    items = await service.list(only_available=not all_items, outlet_id=outlet)
    return MenuList(items=items, categories=CATEGORIES)


@router.post("", response_model=MenuItem, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: MenuItemCreate,
    _: str = Depends(require_admin),
    service: MenuService = Depends(get_menu_service),
) -> MenuItem:
    return await service.create(payload)


@router.patch("/{item_id}", response_model=MenuItem)
async def update_item(
    item_id: str,
    patch: MenuItemUpdate,
    _: str = Depends(require_admin),
    service: MenuService = Depends(get_menu_service),
) -> MenuItem:
    try:
        return await service.update(item_id, patch)
    except MenuItemNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_item(
    item_id: str,
    _: str = Depends(require_admin),
    service: MenuService = Depends(get_menu_service),
) -> Response:
    try:
        await service.delete(item_id)
    except MenuItemNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
