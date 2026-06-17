import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock

from app.main import app
from app.database import get_db
from app.models import Base, Organization, User
from app.models.user import UserRole
from app.crud import user as user_crud, organization as org_crud
from app.schemas.organization import OrganizationCreate
from app.schemas.user import UserCreate
import app.services.auth_service as auth_service_module

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def mock_redis_denylist(monkeypatch):
    monkeypatch.setattr(auth_service_module, "is_token_denylisted", AsyncMock(return_value=False))
    monkeypatch.setattr(auth_service_module, "denylist_token", AsyncMock(return_value=None))


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_org(db: AsyncSession) -> Organization:
    return await org_crud.create(db, obj_in=OrganizationCreate(
        name="Test Org",
        slug="test-org",
        settings={},
    ))


@pytest_asyncio.fixture
async def test_admin(db: AsyncSession, test_org: Organization) -> User:
    return await user_crud.create(db, obj_in=UserCreate(
        email="admin@test.com",
        password="TestPass123!",
        first_name="Test",
        last_name="Admin",
        role=UserRole.admin,
        organization_id=test_org.id,
    ))


@pytest_asyncio.fixture
async def test_student(db: AsyncSession, test_org: Organization) -> User:
    return await user_crud.create(db, obj_in=UserCreate(
        email="student@test.com",
        password="TestPass123!",
        first_name="Test",
        last_name="Student",
        role=UserRole.student,
        organization_id=test_org.id,
    ))


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, test_admin: User) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "TestPass123!"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def student_token(client: AsyncClient, test_student: User) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": "student@test.com", "password": "TestPass123!"})
    return resp.json()["access_token"]
