import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CRUDUser(CRUDBase[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_organization(
        self, db: AsyncSession, organization_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[User], int]:
        from sqlalchemy import func
        count_q = select(func.count()).select_from(User).where(User.organization_id == organization_id)
        count_result = await db.execute(count_q)
        total = count_result.scalar_one()
        result = await db.execute(
            select(User).where(User.organization_id == organization_id).offset(offset).limit(limit)
        )
        return result.scalars().all(), total

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        user = User(
            email=obj_in.email.lower(),
            password_hash=pwd_context.hash(obj_in.password),
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            role=obj_in.role,
            organization_id=obj_in.organization_id,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def update(self, db: AsyncSession, *, obj: User, obj_in: UserUpdate) -> User:
        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(obj, field, value)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def update_password(self, db: AsyncSession, *, obj: User, new_password: str) -> User:
        obj.password_hash = pwd_context.hash(new_password)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def record_login(self, db: AsyncSession, *, obj: User) -> None:
        obj.last_login_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(obj)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)


user = CRUDUser(User)
