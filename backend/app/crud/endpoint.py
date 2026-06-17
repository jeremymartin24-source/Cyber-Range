import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.endpoint import Endpoint, EndpointStatus
from app.schemas.endpoint import EndpointCreate, EndpointUpdate


class CRUDEndpoint(CRUDBase[Endpoint]):
    async def get_by_organization(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Endpoint]:
        result = await db.execute(
            select(Endpoint)
            .where(Endpoint.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_wazuh_agent(
        self, db: AsyncSession, wazuh_agent_id: str
    ) -> Endpoint | None:
        result = await db.execute(
            select(Endpoint).where(Endpoint.wazuh_agent_id == wazuh_agent_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: EndpointCreate,
        organization_id: uuid.UUID,
    ) -> Endpoint:
        db_obj = Endpoint(
            organization_id=organization_id,
            wazuh_agent_id=obj_in.wazuh_agent_id,
            hostname=obj_in.hostname,
            ip_address=obj_in.ip_address,
            os_platform=obj_in.os_platform,
            os_version=obj_in.os_version,
            description=obj_in.description,
            tags=obj_in.tags,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: Endpoint, obj_in: EndpointUpdate
    ) -> Endpoint:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def set_status(
        self, db: AsyncSession, *, endpoint: Endpoint, status: EndpointStatus
    ) -> Endpoint:
        endpoint.status = status
        db.add(endpoint)
        await db.commit()
        await db.refresh(endpoint)
        return endpoint


endpoint = CRUDEndpoint(Endpoint)
