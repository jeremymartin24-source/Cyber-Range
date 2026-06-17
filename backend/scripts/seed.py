"""
Seed script: creates default org, users, a sample course, teams, and endpoints.
Run with: python -m scripts.seed
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.crud import organization as org_crud, user as user_crud, course as course_crud
from app.crud import team as team_crud, team_member as team_member_crud, endpoint as endpoint_crud
from app.crud import enrollment as enrollment_crud
from app.schemas.organization import OrganizationCreate
from app.schemas.user import UserCreate
from app.schemas.course import CourseCreate
from app.schemas.team import TeamCreate, TeamMemberAdd
from app.schemas.endpoint import EndpointCreate
from app.models.user import UserRole
from app.models.team import TeamMemberRole


async def seed():
    async with AsyncSessionLocal() as db:
        # Organization
        existing_org = await org_crud.get_by_slug(db, slug="bmg")
        if not existing_org:
            org = await org_crud.create(db, obj_in=OrganizationCreate(
                name="Buckeye Manufacturing Group",
                slug="bmg",
                settings={
                    "branding": {"company_name": "Buckeye Manufacturing Group"},
                    "wazuh_agent_prefix": "BMG-",
                },
            ))
            print(f"Created organization: {org.name} (id={org.id})")
        else:
            org = existing_org
            print(f"Organization already exists: {org.name}")

        # Admin user
        existing_admin = await user_crud.get_by_email(db, email="admin@bmg.example.com")
        if not existing_admin:
            admin = await user_crud.create(db, obj_in=UserCreate(
                email="admin@bmg.example.com",
                password="Admin1234!",
                first_name="System",
                last_name="Admin",
                role=UserRole.admin,
                organization_id=org.id,
            ))
            print(f"Created admin: {admin.email}")
            print("  Default password: Admin1234!  CHANGE IN PRODUCTION")
        else:
            admin = existing_admin
            print(f"Admin already exists: {admin.email}")

        # Instructor user
        existing_instructor = await user_crud.get_by_email(db, email="instructor@bmg.example.com")
        if not existing_instructor:
            instructor = await user_crud.create(db, obj_in=UserCreate(
                email="instructor@bmg.example.com",
                password="Instructor1234!",
                first_name="Jane",
                last_name="Smith",
                role=UserRole.instructor,
                organization_id=org.id,
            ))
            print(f"Created instructor: {instructor.email}")
        else:
            instructor = existing_instructor
            print(f"Instructor already exists: {instructor.email}")

        # Student users
        student_data = [
            ("alice@bmg.example.com", "Alice", "Johnson"),
            ("bob@bmg.example.com", "Bob", "Williams"),
            ("carol@bmg.example.com", "Carol", "Davis"),
            ("dave@bmg.example.com", "Dave", "Miller"),
        ]
        students = []
        for email, first, last in student_data:
            existing = await user_crud.get_by_email(db, email=email)
            if not existing:
                s = await user_crud.create(db, obj_in=UserCreate(
                    email=email,
                    password="Student1234!",
                    first_name=first,
                    last_name=last,
                    role=UserRole.student,
                    organization_id=org.id,
                ))
                print(f"Created student: {s.email}")
                students.append(s)
            else:
                students.append(existing)
                print(f"Student already exists: {email}")

        # Course
        existing_courses = await course_crud.get_by_instructor(db, instructor.id)
        if not existing_courses:
            course = await course_crud.create(db, obj_in=CourseCreate(
                organization_id=org.id,
                name="Introduction to Cybersecurity Operations",
                description="Hands-on SOC analyst training using simulated incidents at BMG.",
                semester="Fall",
                year=2025,
            ), instructor_id=instructor.id)
            print(f"Created course: {course.name}")
        else:
            course = existing_courses[0]
            print(f"Course already exists: {course.name}")

        # Enroll students
        for student in students:
            existing_enrollment = await enrollment_crud.get_by_course_and_user(db, course.id, student.id)
            if not existing_enrollment:
                await enrollment_crud.enroll(db, course.id, student.id)
                print(f"Enrolled {student.email}")

        # Teams
        team_configs = [
            ("Alpha Team", [students[0], students[1]]),
            ("Beta Team", [students[2], students[3]]),
        ]
        for team_name, team_students in team_configs:
            existing_teams = await team_crud.get_by_course(db, course.id)
            team_exists = any(t.name == team_name for t in existing_teams)
            if not team_exists:
                t = await team_crud.create(db, obj_in=TeamCreate(
                    course_id=course.id,
                    name=team_name,
                ))
                print(f"Created team: {t.name}")
                for i, student in enumerate(team_students):
                    role = TeamMemberRole.lead if i == 0 else TeamMemberRole.analyst
                    await team_member_crud.add_member(db, t.id, student.id, role)
                    print(f"  Added {student.email} as {role.value}")
            else:
                print(f"Team already exists: {team_name}")

        # Simulated endpoints
        endpoint_configs = [
            ("bmg-dc01", "10.0.1.10", "windows", "Windows Server 2022", "Domain Controller"),
            ("bmg-fs01", "10.0.1.11", "windows", "Windows Server 2022", "File Server"),
            ("bmg-web01", "10.0.2.10", "linux", "Ubuntu 22.04 LTS", "Web Server"),
            ("bmg-workstation01", "10.0.3.101", "windows", "Windows 11 Pro", "HR Workstation"),
            ("bmg-workstation02", "10.0.3.102", "windows", "Windows 11 Pro", "Finance Workstation"),
        ]
        for hostname, ip, os_platform, os_version, description in endpoint_configs:
            from sqlalchemy import select
            from app.models.endpoint import Endpoint
            result = await db.execute(
                select(Endpoint).where(Endpoint.hostname == hostname)
            )
            existing_ep = result.scalar_one_or_none()
            if not existing_ep:
                ep = await endpoint_crud.create(
                    db,
                    obj_in=EndpointCreate(
                        hostname=hostname,
                        ip_address=ip,
                        os_platform=os_platform,
                        os_version=os_version,
                        description=description,
                        tags=["simulation"],
                    ),
                    organization_id=org.id,
                )
                print(f"Created endpoint: {ep.hostname} ({ep.ip_address})")
            else:
                print(f"Endpoint already exists: {hostname}")

        print("\nSeed complete.")
        print("Credentials:")
        print("  admin@bmg.example.com / Admin1234!")
        print("  instructor@bmg.example.com / Instructor1234!")
        print("  alice@bmg.example.com / Student1234!")


if __name__ == "__main__":
    asyncio.run(seed())
