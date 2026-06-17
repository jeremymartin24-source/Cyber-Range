import uuid
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.scenario import Scenario, ScenarioRun, Inject, ScenarioRunStatus, InjectStatus


class CRUDScenario(CRUDBase[Scenario]):
    async def get_by_slug(self, db: AsyncSession, slug: str) -> Scenario | None:
        result = await db.execute(select(Scenario).where(Scenario.slug == slug))
        return result.scalar_one_or_none()

    async def list_active(self, db: AsyncSession) -> list[Scenario]:
        result = await db.execute(
            select(Scenario).where(Scenario.is_active == True).order_by(Scenario.name)  # noqa: E712
        )
        return list(result.scalars().all())

    async def create_from_yaml(self, db: AsyncSession, *, parsed: dict) -> Scenario:
        injects_raw = parsed.get("injects", [])
        db_obj = Scenario(
            slug=parsed["id"],
            name=parsed["name"],
            version=parsed.get("version", "1.0.0"),
            difficulty=parsed.get("difficulty", "intermediate"),
            estimated_duration_minutes=parsed.get("estimated_duration_minutes"),
            description=parsed.get("description"),
            objectives=parsed.get("objectives", []),
            ttps=parsed.get("ttps", []),
            yaml_content=parsed,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_from_yaml(self, db: AsyncSession, *, db_obj: Scenario, parsed: dict) -> Scenario:
        db_obj.name = parsed["name"]
        db_obj.version = parsed.get("version", "1.0.0")
        db_obj.difficulty = parsed.get("difficulty", "intermediate")
        db_obj.estimated_duration_minutes = parsed.get("estimated_duration_minutes")
        db_obj.description = parsed.get("description")
        db_obj.objectives = parsed.get("objectives", [])
        db_obj.ttps = parsed.get("ttps", [])
        db_obj.yaml_content = parsed
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


class CRUDScenarioRun(CRUDBase[ScenarioRun]):
    async def get_by_course(
        self, db: AsyncSession, course_id: uuid.UUID
    ) -> list[ScenarioRun]:
        result = await db.execute(
            select(ScenarioRun)
            .where(ScenarioRun.course_id == course_id)
            .order_by(ScenarioRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_runs(self, db: AsyncSession) -> list[ScenarioRun]:
        result = await db.execute(
            select(ScenarioRun).where(ScenarioRun.status == ScenarioRunStatus.active)
        )
        return list(result.scalars().all())

    async def create_run(
        self,
        db: AsyncSession,
        *,
        scenario_id: uuid.UUID,
        course_id: uuid.UUID,
        started_by: uuid.UUID,
        team_id: uuid.UUID | None = None,
        settings: dict | None = None,
    ) -> ScenarioRun:
        now = datetime.now(timezone.utc)
        db_obj = ScenarioRun(
            scenario_id=scenario_id,
            course_id=course_id,
            team_id=team_id,
            started_by=started_by,
            status=ScenarioRunStatus.active,
            started_at=now,
            settings=settings or {},
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def set_incident(
        self, db: AsyncSession, *, run: ScenarioRun, incident_id: uuid.UUID
    ) -> ScenarioRun:
        run.incident_id = incident_id
        db.add(run)
        await db.flush()
        await db.refresh(run)
        return run

    async def complete(self, db: AsyncSession, *, run: ScenarioRun) -> ScenarioRun:
        run.status = ScenarioRunStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        db.add(run)
        await db.flush()
        await db.refresh(run)
        return run

    async def abort(self, db: AsyncSession, *, run: ScenarioRun) -> ScenarioRun:
        run.status = ScenarioRunStatus.aborted
        run.completed_at = datetime.now(timezone.utc)
        db.add(run)
        await db.flush()
        await db.refresh(run)
        return run


class CRUDInject(CRUDBase[Inject]):
    async def get_by_run(
        self, db: AsyncSession, scenario_run_id: uuid.UUID
    ) -> list[Inject]:
        result = await db.execute(
            select(Inject)
            .where(Inject.scenario_run_id == scenario_run_id)
            .order_by(Inject.scheduled_at)
        )
        return list(result.scalars().all())

    async def get_pending_due(self, db: AsyncSession) -> list[Inject]:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Inject).where(
                and_(
                    Inject.status == InjectStatus.pending,
                    Inject.scheduled_at <= now,
                )
            )
        )
        return list(result.scalars().all())

    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        scenario_run_id: uuid.UUID,
        inject_specs: list[dict],
        started_at: datetime,
    ) -> list[Inject]:
        injects = []
        for spec in inject_specs:
            at_minute = spec.get("at_minute", 0)
            scheduled_at = datetime.fromtimestamp(
                started_at.timestamp() + at_minute * 60,
                tz=timezone.utc,
            )
            inject = Inject(
                scenario_run_id=scenario_run_id,
                inject_slug=spec["id"],
                inject_type=spec["type"],
                scheduled_at=scheduled_at,
                payload=spec.get("data", {}),
            )
            db.add(inject)
            injects.append(inject)
        await db.flush()
        for inject in injects:
            await db.refresh(inject)
        return injects

    async def mark_fired(
        self, db: AsyncSession, *, inject: Inject, result: dict
    ) -> Inject:
        inject.status = InjectStatus.fired
        inject.fired_at = datetime.now(timezone.utc)
        inject.result = result
        db.add(inject)
        await db.flush()
        await db.refresh(inject)
        return inject

    async def mark_failed(
        self, db: AsyncSession, *, inject: Inject, error: str
    ) -> Inject:
        inject.status = InjectStatus.failed
        inject.fired_at = datetime.now(timezone.utc)
        inject.result = {"error": error}
        db.add(inject)
        await db.flush()
        await db.refresh(inject)
        return inject

    async def skip(self, db: AsyncSession, *, inject: Inject) -> Inject:
        inject.status = InjectStatus.skipped
        db.add(inject)
        await db.flush()
        await db.refresh(inject)
        return inject


scenario = CRUDScenario(Scenario)
scenario_run = CRUDScenarioRun(ScenarioRun)
inject = CRUDInject(Inject)
