"""Integration test fixtures — SQLite in-memory database via aiosqlite.

SQLite is used for portability; production runs PostgreSQL.
The ORM models use JSON (not JSONB) which maps to TEXT in SQLite.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.adapters.postgres.orm_models import Base
from src.adapters.postgres.entity_adapter import PostgresEntityAdapter
from src.adapters.postgres.relationship_adapter import PostgresRelationshipAdapter
from src.adapters.postgres.evidence_adapter import PostgresEvidenceAdapter
from src.adapters.postgres.provenance_adapter import PostgresProvenanceAdapter
from src.adapters.postgres.trust_score_adapter import PostgresTrustScoreAdapter
from src.adapters.postgres.version_adapter import PostgresVersionAdapter

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def session(db_engine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest.fixture
def entity_adapter(session):
    return PostgresEntityAdapter(session)


@pytest.fixture
def relationship_adapter(session):
    return PostgresRelationshipAdapter(session)


@pytest.fixture
def evidence_adapter(session):
    return PostgresEvidenceAdapter(session)


@pytest.fixture
def provenance_adapter(session):
    return PostgresProvenanceAdapter(session)


@pytest.fixture
def trust_score_adapter(session):
    return PostgresTrustScoreAdapter(session)


@pytest.fixture
def version_adapter(session):
    return PostgresVersionAdapter(session)
