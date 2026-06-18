"""
Seed the database with initial data for a fresh CyberOps Range deployment.

Idempotent — safe to run multiple times. Creates only what doesn't exist.

Environment variables:
  DATABASE_URL          required (set by docker-compose)
  SEED_ADMIN_PASSWORD   admin account password (default: Admin1234!)
  SEED_SKIP             set to "1" to skip seeding entirely
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.crud.campaign import campaign as campaign_crud
from app.crud.course import course as course_crud
from app.crud.course import enrollment as enrollment_crud
from app.crud.endpoint import endpoint as endpoint_crud
from app.crud.organization import organization as org_crud
from app.crud.team import team as team_crud
from app.crud.team import team_member as team_member_crud
from app.crud.user import user as user_crud
from app.database import AsyncSessionLocal
from app.models.campaign import CampaignScenarioEntry
from app.models.endpoint import Endpoint
from app.models.team import TeamMemberRole
from app.models.user import UserRole
from app.schemas.campaign import CampaignCreate
from app.schemas.course import CourseCreate
from app.schemas.endpoint import EndpointCreate
from app.schemas.organization import OrganizationCreate
from app.schemas.team import TeamCreate
from app.schemas.user import UserCreate
from app.services import scenario_service

ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "Admin1234!")

_GREEN = "\033[92m"
_GREY = "\033[90m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"


def _created(msg: str) -> None:
    print(f"  {_GREEN}[created]{_RESET} {msg}")


def _exists(msg: str) -> None:
    print(f"  {_GREY}[exists] {_RESET} {msg}")


async def seed() -> None:  # noqa: C901
    async with AsyncSessionLocal() as db:
        # ── Organization ─────────────────────────────────────────────────────────
        print("\n── Organization")
        org = await org_crud.get_by_slug(db, slug="bmg")
        if not org:
            org = await org_crud.create(
                db,
                obj_in=OrganizationCreate(
                    name="Buckeye Manufacturing Group",
                    slug="bmg",
                    settings={
                        "branding": {"company_name": "Buckeye Manufacturing Group"},
                        "wazuh_agent_prefix": "BMG-",
                        "timezone": "America/New_York",
                        "industry": "manufacturing",
                    },
                ),
            )
            await db.commit()
            _created("Buckeye Manufacturing Group (slug=bmg)")
        else:
            _exists("Buckeye Manufacturing Group")

        # ── Users ────────────────────────────────────────────────────────────────
        print("\n── Users")

        admin = await user_crud.get_by_email(db, email="admin@bmg.example.com")
        if not admin:
            admin = await user_crud.create(
                db,
                obj_in=UserCreate(
                    email="admin@bmg.example.com",
                    password=ADMIN_PASSWORD,
                    first_name="System",
                    last_name="Admin",
                    role=UserRole.admin,
                    organization_id=org.id,
                ),
            )
            await db.commit()
            _created(f"admin@bmg.example.com  (password: {ADMIN_PASSWORD})")
        else:
            _exists("admin@bmg.example.com")

        instructor = await user_crud.get_by_email(db, email="instructor@bmg.example.com")
        if not instructor:
            instructor = await user_crud.create(
                db,
                obj_in=UserCreate(
                    email="instructor@bmg.example.com",
                    password="Instructor1234!",
                    first_name="Jane",
                    last_name="Smith",
                    role=UserRole.instructor,
                    organization_id=org.id,
                ),
            )
            await db.commit()
            _created("instructor@bmg.example.com  (password: Instructor1234!)")
        else:
            _exists("instructor@bmg.example.com")

        student_defs = [
            ("alice@bmg.example.com", "Alice", "Johnson"),
            ("bob@bmg.example.com", "Bob", "Williams"),
            ("carol@bmg.example.com", "Carol", "Davis"),
            ("dave@bmg.example.com", "Dave", "Miller"),
        ]
        students = []
        for email, first, last in student_defs:
            s = await user_crud.get_by_email(db, email=email)
            if not s:
                s = await user_crud.create(
                    db,
                    obj_in=UserCreate(
                        email=email,
                        password="Student1234!",
                        first_name=first,
                        last_name=last,
                        role=UserRole.student,
                        organization_id=org.id,
                    ),
                )
                await db.commit()
                _created(f"{email}  (password: Student1234!)")
            else:
                _exists(email)
            students.append(s)

        # ── Course ───────────────────────────────────────────────────────────────
        print("\n── Course")
        existing_courses = await course_crud.get_by_instructor(db, instructor.id)
        if not existing_courses:
            course = await course_crud.create(
                db,
                obj_in=CourseCreate(
                    organization_id=org.id,
                    name="Introduction to Cybersecurity Operations",
                    description=(
                        "Hands-on SOC analyst training using simulated incidents at BMG. "
                        "Students triage alerts, manage incidents, and practise the full "
                        "detect-contain-recover cycle."
                    ),
                    semester="Fall",
                    year=2025,
                ),
                instructor_id=instructor.id,
            )
            _created("Introduction to Cybersecurity Operations (Fall 2025)")
        else:
            course = existing_courses[0]
            _exists(course.name)

        # ── Enrollments ──────────────────────────────────────────────────────────
        print("\n── Enrollments")
        for student in students:
            e = await enrollment_crud.get_by_course_and_user(
                db, course_id=course.id, user_id=student.id
            )
            if not e:
                await enrollment_crud.enroll(db, course_id=course.id, user_id=student.id)
                _created(f"{student.email} → {course.name}")
            else:
                _exists(student.email)

        # ── Teams ────────────────────────────────────────────────────────────────
        print("\n── Teams")
        team_defs = [
            (
                "Alpha Team",
                [(students[0], TeamMemberRole.lead), (students[1], TeamMemberRole.analyst)],
            ),
            (
                "Beta Team",
                [(students[2], TeamMemberRole.lead), (students[3], TeamMemberRole.analyst)],
            ),
        ]
        for team_name, members in team_defs:
            existing = await team_crud.get_by_course(db, course.id)
            if not any(t.name == team_name for t in existing):
                t = await team_crud.create(
                    db, obj_in=TeamCreate(course_id=course.id, name=team_name)
                )
                for student, role in members:
                    await team_member_crud.add_member(db, t.id, student.id, role)
                await db.commit()
                _created(f"{team_name}  ({len(members)} members)")
            else:
                _exists(team_name)

        # ── Endpoints (simulated BMG network) ────────────────────────────────────
        print("\n── Endpoints")
        endpoint_defs = [
            ("bmg-dc01", "10.0.1.10", "windows", "Windows Server 2022", "Domain Controller"),
            ("bmg-fs01", "10.0.1.11", "windows", "Windows Server 2022", "File Server"),
            ("bmg-web01", "10.0.2.10", "linux", "Ubuntu 22.04 LTS", "Web Server"),
            (
                "WIN-WS-CAROL-01",
                "10.0.3.101",
                "windows",
                "Windows 11 Pro",
                "HR Workstation — Carol Johnson",
            ),
            (
                "WIN-WS-BOB-01",
                "10.0.3.102",
                "windows",
                "Windows 11 Pro",
                "Finance Workstation — Bob Williams",
            ),
        ]
        for hostname, ip, platform, version, description in endpoint_defs:
            result = await db.execute(select(Endpoint).where(Endpoint.hostname == hostname))
            if not result.scalar_one_or_none():
                await endpoint_crud.create(
                    db,
                    obj_in=EndpointCreate(
                        hostname=hostname,
                        ip_address=ip,
                        os_platform=platform,
                        os_version=version,
                        description=description,
                        tags=["simulation"],
                    ),
                    organization_id=org.id,
                )
                await db.commit()
                _created(f"{hostname}  ({ip})")
            else:
                _exists(hostname)

        # ── Scenarios ─────────────────────────────────────────────────────────────
        print("\n── Scenarios")
        yaml_files = await scenario_service.list_scenario_files()
        scenarios = []
        for fname in sorted(yaml_files):
            sc = await scenario_service.import_scenario(db, yaml_path=fname)
            _created(f"{sc.name}  (v{sc.version})")
            scenarios.append(sc)

        # ── Campaign ─────────────────────────────────────────────────────────────
        if len(scenarios) >= 2:
            print("\n── Campaign")
            camp = await campaign_crud.get_by_slug(db, slug="bmg-foundations-arc")
            if not camp:
                camp = await campaign_crud.create(
                    db,
                    obj_in=CampaignCreate(
                        slug="bmg-foundations-arc",
                        name="BMG Foundations Arc",
                        description=(
                            "Two-scenario training arc: phishing response followed by ransomware "
                            "tabletop — the core sequence for Introduction to Cybersecurity Operations."
                        ),
                    ),
                    created_by=admin.id,
                )
                for order_index, sc in enumerate(scenarios[:2], start=1):
                    db.add(
                        CampaignScenarioEntry(
                            campaign_id=camp.id,
                            scenario_id=sc.id,
                            order_index=order_index,
                        )
                    )
                await db.commit()
                _created("BMG Foundations Arc  (phishing → ransomware)")
            else:
                _exists("BMG Foundations Arc")

    print(f"\n{_GREEN}Seed complete.{_RESET}")
    print(f"\n  Admin login: admin@bmg.example.com / {ADMIN_PASSWORD}")
    print(f"  {_YELLOW}!! Change the admin password immediately in production !!{_RESET}\n")


def main() -> None:
    if os.environ.get("SEED_SKIP") == "1":
        print("SEED_SKIP=1 — skipping database seed.")
        return
    asyncio.run(seed())


if __name__ == "__main__":
    main()
