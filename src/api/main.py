import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.adapters.postgres.connection import engine
from src.adapters.postgres.orm_models import Base
from src.api.routers import entities, relationships, evidence, ingestion
from src.api.routers import query, explain, conflict


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="SCP Knowledge Graph Layer",
    description="Semantic understanding layer — transforms SCP Memory Core into structured, trustworthy knowledge.",
    version="0.5.0",
    lifespan=lifespan,
)

_allowed_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:4173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(entities.router, prefix="/v1")
app.include_router(relationships.router, prefix="/v1")
app.include_router(evidence.router, prefix="/v1")
app.include_router(ingestion.router, prefix="/v1")
app.include_router(query.router, prefix="/v1")
app.include_router(explain.router, prefix="/v1")
app.include_router(conflict.router, prefix="/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.5.0"}
