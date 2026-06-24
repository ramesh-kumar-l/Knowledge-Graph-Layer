from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.postgres.connection import engine
from src.adapters.postgres.orm_models import Base
from src.api.routers import entities, relationships, evidence, ingestion
from src.api.routers import query, explain


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup if they don't exist (dev convenience; prod uses Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="SCP Knowledge Graph Layer",
    description="Semantic understanding layer — transforms SCP Memory Core into structured, trustworthy knowledge.",
    version="0.4.0",
    lifespan=lifespan,
)

app.include_router(entities.router, prefix="/v1")
app.include_router(relationships.router, prefix="/v1")
app.include_router(evidence.router, prefix="/v1")
app.include_router(ingestion.router, prefix="/v1")
app.include_router(query.router, prefix="/v1")
app.include_router(explain.router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.4.0"}
