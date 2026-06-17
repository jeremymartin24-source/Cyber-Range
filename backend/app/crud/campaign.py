import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.campaign import (
    Campaign, CampaignScenarioEntry, CampaignRun, CampaignRunProgress,
    CampaignRunStatus, CampaignRunProgressStatus,
)
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignScenarioEntryCreate, CampaignScenarioEntryUpdate


class CRUDCampaign(CRUDBase[Campaign]):
    async def get_by_slug(self, db: AsyncSession, slug: str) -> Campaign | None:
        result = await db.execute(select(Campaign).where(Campaign.slug == slug))
        return result.scalar_one_or_none()

    async def list_active(self, db: AsyncSession) -> list[Campaign]:
        result = await db.execute(
            select(Campaign).where(Campaign.is_active == True).order_by(Campaign.name)  # noqa: E712
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: CampaignCreate, created_by: uuid.UUID) -> Campaign:
        db_obj = Campaign(
            slug=obj_in.slug,
            name=obj_in.name,
            description=obj_in.description,
            created_by=created_by,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, *, campaign: Campaign, obj_in: CampaignUpdate) -> Campaign:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(campaign, field, value)
        db.add(campaign)
        await db.flush()
        await db.refresh(campaign)
        return campaign

    async def get_entries(self, db: AsyncSession, campaign_id: uuid.UUID) -> list[CampaignScenarioEntry]:
        result = await db.execute(
            select(CampaignScenarioEntry)
            .where(CampaignScenarioEntry.campaign_id == campaign_id)
            .order_by(CampaignScenarioEntry.order_index)
        )
        return list(result.scalars().all())

    async def add_entry(
        self,
        db: AsyncSession,
        *,
        campaign_id: uuid.UUID,
        obj_in: CampaignScenarioEntryCreate,
    ) -> CampaignScenarioEntry:
        db_obj = CampaignScenarioEntry(
            campaign_id=campaign_id,
            scenario_id=obj_in.scenario_id,
            order_index=obj_in.order_index,
            day_offset=obj_in.day_offset,
            is_optional=obj_in.is_optional,
            notes=obj_in.notes,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_entry(self, db: AsyncSession, entry_id: uuid.UUID) -> CampaignScenarioEntry | None:
        result = await db.execute(
            select(CampaignScenarioEntry).where(CampaignScenarioEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def update_entry(
        self,
        db: AsyncSession,
        *,
        entry: CampaignScenarioEntry,
        obj_in: CampaignScenarioEntryUpdate,
    ) -> CampaignScenarioEntry:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(entry, field, value)
        db.add(entry)
        await db.flush()
        await db.refresh(entry)
        return entry

    async def remove_entry(self, db: AsyncSession, *, entry: CampaignScenarioEntry) -> None:
        await db.delete(entry)
        await db.flush()


class CRUDCampaignRun(CRUDBase[CampaignRun]):
    async def get_by_course(self, db: AsyncSession, course_id: uuid.UUID) -> list[CampaignRun]:
        result = await db.execute(
            select(CampaignRun)
            .where(CampaignRun.course_id == course_id)
            .order_by(CampaignRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_campaign(self, db: AsyncSession, campaign_id: uuid.UUID) -> list[CampaignRun]:
        result = await db.execute(
            select(CampaignRun)
            .where(CampaignRun.campaign_id == campaign_id)
            .order_by(CampaignRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_run(
        self,
        db: AsyncSession,
        *,
        campaign_id: uuid.UUID,
        course_id: uuid.UUID,
        started_by: uuid.UUID,
        team_id: uuid.UUID | None = None,
        settings: dict | None = None,
    ) -> CampaignRun:
        db_obj = CampaignRun(
            campaign_id=campaign_id,
            course_id=course_id,
            team_id=team_id,
            started_by=started_by,
            status=CampaignRunStatus.draft,
            settings=settings or {},
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_progress(
        self, db: AsyncSession, campaign_run_id: uuid.UUID
    ) -> list[CampaignRunProgress]:
        result = await db.execute(
            select(CampaignRunProgress)
            .where(CampaignRunProgress.campaign_run_id == campaign_run_id)
            .order_by(CampaignRunProgress.order_index)
        )
        return list(result.scalars().all())

    async def complete(self, db: AsyncSession, *, run: CampaignRun) -> CampaignRun:
        run.status = CampaignRunStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        db.add(run)
        await db.flush()
        await db.refresh(run)
        return run

    async def abort(self, db: AsyncSession, *, run: CampaignRun) -> CampaignRun:
        run.status = CampaignRunStatus.aborted
        run.completed_at = datetime.now(timezone.utc)
        db.add(run)
        await db.flush()
        await db.refresh(run)
        return run


class CRUDCampaignRunProgress(CRUDBase[CampaignRunProgress]):
    async def create_for_entry(
        self,
        db: AsyncSession,
        *,
        campaign_run_id: uuid.UUID,
        campaign_scenario_entry_id: uuid.UUID,
        order_index: int,
    ) -> CampaignRunProgress:
        db_obj = CampaignRunProgress(
            campaign_run_id=campaign_run_id,
            campaign_scenario_entry_id=campaign_scenario_entry_id,
            order_index=order_index,
            status=CampaignRunProgressStatus.pending,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def mark_active(
        self,
        db: AsyncSession,
        *,
        progress: CampaignRunProgress,
        scenario_run_id: uuid.UUID,
    ) -> CampaignRunProgress:
        progress.status = CampaignRunProgressStatus.active
        progress.scenario_run_id = scenario_run_id
        db.add(progress)
        await db.flush()
        await db.refresh(progress)
        return progress

    async def mark_completed(
        self, db: AsyncSession, *, progress: CampaignRunProgress
    ) -> CampaignRunProgress:
        progress.status = CampaignRunProgressStatus.completed
        db.add(progress)
        await db.flush()
        await db.refresh(progress)
        return progress

    async def mark_skipped(
        self, db: AsyncSession, *, progress: CampaignRunProgress
    ) -> CampaignRunProgress:
        progress.status = CampaignRunProgressStatus.skipped
        db.add(progress)
        await db.flush()
        await db.refresh(progress)
        return progress


campaign = CRUDCampaign(Campaign)
campaign_run = CRUDCampaignRun(CampaignRun)
campaign_progress = CRUDCampaignRunProgress(CampaignRunProgress)
