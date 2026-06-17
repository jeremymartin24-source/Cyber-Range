import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import organization as org_crud
from app.database import get_db
from app.dependencies.auth import require_admin, require_instructor
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.organization import OrganizationCreate, OrganizationResponse, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/", response_model=PaginatedResponse)
async def list_organizations(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    orgs, total = await org_crud.get_multi(db, offset=offset, limit=limit)
    return PaginatedResponse(
        items=[OrganizationResponse.model_validate(o) for o in orgs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await org_crud.get_by_slug(db, slug=body.slug)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    org = await org_crud.create(db, obj_in=body)
    return OrganizationResponse.model_validate(org)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    org = await org_crud.get(db, id=org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    org = await org_crud.get(db, id=org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    updated = await org_crud.update(db, obj=org, obj_in=body)
    return OrganizationResponse.model_validate(updated)
