"""
Campaign lifecycle: creating runs, advancing through scenario entries, syncing progress.
"""

import uuid
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.campaign import campaign as campaign_crud
from app.crud.campaign import campaign_progress as progress_crud
from app.crud.campaign import campaign_run as run_crud
from app.crud.student_decision import student_decision as decision_crud
from app.models.campaign import CampaignRunProgressStatus, CampaignRunStatus
from app.models.scenario import ScenarioRunStatus
from app.schemas.campaign import (
    CampaignRunReport,
    CampaignRunScenarioSummary,
)
from app.services import scenario_service


async def launch_campaign(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    course_id: uuid.UUID,
    started_by: uuid.UUID,
    organization_id: uuid.UUID,
    team_id: uuid.UUID | None = None,
    settings: dict | None = None,
) -> object:
    """
    Create a CampaignRun and pre-populate CampaignRunProgress rows
    for every entry in the campaign template.  Returns the CampaignRun.
    """
    c = await campaign_crud.get(db, campaign_id)
    if not c:
        raise ValueError("Campaign not found")
    if not c.is_active:
        raise ValueError("Campaign is not active")

    entries = await campaign_crud.get_entries(db, campaign_id)
    if not entries:
        raise ValueError("Campaign has no scenarios — add at least one before launching")

    run = await run_crud.create_run(
        db,
        campaign_id=campaign_id,
        course_id=course_id,
        started_by=started_by,
        team_id=team_id,
        settings=settings or {},
    )

    for entry in sorted(entries, key=lambda e: e.order_index):
        await progress_crud.create_for_entry(
            db,
            campaign_run_id=run.id,
            campaign_scenario_entry_id=entry.id,
            order_index=entry.order_index,
        )

    await db.commit()
    await db.refresh(run)
    return run


async def sync_progress(db: AsyncSession, campaign_run_id: uuid.UUID) -> None:
    """
    Reconcile CampaignRunProgress statuses against the actual ScenarioRun statuses.
    Called at read time so the UI always sees up-to-date progress.
    """
    entries = await run_crud.get_progress(db, campaign_run_id)
    changed = False
    for entry in entries:
        if entry.scenario_run_id and entry.status == CampaignRunProgressStatus.active:
            from app.models.scenario import ScenarioRun

            sr = await db.get(ScenarioRun, entry.scenario_run_id)
            if sr:
                if sr.status == ScenarioRunStatus.completed:
                    entry.status = CampaignRunProgressStatus.completed
                    db.add(entry)
                    changed = True
                elif sr.status == ScenarioRunStatus.aborted:
                    entry.status = CampaignRunProgressStatus.skipped
                    db.add(entry)
                    changed = True
    if changed:
        await db.flush()


async def launch_next_scenario(
    db: AsyncSession,
    *,
    campaign_run: object,
    started_by: uuid.UUID,
    organization_id: uuid.UUID,
) -> object:
    """
    Advance the campaign: launch the next pending scenario.
    Returns the newly created ScenarioRun.
    """
    if campaign_run.status not in (CampaignRunStatus.draft, CampaignRunStatus.active):
        raise ValueError(f"Cannot advance a {campaign_run.status.value} campaign run")

    await sync_progress(db, campaign_run.id)

    progress_entries = await run_crud.get_progress(db, campaign_run.id)
    pending = [p for p in progress_entries if p.status == CampaignRunProgressStatus.pending]
    if not pending:
        raise ValueError("No more pending scenarios in this campaign run")

    next_progress = min(pending, key=lambda p: p.order_index)
    entry = await campaign_crud.get_entry(db, next_progress.campaign_scenario_entry_id)
    if not entry:
        raise ValueError("Campaign scenario entry not found")

    scenario_run = await scenario_service.launch_scenario(
        db,
        scenario_id=entry.scenario_id,
        course_id=campaign_run.course_id,
        started_by=started_by,
        organization_id=organization_id,
        team_id=campaign_run.team_id,
        settings=campaign_run.settings,
    )

    await progress_crud.mark_active(db, progress=next_progress, scenario_run_id=scenario_run.id)

    if campaign_run.status == CampaignRunStatus.draft:
        campaign_run.status = CampaignRunStatus.active
        campaign_run.started_at = datetime.now(UTC)
        db.add(campaign_run)

    await db.commit()
    return scenario_run


async def skip_current_scenario(
    db: AsyncSession,
    *,
    campaign_run: object,
) -> object:
    """Mark the next pending (or currently active) progress entry as skipped."""
    if campaign_run.status not in (CampaignRunStatus.draft, CampaignRunStatus.active):
        raise ValueError(f"Cannot skip in a {campaign_run.status.value} campaign run")

    await sync_progress(db, campaign_run.id)
    progress_entries = await run_crud.get_progress(db, campaign_run.id)

    # Find the lowest-index pending entry
    pending = [p for p in progress_entries if p.status == CampaignRunProgressStatus.pending]
    if not pending:
        raise ValueError("No pending scenarios to skip")

    target = min(pending, key=lambda p: p.order_index)
    return await progress_crud.mark_skipped(db, progress=target)


async def generate_campaign_report(
    db: AsyncSession, campaign_run_id: uuid.UUID
) -> CampaignRunReport:
    run = await run_crud.get(db, campaign_run_id)
    if not run:
        raise ValueError(f"CampaignRun {campaign_run_id} not found")

    c = await campaign_crud.get(db, run.campaign_id)

    await sync_progress(db, campaign_run_id)
    progress_entries = await run_crud.get_progress(db, campaign_run_id)

    from app.crud.scenario import scenario as scenario_crud
    from app.models.scenario import ScenarioRun

    scenarios: list[CampaignRunScenarioSummary] = []
    total_decisions = 0
    status_counts = Counter(str(p.status.value) for p in progress_entries)

    for prog in sorted(progress_entries, key=lambda p: p.order_index):
        entry = await campaign_crud.get_entry(db, prog.campaign_scenario_entry_id)
        sc = await scenario_crud.get(db, entry.scenario_id) if entry else None

        sr = None
        sr_status = None
        dec_count = 0
        if prog.scenario_run_id:
            sr = await db.get(ScenarioRun, prog.scenario_run_id)
            if sr:
                sr_status = sr.status.value
                if sr.incident_id:
                    decisions = await decision_crud.get_by_incident(db, sr.incident_id)
                    dec_count = len(decisions)
                    total_decisions += dec_count

        scenarios.append(
            CampaignRunScenarioSummary(
                order_index=prog.order_index,
                campaign_scenario_entry_id=prog.campaign_scenario_entry_id,
                scenario_id=entry.scenario_id if entry else uuid.UUID(int=0),
                scenario_name=sc.name if sc else "Unknown",
                scenario_slug=sc.slug if sc else "unknown",
                is_optional=entry.is_optional if entry else False,
                progress_status=prog.status.value,
                scenario_run_id=prog.scenario_run_id,
                scenario_run_status=sr_status,
                decisions_count=dec_count,
            )
        )

    return CampaignRunReport(
        campaign_run_id=run.id,
        campaign_name=c.name if c else "Unknown",
        campaign_slug=c.slug if c else "unknown",
        status=run.status.value,
        course_id=run.course_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        scenarios_total=len(progress_entries),
        scenarios_completed=status_counts.get("completed", 0),
        scenarios_pending=status_counts.get("pending", 0),
        scenarios_skipped=status_counts.get("skipped", 0),
        total_decisions=total_decisions,
        scenarios=scenarios,
    )
