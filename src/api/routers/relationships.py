from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.domain import (
    Relationship, CreateRelationshipCommand,
    RelationshipType, SubjectType,
)
from src.repositories import RelationshipRepository, EntityRepository
from src.services import VersionService
from src.api.deps import relationship_repo, entity_repo, version_service

router = APIRouter(prefix="/relationships", tags=["relationships"])

RelRepoDep = Annotated[RelationshipRepository, Depends(relationship_repo)]
EntityRepoDep = Annotated[EntityRepository, Depends(entity_repo)]
VersionSvcDep = Annotated[VersionService, Depends(version_service)]


@router.post("/", response_model=Relationship, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    command: CreateRelationshipCommand,
    rel_repo: RelRepoDep,
    ent_repo: EntityRepoDep,
    ver_svc: VersionSvcDep,
) -> Relationship:
    # Validate both entities exist (application-layer referential integrity)
    from_entity = await ent_repo.get_by_id(command.from_entity_id)
    to_entity = await ent_repo.get_by_id(command.to_entity_id)
    if not from_entity:
        raise HTTPException(status_code=422, detail=f"from_entity_id {command.from_entity_id} not found")
    if not to_entity:
        raise HTTPException(status_code=422, detail=f"to_entity_id {command.to_entity_id} not found")

    relationship = await rel_repo.create(command)
    await ver_svc.create_version_before_write(
        subject_type=SubjectType.RELATIONSHIP,
        subject_id=relationship.id,
        current_snapshot=relationship.to_snapshot(),
        next_version=1,
        changed_by=command.created_by,
        change_reason="created",
    )
    return relationship


@router.get("/{rel_id}", response_model=Relationship)
async def get_relationship(rel_id: UUID, rel_repo: RelRepoDep) -> Relationship:
    rel = await rel_repo.get_by_id(rel_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return rel


@router.get("/", response_model=list[Relationship])
async def list_relationships(
    rel_repo: RelRepoDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Relationship]:
    return await rel_repo.list_active(offset=offset, limit=limit)


@router.get("/outbound/{entity_id}", response_model=list[Relationship])
async def get_outbound(
    entity_id: UUID,
    rel_repo: RelRepoDep,
    ent_repo: EntityRepoDep,
    type: RelationshipType | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[Relationship]:
    entity = await ent_repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return await rel_repo.get_outbound(entity_id, rel_type=type, limit=limit)


@router.get("/inbound/{entity_id}", response_model=list[Relationship])
async def get_inbound(
    entity_id: UUID,
    rel_repo: RelRepoDep,
    ent_repo: EntityRepoDep,
    type: RelationshipType | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[Relationship]:
    entity = await ent_repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return await rel_repo.get_inbound(entity_id, rel_type=type, limit=limit)


@router.delete("/{rel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_relationship(
    rel_id: UUID,
    rel_repo: RelRepoDep,
    changed_by: str = Query("system"),
) -> None:
    rel = await rel_repo.get_by_id(rel_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    await rel_repo.soft_delete(rel_id, changed_by)
