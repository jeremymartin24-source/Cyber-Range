from celery import shared_task
from app.workers.celery_app import celery_app


@celery_app.task(name="workers.process_pending_injects")
def process_pending_injects() -> dict:
    """
    Beat task: fire any injects whose scheduled_at has passed and status is pending.
    Runs every 30 seconds via celery beat.
    """
    import asyncio
    from app.database import AsyncSessionLocal
    from app.crud.scenario import inject as inject_crud, scenario_run as run_crud
    from app.services.scenario_service import process_inject
    from app.crud.scenario import inject as inject_crud_mod

    async def _run() -> dict:
        fired = 0
        failed = 0
        async with AsyncSessionLocal() as db:
            pending = await inject_crud.get_pending_due(db)
            for inj in pending:
                # Skip if the run is no longer active
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
