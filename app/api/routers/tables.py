"""Table lookup (public, for the scanned QR) + staff table management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.dependencies import get_table_service
from app.core.security import require_admin
from app.models.schemas.table import Table, TableCreate, TableList
from app.services.table_service import TableNotFoundError, TableService

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("/{table_id}", response_model=Table)
async def get_table(
    table_id: str,
    service: TableService = Depends(get_table_service),
) -> Table:
    """Resolve a scanned QR code to its table. Public — a diner just scanned it."""
    try:
        return await service.get(table_id)
    except TableNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown table")


@router.get("", response_model=TableList)
async def list_tables(
    outlet: str | None = None,
    _: str = Depends(require_admin),
    service: TableService = Depends(get_table_service),
) -> TableList:
    return TableList(items=await service.list(outlet_id=outlet))


@router.post("", response_model=Table, status_code=status.HTTP_201_CREATED)
async def create_table(
    payload: TableCreate,
    _: str = Depends(require_admin),
    service: TableService = Depends(get_table_service),
) -> Table:
    return await service.create(payload)


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_table(
    table_id: str,
    _: str = Depends(require_admin),
    service: TableService = Depends(get_table_service),
) -> Response:
    try:
        await service.delete(table_id)
    except TableNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown table")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
