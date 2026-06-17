import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor, require_admin
from app.models.user import User
from app.crud.campaign import campaign as campaign_crud, campaign_run as run_crud, campaign_progress as progress_crud
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignScenarioEntryCreate,
    CampaignScenarioEntryUpdate,
    CampaignScenarioEntryResponse,
    CampaignLaunchRequest,
    CampaignRunResponse,
    CampaignRunProgressResponse,
    CampaignRunReport,
)
from app.schemas.common import MessageResponse
from app.services import campaign_service

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
runs_router = APIRouter(prefix="/campaign-runs", tags=["campaign-runs"])


# ── Campaign library ───────────────────────────────────────────────────────────

@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await campaign_crud.list_active(db)


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    obj_in: CampaignCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await campaign_crud.get_by_slug(db, obj_in.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Campaign with this slug already exists")
    c = await campaign_crud.create(db, obj_in=obj_in, created_by=current_user.id)
    await db.commit()
    return c


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    c = await campaign_crud.get(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    obj_in: CampaignUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await campaign_crud.get(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    c = await campaign_crud.update(db, campaign=c, obj_in=obj_in)
    await db.commit()
    return c


@router.delete("/{campaign_id}", response_model=MessageResponse)
async def delete_campaign(
    campaign_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await campaign_crud.get(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await campaign_crud.delete(db, obj=c)
    await db.commit()
    return MessageResponse(message="Campaign deleted")


# ── Campaign scenario entries ──────────────────────────────────────────────────

@router.get("/{campaign_id}/scenarios", response_model=list[CampaignScenarioEntryResponse])
async def list_campaign_scenarios(
    campaign_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    c = await campaign_crud.get(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await campaign_crud.get_entries(db, campaign_id)


@router.post(
    "/{campaign_id}/scenarios",
    response_model=CampaignScenarioEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_campaign_scenario(
    campaign_id: uuid.UUID,
    obj_in: CampaignScenarioEntryCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await campaign_crud.get(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    from app.crud.scenario import scenario as scenario_crud
    sc = await scenario_crud.get(db, obj_in.scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    entry = await campaign_crud.add_entry(db, campaign_id=campaign_id, obj_in=obj_in)
    await db.commit()
    return entry


@router.put(
    "/{campaign_id}/scenarios/{entry_id}",
    response_model=CampaignScenarioEntryResponse,
)
async def update_campaign_scenario(
    campaign_id: uuid.UUID,
    entry_id: uuid.UUID,
    obj_in: CampaignScenarioEntryUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    entry = await campaign_crud.get_entry(db, entry_id)
    if not entry or entry.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Campaign scenario entry not found")
    entry = await campaign_crud.update_entry(db, entry=entry, obj_in=obj_in)
    await db.commit()
    return entry


@router.delete("/{campaign_id}/scenarios/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_campaign_scenario(
    campaign_id: uuid.UUID,
    entry_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    entry = await campaign_crud.get_entry(db, entry_id)
    if not entry or entry.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Campaign scenario entry not found")
    await campaign_crud.remove_entry(db, entry=entry)
    await db.commit()


# ── Campaign launch ────────────────────────────────────────────────────────────

@router.post(
    "/{campaign_id}/launch",
    response_model=CampaignRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def launch_campaign(
    campaign_id: uuid.UUID,
    obj_in: CampaignLaunchRequest,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    c = await campaign_crud.get(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        run = await campaign_service.launch_campaign(
            db,
            campaign_id=campaign_id,
            course_id=obj_in.course_id,
            started_by=current_user.id,
            organization_id=current_user.organization_id,
            team_id=obj_in.team_id,
            settings=obj_in.settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return run


# ── Campaign runs ──────────────────────────────────────────────────────────────

@runs_router.get("", response_model=list[CampaignRunResponse])
async def list_campaign_runs(
    course_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    if course_id:
        return await run_crud.get_by_course(db, course_id)
    if campaign_id:
        return await run_crud.get_by_campaign(db, campaign_id)
    runs, _ = await run_crud.get_multi(db)
    return runs


@runs_router.get("/{run_id}", response_model=CampaignRunResponse)
async def get_campaign_run(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    return run


@runs_router.get("/{run_id}/progress", response_model=list[CampaignRunProgressResponse])
async def get_campaign_run_progress(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    await campaign_service.sync_progress(db, run_id)
    await db.commit()
    return await run_crud.get_progress(db, run_id)


@runs_router.post("/{run_id}/launch-next", response_model=dict)
async def launch_next_scenario(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    """Launch the next pending scenario in this campaign run."""
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    try:
        scenario_run = await campaign_service.launch_next_scenario(
            db,
            campaign_run=run,
            started_by=current_user.id,
            organization_id=current_user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"scenario_run_id": str(scenario_run.id), "status": scenario_run.status.value}


@runs_router.post("/{run_id}/skip", response_model=CampaignRunProgressResponse)
async def skip_current_scenario(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    """Skip the next pending scenario slot in this campaign run."""
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    try:
        progress = await campaign_service.skip_current_scenario(db, campaign_run=run)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()
    return progress


@runs_router.post("/{run_id}/complete", response_model=CampaignRunResponse)
async def complete_campaign_run(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    if run.status not in ("draft", "active"):
        raise HTTPException(status_code=422, detail=f"Cannot complete a {run.status.value} run")
    run = await run_crud.complete(db, run=run)
    await db.commit()
    return run


@runs_router.post("/{run_id}/abort", response_model=CampaignRunResponse)
async def abort_campaign_run(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    if run.status not in ("draft", "active"):
        raise HTTPException(status_code=422, detail=f"Cannot abort a {run.status.value} run")
    run = await run_crud.abort(db, run=run)
    await db.commit()
    return run


@runs_router.get("/{run_id}/report", response_model=CampaignRunReport)
async def get_campaign_run_report(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    try:
        return await campaign_service.generate_campaign_report(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
