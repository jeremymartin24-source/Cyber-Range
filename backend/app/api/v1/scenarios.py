import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user, require_instructor, require_admin
from app.models.user import User
from app.crud import scenario as scenario_crud, scenario_run as run_crud, inject as inject_crud
from app.schemas.scenario import (
    ScenarioResponse,
    ScenarioImportRequest,
    ScenarioLaunchRequest,
    ScenarioRunResponse,
    InjectResponse,
)
from app.schemas.common import MessageResponse
from app.services import scenario_service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# --- Scenario library ---

@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await scenario_crud.list_active(db)


@router.get("/files", response_model=list[str])
async def list_scenario_files(
    current_user: User = Depends(require_admin),
):
    return await scenario_service.list_scenario_files()


@router.post("/import", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def import_scenario(
    obj_in: ScenarioImportRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        sc = await scenario_service.import_scenario(db, yaml_path=obj_in.yaml_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return sc


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    sc = await scenario_crud.get(db, scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return sc


@router.delete("/{scenario_id}", response_model=MessageResponse)
async def delete_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    sc = await scenario_crud.get(db, scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    await scenario_crud.delete(db, obj=sc)
    await db.commit()
    return MessageResponse(message="Scenario deleted")


# --- Scenario runs ---

@router.post("/{scenario_id}/launch", response_model=ScenarioRunResponse, status_code=status.HTTP_201_CREATED)
async def launch_scenario(
    scenario_id: uuid.UUID,
    obj_in: ScenarioLaunchRequest,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    sc = await scenario_crud.get(db, scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if not sc.is_active:
        raise HTTPException(status_code=422, detail="Scenario is not active")
    try:
        run = await scenario_service.launch_scenario(
            db,
            scenario_id=scenario_id,
            course_id=obj_in.course_id,
            started_by=current_user.id,
            organization_id=current_user.organization_id,
            team_id=obj_in.team_id,
            settings=obj_in.settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return run


# --- Scenario run management ---

runs_router = APIRouter(prefix="/scenario-runs", tags=["scenario-runs"])


@runs_router.get("", response_model=list[ScenarioRunResponse])
async def list_runs(
    course_id: uuid.UUID | None = None,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    if course_id:
        return await run_crud.get_by_course(db, course_id)
    return await run_crud.get_active_runs(db)


@runs_router.get("/{run_id}", response_model=ScenarioRunResponse)
async def get_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    return run


@runs_router.post("/{run_id}/abort", response_model=ScenarioRunResponse)
async def abort_run(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    if run.status not in ("pending", "active"):
        raise HTTPException(status_code=422, detail=f"Cannot abort a {run.status} run")
    run = await run_crud.abort(db, run=run)
    await db.commit()
    return run


@runs_router.post("/{run_id}/complete", response_model=ScenarioRunResponse)
async def complete_run(
    run_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    if run.status != "active":
        raise HTTPException(status_code=422, detail="Run is not active")
    run = await run_crud.complete(db, run=run)
    await db.commit()
    return run


@runs_router.get("/{run_id}/injects", response_model=list[InjectResponse])
async def list_injects(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await run_crud.get(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    return await inject_crud.get_by_run(db, run_id)


@runs_router.post("/{run_id}/injects/{inject_id}/fire", response_model=InjectResponse)
async def fire_inject(
    run_id: uuid.UUID,
    inject_id: uuid.UUID,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    inj = await inject_crud.get(db, inject_id)
    if not inj or inj.scenario_run_id != run_id:
        raise HTTPException(status_code=404, detail="Inject not found")
    if inj.status != "pending":
        raise HTTPException(status_code=409, detail=f"Inject already {inj.status}")
    try:
        result = await scenario_service.process_inject(db, inject=inj)
        inj = await inject_crud.mark_fired(db, inject=inj, result=result)
    except Exception as exc:
        inj = await inject_crud.mark_failed(db, inject=inj, error=str(exc))
    await db.commit()
    return inj
