import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor
from app.models.user import User
from app.models.endpoint import EndpointStatus
from app.crud import endpoint as endpoint_crud
from app.schemas.endpoint import EndpointCreate, EndpointUpdate, EndpointResponse, EndpointActionResponse
from app.schemas.common import MessageResponse
from app.services import decision_service

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


@router.get("", response_model=list[EndpointResponse])
async def list_endpoints(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await endpoint_crud.get_by_organization(
        db, current_user.organization_id, skip=skip, limit=limit
    )


@router.post("", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    obj_in: EndpointCreate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await endpoint_crud.create(
        db, obj_in=obj_in, organization_id=current_user.organization_id
    )


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ep = await endpoint_crud.get(db, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return ep


@router.patch("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: uuid.UUID,
    obj_in: EndpointUpdate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    ep = await endpoint_crud.get(db, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return await endpoint_crud.update(db, db_obj=ep, obj_in=obj_in)


@router.delete("/{endpoint_id}", response_model=MessageResponse)
async def delete_endpoint(
    endpoint_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    ep = await endpoint_crud.get(db, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    await endpoint_crud.delete(db, obj=ep)
    return MessageResponse(message="Endpoint deleted")


@router.post("/{endpoint_id}/isolate", response_model=EndpointActionResponse)
async def isolate_endpoint(
    endpoint_id: uuid.UUID,
    rationale: str | None = None,
    incident_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ep = await endpoint_crud.get(db, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    if ep.status == EndpointStatus.isolated:
        raise HTTPException(status_code=409, detail="Endpoint already isolated")
    ep = await endpoint_crud.set_status(db, endpoint=ep, status=EndpointStatus.isolated)
    await decision_service.endpoint_isolated(
        db,
        user_id=current_user.id,
        endpoint_id=ep.id,
        hostname=ep.hostname,
        incident_id=incident_id,
        rationale=rationale,
    )
    return EndpointActionResponse(
        message=f"{ep.hostname} isolated",
        action="isolated",
        endpoint_id=ep.id,
        new_status=ep.status,
    )


@router.post("/{endpoint_id}/restore", response_model=EndpointActionResponse)
async def restore_endpoint(
    endpoint_id: uuid.UUID,
    rationale: str | None = None,
    incident_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ep = await endpoint_crud.get(db, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    if ep.status != EndpointStatus.isolated:
        raise HTTPException(status_code=409, detail="Endpoint is not isolated")
    ep = await endpoint_crud.set_status(db, endpoint=ep, status=EndpointStatus.active)
    await decision_service.endpoint_restored(
        db,
        user_id=current_user.id,
        endpoint_id=ep.id,
        hostname=ep.hostname,
        incident_id=incident_id,
        rationale=rationale,
    )
    return EndpointActionResponse(
        message=f"{ep.hostname} restored",
        action="restored",
        endpoint_id=ep.id,
        new_status=ep.status,
    )
