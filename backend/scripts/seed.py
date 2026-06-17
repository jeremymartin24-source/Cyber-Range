"""
Seed script: creates the default organization and admin user.
Run with: python -m scripts.seed
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.crud import organization as org_crud, user as user_crud
from app.schemas.organization import OrganizationCreate
from app.schemas.user import UserCreate
from app.models.user import UserRole


async def seed():
    async with AsyncSessionLocal() as db:
        # Create default organization
        existing_org = await org_crud.get_by_slug(db, slug="bmg")
        if not existing_org:
            org = await org_crud.create(db, obj_in=OrganizationCreate(
                name="Buckeye Manufacturing Group",
                slug="bmg",
                settings={"branding": {"company_name": "Buckeye Manufacturing Group"}, "wazuh_agent_prefix": "BMG-"},
            ))
            print(f"Created organization: {org.name} (id={org.id})")
        else:
            org = existing_org
            print(f"Organization already exists: {org.name}")

        # Create admin user
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
            print(f"Created admin user: {admin.email}")
            print("  Default password: Admin1234!")
            print("  CHANGE THIS PASSWORD IMMEDIATELY IN PRODUCTION")
        else:
            print(f"Admin user already exists: {existing_admin.email}")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
