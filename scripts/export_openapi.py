"""Export the FastAPI OpenAPI 3.1 spec to docs/openapi.json.

Run from the project root:
    python scripts/export_openapi.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from src.api.main import app  # noqa: E402

output = pathlib.Path(__file__).parent.parent / "docs" / "openapi.json"
output.parent.mkdir(parents=True, exist_ok=True)

schema = app.openapi()
output.write_text(json.dumps(schema, indent=2), encoding="utf-8")
print(f"OpenAPI spec ({schema.get('info', {}).get('version', '?')}) written to {output}")
