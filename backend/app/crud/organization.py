from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization]):
    async def get_by_slug(self, db: AsyncSession, slug: str) -> Organization | None:
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def list_all(self, db: AsyncSession) -> list[Organization]:
        result = await db.execute(select(Organization).order_by(Organization.name))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: OrganizationCreate) -> Organization:
        org = Organization(
            name=obj_in.name,
            slug=obj_in.slug,
            settings=obj_in.settings,
        )
        db.add(org)
        await db.flush()
        await db.refresh(org)
        return org

    async def update(self, db: AsyncSession, *, obj: Organization, obj_in: OrganizationUpdate) -> Organization:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(obj, field, value)
        await db.flush()
        await db.refresh(obj)
        return obj


organization = CRUDOrganization(Organization)
