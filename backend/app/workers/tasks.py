import asyncio
from datetime import UTC

from app.workers.celery_app import celery_app


@celery_app.task(name="workers.process_pending_injects")
def process_pending_injects() -> dict:
    """
    Beat task: fire any injects whose scheduled_at has passed and status is pending.
    Runs every 30 seconds via celery beat.
    """
    from app.crud.scenario import inject as inject_crud
    from app.crud.scenario import scenario_run as run_crud
    from app.database import AsyncSessionLocal
    from app.services.scenario_service import process_inject

    async def _run() -> dict:
        fired = 0
        failed = 0
        async with AsyncSessionLocal() as db:
            pending = await inject_crud.get_pending_due(db)
            for inj in pending:
                run = await run_crud.get(db, inj.scenario_run_id)
                if not run or run.status != "active":
                    await inject_crud.skip(db, inject=inj)
                    await db.commit()
                    continue
                try:
                    result = await process_inject(db, inject=inj)
                    await inject_crud.mark_fired(db, inject=inj, result=result)
                    fired += 1
                except Exception as exc:
                    await inject_crud.mark_failed(db, inject=inj, error=str(exc))
                    failed += 1
                await db.commit()
        return {"fired": fired, "failed": failed}

    return asyncio.run(_run())


@celery_app.task(name="workers.poll_wazuh_alerts")
def poll_wazuh_alerts() -> dict:
    """
    Beat task: poll Wazuh for new alerts and ingest them for all organizations.
    Skipped silently when WAZUH_URL is not configured.
    Runs every WAZUH_POLL_INTERVAL_SECONDS seconds (default 60) via celery beat.
    """
    from app.config import settings

    if not settings.wazuh_enabled:
        return {"skipped": True, "reason": "Wazuh not configured"}

    import structlog

    from app.crud.alert import alert as alert_crud
    from app.crud.organization import organization as org_crud
    from app.database import AsyncSessionLocal
    from app.integrations.wazuh.client import WazuhUnavailable, wazuh_client
    from app.integrations.wazuh.normalizer import normalize_batch

    log = structlog.get_logger(__name__)

    async def _run() -> dict:
        try:
            # Try connectivity first — fail fast without error spam
            if not await wazuh_client.is_available():
                return {"skipped": True, "reason": "Wazuh unreachable"}

            ingested_total = 0
            duplicate_total = 0

            # Poll alerts (last 5 minutes worth, relying on dedup for idempotency)
            from datetime import datetime, timedelta

            cutoff = datetime.now(UTC) - timedelta(minutes=5)
            q = f"timestamp>{cutoff.strftime('%Y-%m-%dT%H:%M:%S')}"

            events = await wazuh_client.get_alerts(q=q, limit=500)
            if not events:
                return {"ingested": 0, "duplicates": 0}

            async with AsyncSessionLocal() as db:
                orgs = await org_crud.list_all(db)
                for org in orgs:
                    from sqlalchemy import select

                    from app.models.endpoint import Endpoint

                    result = await db.execute(
                        select(Endpoint.hostname, Endpoint.id).where(
                            Endpoint.organization_id == org.id
                        )
                    )
                    agent_map = {row.hostname: row.id for row in result.all()}
                    normalized = normalize_batch(
                        events, org_id=org.id, agent_endpoint_map=agent_map
                    )

                    for alert_in in normalized:
                        if alert_in.wazuh_alert_id:
                            existing = await alert_crud.get_by_wazuh_id(db, alert_in.wazuh_alert_id)
                            if existing:
                                duplicate_total += 1
                                continue
                        await alert_crud.create(db, obj_in=alert_in)
                        ingested_total += 1

            log.info("wazuh_poll_complete", ingested=ingested_total, duplicates=duplicate_total)
            return {"ingested": ingested_total, "duplicates": duplicate_total}

        except WazuhUnavailable as exc:
            log.warning("wazuh_poll_failed", error=str(exc))
            return {"skipped": True, "reason": str(exc)}

    return asyncio.run(_run())
