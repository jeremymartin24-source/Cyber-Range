"""
Scenario lifecycle: loading from YAML, launching runs, processing injects.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.alert import alert as alert_crud
from app.crud.incident import incident as incident_crud
from app.crud.scenario import inject as inject_crud
from app.crud.scenario import scenario as scenario_crud
from app.crud.scenario import scenario_run as run_crud
from app.models.incident import IncidentSeverity
from app.models.scenario import Inject, InjectType, Scenario, ScenarioRun
from app.schemas.alert import AlertCreate
from app.schemas.incident import IncidentCreate

SCENARIOS_DIR = Path(__file__).parent.parent.parent / "scenarios"


def _parse_yaml_file(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


async def import_scenario(db: AsyncSession, *, yaml_path: str) -> Scenario:
    full_path = SCENARIOS_DIR / yaml_path
    if not full_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {yaml_path}")

    parsed = _parse_yaml_file(full_path)
    if "id" not in parsed or "name" not in parsed:
        raise ValueError("Scenario YAML must have 'id' and 'name' fields")

    existing = await scenario_crud.get_by_slug(db, slug=parsed["id"])
    if existing:
        updated = await scenario_crud.update_from_yaml(db, db_obj=existing, parsed=parsed)
        await db.commit()
        return updated

    created = await scenario_crud.create_from_yaml(db, parsed=parsed)
    await db.commit()
    return created


async def list_scenario_files() -> list[str]:
    if not SCENARIOS_DIR.exists():
        return []
    return [
        f.name for f in SCENARIOS_DIR.iterdir() if f.suffix in (".yaml", ".yml") and f.is_file()
    ]


async def launch_scenario(
    db: AsyncSession,
    *,
    scenario_id: uuid.UUID,
    course_id: uuid.UUID,
    started_by: uuid.UUID,
    organization_id: uuid.UUID,
    team_id: uuid.UUID | None = None,
    settings: dict | None = None,
) -> ScenarioRun:
    sc = await scenario_crud.get(db, scenario_id)
    if not sc:
        raise ValueError("Scenario not found")

    now = datetime.now(UTC)

    # Create the scenario run
    run = await run_crud.create_run(
        db,
        scenario_id=scenario_id,
        course_id=course_id,
        started_by=started_by,
        team_id=team_id,
        settings=settings or {},
    )

    # Create the associated incident
    inc = await incident_crud.create(
        db,
        obj_in=IncidentCreate(
            organization_id=organization_id,
            title=f"[SCENARIO] {sc.name}",
            description=sc.description,
            severity=IncidentSeverity.medium,
            category="scenario",
            team_id=team_id,
        ),
        created_by=started_by,
    )
    run = await run_crud.set_incident(db, run=run, incident_id=inc.id)

    # Schedule injects from YAML
    inject_specs = sc.yaml_content.get("injects", [])
    if inject_specs:
        await inject_crud.bulk_create(
            db,
            scenario_run_id=run.id,
            inject_specs=inject_specs,
            started_at=now,
        )

    await db.commit()
    await db.refresh(run)
    return run


async def process_inject(db: AsyncSession, *, inject: Inject) -> dict:
    """
    Fire a single inject and return a result dict.
    Called by the Celery task for due injects.
    """
    run = await db.get(ScenarioRun, inject.scenario_run_id)
    if not run or run.status != "active":
        return {"skipped": True, "reason": "run not active"}

    result: dict = {}

    if inject.inject_type == InjectType.alert:
        payload = inject.payload
        # Determine organization from run → incident or course
        # For now, get org from the incident if present
        org_id = await _get_org_id_for_run(db, run)
        if org_id:
            alert = await alert_crud.create(
                db,
                obj_in=AlertCreate(
                    organization_id=org_id,
                    rule_id=payload.get("rule_id"),
                    rule_level=payload.get("rule_level"),
                    rule_description=payload.get("rule_description"),
                    rule_groups=payload.get("rule_groups", []),
                    agent_id=payload.get("agent_id"),
                    agent_name=payload.get("agent_name"),
                    raw_data=payload.get("raw_data", {}),
                    timestamp=datetime.now(UTC),
                    is_simulated=True,
                ),
            )
            result = {"alert_id": str(alert.id), "type": "alert"}
        else:
            result = {"error": "no organization found for run"}

    elif inject.inject_type == InjectType.hint:
        result = {"type": "hint", "message": inject.payload.get("message", "")}

    elif inject.inject_type == InjectType.narrative_update:
        result = {"type": "narrative_update", "update": inject.payload.get("update", "")}

    elif inject.inject_type == InjectType.endpoint_action:
        result = {"type": "endpoint_action", "action": inject.payload.get("action", "unknown")}

    return result


async def _get_org_id_for_run(db: AsyncSession, run: ScenarioRun) -> uuid.UUID | None:
    if run.incident_id:
        from app.models.incident import Incident

        incident = await db.get(Incident, run.incident_id)
        if incident:
            return incident.organization_id
    # Fall back to getting org from course
    from app.models.course import Course

    course = await db.get(Course, run.course_id)
    if course:
        return course.organization_id
    return None
