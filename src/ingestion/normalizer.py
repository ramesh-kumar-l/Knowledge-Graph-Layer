import re
import unicodedata


def normalize_name(raw: str) -> str:
    """Canonical form: NFC unicode, collapsed whitespace, title-cased."""
    name = unicodedata.normalize("NFC", raw.strip())
    name = re.sub(r"\s+", " ", name)
    return name.title()


def normalize_for_comparison(name: str) -> str:
    """Lowercase, no punctuation — used for fuzzy and alias matching."""
    name = unicodedata.normalize("NFC", name).lower()
    name = re.sub(r"[^\w\s]", "", name)
    return re.sub(r"\s+", " ", name).strip()


def build_aliases(canonical: str, extras: list[str] | None = None) -> list[str]:
    """Derive alias set: lowercase variant + normalized extras (deduplicated)."""
    aliases: set[str] = set()
    lower = canonical.lower()
    if lower != canonical:
        aliases.add(lower)
    for raw in (extras or []):
        norm = normalize_name(raw)
        if norm != canonical:
            aliases.add(norm)
        lower_alias = raw.strip().lower()
        if lower_alias not in {canonical.lower(), norm.lower()}:
            aliases.add(lower_alias)
    return sorted(aliases - {""})


def normalize_attribute_keys(attrs: dict) -> dict:
    """Lowercase attribute keys, replace spaces/dashes with underscore."""
    return {
        re.sub(r"[\s\-]+", "_", k.lower().strip()): v
        for k, v in attrs.items()
    }
