"""Unit tests for ingestion normalizer — pure functions, no DB."""
import pytest

from src.ingestion.normalizer import (
    normalize_name,
    normalize_for_comparison,
    build_aliases,
    normalize_attribute_keys,
)


class TestNormalizeName:
    def test_strips_whitespace(self):
        assert normalize_name("  Alice Chen  ") == "Alice Chen"

    def test_title_cases(self):
        assert normalize_name("alice chen") == "Alice Chen"

    def test_collapses_internal_whitespace(self):
        assert normalize_name("Alice   Chen") == "Alice Chen"

    def test_unicode_nfc(self):
        # café — e + combining accent → precomposed form
        nfc = "café"
        nfd = "café"
        assert normalize_name(nfd) == normalize_name(nfc)

    def test_single_word(self):
        assert normalize_name("python") == "Python"

    def test_preserves_title_case(self):
        assert normalize_name("ALICE CHEN") == "Alice Chen"


class TestNormalizeForComparison:
    def test_lowercase(self):
        assert normalize_for_comparison("Alice Chen") == "alice chen"

    def test_removes_punctuation(self):
        assert normalize_for_comparison("Alice, Chen.") == "alice chen"

    def test_collapses_whitespace(self):
        assert normalize_for_comparison("Alice   Chen") == "alice chen"

    def test_same_entity_different_case(self):
        a = normalize_for_comparison("Project Alpha")
        b = normalize_for_comparison("project alpha")
        assert a == b

    def test_handles_hyphens(self):
        result = normalize_for_comparison("test-entity")
        assert "-" not in result


class TestBuildAliases:
    def test_adds_lowercase_variant(self):
        aliases = build_aliases("Alice Chen")
        assert "alice chen" in aliases

    def test_canonical_not_in_aliases(self):
        aliases = build_aliases("alice chen")
        assert "alice chen" not in aliases  # canonical == lowercase, nothing added

    def test_extras_normalized_and_added(self):
        aliases = build_aliases("Alice Chen", extras=["A. Chen", "Alice C."])
        # normalized title-case form is added; lowercase deduped via norm.lower()
        assert "A. Chen" in aliases or "Alice C." in aliases

    def test_deduplicated(self):
        aliases = build_aliases("Alice", extras=["alice", "ALICE"])
        assert len(aliases) == len(set(aliases))

    def test_empty_extras(self):
        aliases = build_aliases("Alice Chen", extras=[])
        assert isinstance(aliases, list)

    def test_no_empty_strings(self):
        aliases = build_aliases("Alice Chen", extras=[""])
        assert "" not in aliases


class TestNormalizeAttributeKeys:
    def test_lowercases_keys(self):
        result = normalize_attribute_keys({"Status": "ACTIVE"})
        assert "status" in result

    def test_replaces_spaces(self):
        result = normalize_attribute_keys({"due date": "2026-07-01"})
        assert "due_date" in result

    def test_replaces_dashes(self):
        result = normalize_attribute_keys({"org-type": "TEAM"})
        assert "org_type" in result

    def test_preserves_values(self):
        result = normalize_attribute_keys({"Status": "ACTIVE", "level": "EXPERT"})
        assert result["status"] == "ACTIVE"
        assert result["level"] == "EXPERT"
