from fastapi import APIRouter
from app.api.v1 import (
    auth,
    users,
    organizations,
    courses,
    teams,
    endpoints,
    incidents,
    alerts,
    evidence,
    case_notes,
    decisions,
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
