import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.adapters.postgres.connection import engine
from src.adapters.postgres.orm_models import Base
from src.api.routers import entities, relationships, evidence, ingestion
from src.api.routers import query, explain, conflict
from src.api.rate_limit import rate_limit_check

_VERSION = "0.6.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="SCP Knowledge Graph Layer",
    description=(
        "Semantic understanding layer — transforms SCP Memory Core memories into "
        "structured, trustworthy, versioned knowledge.\n\n"
        "**Auth:** Pass your API key in the `X-Api-Key` header. "
        "Keys are configured via the `API_KEYS` environment variable. "
        "Omit the variable to disable auth in development.\n\n"
        "**Rate limit:** 100 requests per 60 seconds per API key."
    ),
    version=_VERSION,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "entities", "description": "Entity CRUD and version history"},
        {"name": "relationships", "description": "Relationship CRUD"},
        {"name": "evidence", "description": "Evidence management"},
        {"name": "ingestion", "description": "Memory record ingestion pipeline"},
        {"name": "query", "description": "Graph traversal, neighbors, path discovery"},
        {"name": "explain", "description": "Trust score breakdown and provenance chain"},
        {"name": "conflict", "description": "Conflict queue and resolution"},
        {"name": "system", "description": "Health and spec endpoints"},
    ],
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

_v1_deps = [Depends(rate_limit_check)]

app.include_router(entities.router, prefix="/v1", dependencies=_v1_deps)
app.include_router(relationships.router, prefix="/v1", dependencies=_v1_deps)
app.include_router(evidence.router, prefix="/v1", dependencies=_v1_deps)
app.include_router(ingestion.router, prefix="/v1", dependencies=_v1_deps)
app.include_router(query.router, prefix="/v1", dependencies=_v1_deps)
app.include_router(explain.router, prefix="/v1", dependencies=_v1_deps)
app.include_router(conflict.router, prefix="/v1", dependencies=_v1_deps)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": _VERSION}


@app.get("/v1/openapi.json", include_in_schema=False, tags=["system"])
async def openapi_spec() -> dict:
    """Serve the OpenAPI 3.1 spec at a versioned path."""
    return app.openapi()
