from unittest.mock import AsyncMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.services.auth_service as auth_service_module
import app.services.lockout_service as lockout_service_module
from app.crud import organization as org_crud
from app.crud import user as user_crud
from app.database import get_db
from app.main import app
from app.models import Base, Organization, User
from app.models.user import UserRole
from app.rate_limit import limiter as app_limiter
from app.schemas.organization import OrganizationCreate
from app.schemas.user import UserCreate

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
    monkeypatch.setattr(lockout_service_module, "is_locked", AsyncMock(return_value=False))
    monkeypatch.setattr(lockout_service_module, "record_failed", AsyncMock(return_value=1))
    monkeypatch.setattr(lockout_service_module, "clear", AsyncMock(return_value=None))
    # Disable rate limiting in tests — counters accumulate across the session
    app_limiter.enabled = False
    yield
    app_limiter.enabled = True


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


# --- Shared fixtures committed once per session ---


@pytest_asyncio.fixture(scope="session")
async def shared_db():
    async with TestSessionLocal() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture(scope="session")
async def test_org(shared_db: AsyncSession) -> Organization:
    existing = await org_crud.get_by_slug(shared_db, slug="test-org")
    if existing:
        return existing
    org = await org_crud.create(
        shared_db,
        obj_in=OrganizationCreate(
            name="Test Org",
            slug="test-org",
            settings={},
        ),
    )
    await shared_db.commit()
    return org


@pytest_asyncio.fixture(scope="session")
async def test_admin(shared_db: AsyncSession, test_org: Organization) -> User:
    existing = await user_crud.get_by_email(shared_db, email="admin@test.com")
    if existing:
        return existing
    admin = await user_crud.create(
        shared_db,
        obj_in=UserCreate(
            email="admin@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Admin",
            role=UserRole.admin,
            organization_id=test_org.id,
        ),
    )
    await shared_db.commit()
    return admin


@pytest_asyncio.fixture(scope="session")
async def test_instructor(shared_db: AsyncSession, test_org: Organization) -> User:
    existing = await user_crud.get_by_email(shared_db, email="instructor@test.com")
    if existing:
        return existing
    instructor = await user_crud.create(
        shared_db,
        obj_in=UserCreate(
            email="instructor@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Instructor",
            role=UserRole.instructor,
            organization_id=test_org.id,
        ),
    )
    await shared_db.commit()
    return instructor


@pytest_asyncio.fixture(scope="session")
async def test_student(shared_db: AsyncSession, test_org: Organization) -> User:
    existing = await user_crud.get_by_email(shared_db, email="student@test.com")
    if existing:
        return existing
    student = await user_crud.create(
        shared_db,
        obj_in=UserCreate(
            email="student@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Student",
            role=UserRole.student,
            organization_id=test_org.id,
        ),
    )
    await shared_db.commit()
    return student


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, test_admin: User) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "admin@test.com", "password": "TestPass123!"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def student_token(client: AsyncClient, test_student: User) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "student@test.com", "password": "TestPass123!"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def instructor_token(client: AsyncClient, test_instructor: User) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "instructor@test.com", "password": "TestPass123!"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
