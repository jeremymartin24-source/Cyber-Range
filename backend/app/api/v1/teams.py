import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import team as team_crud
from app.crud import team_member as team_member_crud
from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.team import (
    TeamCreate,
    TeamMemberAdd,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    course_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if course_id:
        return await team_crud.get_by_course(db, course_id)
    if current_user.role == UserRole.student:
        memberships = await team_member_crud.get_by_user(db, current_user.id)
        teams = []
        for m in memberships:
            t = await team_crud.get(db, m.team_id)
            if t:
                teams.append(t)
        return teams
    return []


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    obj_in: TeamCreate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await team_crud.create(db, obj_in=obj_in)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    t = await team_crud.get(db, team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    return t


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    obj_in: TeamUpdate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    t = await team_crud.get(db, team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    return await team_crud.update(db, db_obj=t, obj_in=obj_in)


@router.delete("/{team_id}", response_model=MessageResponse)
async def delete_team(
    team_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    t = await team_crud.get(db, team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    await team_crud.delete(db, obj=t)
    return MessageResponse(message="Team deleted")


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    t = await team_crud.get(db, team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    return await team_member_crud.get_by_team(db, team_id)


@router.post(
    "/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED
)
async def add_member(
    team_id: uuid.UUID,
    obj_in: TeamMemberAdd,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    t = await team_crud.get(db, team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    existing = await team_member_crud.get_by_team_and_user(db, team_id, obj_in.user_id)
    if existing:
        raise HTTPException(status_code=409, detail="User already on team")
    return await team_member_crud.add_member(db, team_id, obj_in.user_id, obj_in.role)


@router.delete("/{team_id}/members/{user_id}", response_model=MessageResponse)
async def remove_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    m = await team_member_crud.get_by_team_and_user(db, team_id, user_id)
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    await team_member_crud.delete(db, obj=m)
    return MessageResponse(message="Member removed")
