from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    auth,
    campaigns,
    case_notes,
    courses,
    decisions,
    endpoints,
    evidence,
    incidents,
    organizations,
    reports,
    scenarios,
    teams,
    users,
    wazuh,
)

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(organizations.router)
router.include_router(courses.router)
router.include_router(teams.router)
router.include_router(endpoints.router)
router.include_router(incidents.router)
router.include_router(alerts.router)
router.include_router(evidence.router)
router.include_router(case_notes.router)
router.include_router(decisions.router)
router.include_router(scenarios.router)
router.include_router(scenarios.runs_router)
router.include_router(wazuh.router)
router.include_router(reports.router)
router.include_router(campaigns.router)
router.include_router(campaigns.runs_router)
