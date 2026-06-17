import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> ModelType | None:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ModelType], int]:
        count_result = await db.execute(select(func.count()).select_from(self.model))
        total = count_result.scalar_one()
        result = await db.execute(select(self.model).offset(offset).limit(limit))
        return result.scalars().all(), total

    async def delete(self, db: AsyncSession, *, obj: ModelType) -> None:
        await db.delete(obj)
        await db.flush()
