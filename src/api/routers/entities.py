from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.domain import (
    Entity, CreateEntityCommand, UpdateEntityCommand,
    EntityType, SubjectType,
)
from src.repositories import EntityRepository
from src.services import TrustScoreService, VersionService
from src.api.deps import entity_repo, trust_score_service, version_service

router = APIRouter(prefix="/entities", tags=["entities"])

EntityRepoDep = Annotated[EntityRepository, Depends(entity_repo)]
TrustSvcDep = Annotated[TrustScoreService, Depends(trust_score_service)]
VersionSvcDep = Annotated[VersionService, Depends(version_service)]


@router.post("/", response_model=Entity, status_code=status.HTTP_201_CREATED)
async def create_entity(
    command: CreateEntityCommand,
    repo: EntityRepoDep,
    trust_svc: TrustSvcDep,
    ver_svc: VersionSvcDep,
) -> Entity:
    entity = await repo.create(command)
    # Create version=1 snapshot (creation record, no diff)
    await ver_svc.create_version_before_write(
        subject_type=SubjectType.ENTITY,
        subject_id=entity.id,
        current_snapshot=entity.to_snapshot(),
        next_version=1,
        changed_by=command.created_by,
        change_reason="created",
    )
    return entity


@router.get("/{entity_id}", response_model=Entity)
async def get_entity(entity_id: UUID, repo: EntityRepoDep) -> Entity:
    entity = await repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/", response_model=list[Entity])
async def list_entities(
    repo: EntityRepoDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Entity]:
    return await repo.list_active(offset=offset, limit=limit)


@router.patch("/{entity_id}", response_model=Entity)
async def update_entity(
    entity_id: UUID,
    command: UpdateEntityCommand,
    repo: EntityRepoDep,
    ver_svc: VersionSvcDep,
) -> Entity:
    entity = await repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Version-before-write (DEC-0006): snapshot current state, then apply update
    await ver_svc.create_version_before_write(
        subject_type=SubjectType.ENTITY,
        subject_id=entity.id,
        current_snapshot=entity.to_snapshot(),
        next_version=entity.version + 1,
        changed_by=command.changed_by,
        change_reason=command.change_reason,
    )
    updated = await repo.update(entity, command)
    return updated


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_entity(
    entity_id: UUID,
    repo: EntityRepoDep,
    changed_by: str = Query("system"),
) -> None:
    entity = await repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    await repo.soft_delete(entity_id, changed_by)


@router.get("/search/", response_model=list[Entity])
async def search_entities(
    repo: EntityRepoDep,
    q: str = Query(min_length=1),
    type: EntityType | None = Query(None),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
) -> list[Entity]:
    return await repo.search_by_name(
        query=q,
        entity_type=type,
        min_confidence=min_confidence,
        limit=limit,
    )


@router.get("/{entity_id}/versions")
async def get_entity_versions(
    entity_id: UUID,
    repo: EntityRepoDep,
    ver_svc: VersionSvcDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    entity = await repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return await ver_svc.get_history(
        SubjectType.ENTITY, entity_id, offset=offset, limit=limit
    )
