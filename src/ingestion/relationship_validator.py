"""Relationship Validator — enforces entity-type constraints from 12-knowledge-graph-model.md.

Constraint table: (from_type_set | None, to_type_set | None) per RelationshipType.
None means "any entity type is allowed" for that side.
IS_SAME_AS has a special rule: both sides must share the same EntityType.
"""
from src.domain.enums import EntityType, RelationshipType
from src.ingestion.models import CandidateRelationship, RelationshipConstraintViolated

# (allowed_from_types | None, allowed_to_types | None)
# None on either side = unconstrained (any entity type accepted)
_CONSTRAINTS: dict[
    RelationshipType,
    tuple[frozenset[EntityType] | None, frozenset[EntityType] | None],
] = {
    RelationshipType.ASSIGNED_TO: (
        frozenset({EntityType.TASK}),
        frozenset({EntityType.PERSON}),
    ),
    RelationshipType.AUTHORED_BY: (
        frozenset({EntityType.DOCUMENT, EntityType.ARTIFACT}),
        frozenset({EntityType.PERSON}),
    ),
    RelationshipType.WORKS_TOWARD: (
        frozenset({EntityType.TASK, EntityType.PROJECT}),
        frozenset({EntityType.GOAL}),
    ),
    RelationshipType.REPORTS_TO: (
        frozenset({EntityType.PERSON}),
        frozenset({EntityType.PERSON}),
    ),
    RelationshipType.MEMBER_OF: (
        frozenset({EntityType.PERSON}),
        frozenset({EntityType.PROJECT, EntityType.ORGANIZATION}),
    ),
    RelationshipType.DEPENDS_ON: (
        frozenset({EntityType.ARTIFACT, EntityType.PRODUCT, EntityType.PROJECT}),
        frozenset({EntityType.ARTIFACT, EntityType.PRODUCT, EntityType.PROJECT}),
    ),
    RelationshipType.REQUIRES: (
        frozenset({EntityType.ARTIFACT, EntityType.PRODUCT, EntityType.PROJECT}),
        frozenset({EntityType.ARTIFACT, EntityType.PRODUCT, EntityType.PROJECT}),
    ),
    RelationshipType.COLLABORATES_ON: (
        frozenset({EntityType.PERSON}),
        frozenset({EntityType.PERSON, EntityType.PROJECT}),
    ),
    # IS_SAME_AS: handled separately (same-type-only rule)
}

# Relationships that require from_type == to_type
_SAME_TYPE_RELS: frozenset[RelationshipType] = frozenset({
    RelationshipType.IS_SAME_AS,
})


class RelationshipValidator:
    """Validates entity-type constraints for candidate relationships."""

    def validate(
        self, candidate: CandidateRelationship
    ) -> tuple[bool, RelationshipConstraintViolated | None]:
        """Return (True, None) if valid, or (False, violation_event) if not."""
        rel_type = candidate.relationship_type

        # Special rule: IS_SAME_AS requires identical entity types
        if rel_type in _SAME_TYPE_RELS:
            if candidate.from_entity_type != candidate.to_entity_type:
                return False, self._violation(candidate)
            return True, None

        # Check constraint table; unconstrained types always pass
        if rel_type not in _CONSTRAINTS:
            return True, None

        from_allowed, to_allowed = _CONSTRAINTS[rel_type]

        if from_allowed and candidate.from_entity_type not in from_allowed:
            return False, self._violation(candidate)

        if to_allowed and candidate.to_entity_type not in to_allowed:
            return False, self._violation(candidate)

        return True, None

    @staticmethod
    def _violation(candidate: CandidateRelationship) -> RelationshipConstraintViolated:
        return RelationshipConstraintViolated(
            from_entity_id=candidate.from_entity_id,
            to_entity_id=candidate.to_entity_id,
            relationship_type=candidate.relationship_type.value,
            from_entity_type=candidate.from_entity_type.value,
            to_entity_type=candidate.to_entity_type.value,
        )
