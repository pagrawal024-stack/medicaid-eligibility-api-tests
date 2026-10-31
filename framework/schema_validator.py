"""JSON Schema contract checks for API responses."""
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).parent / "schemas"


@lru_cache
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def assert_matches_schema(body, schema_name: str) -> None:
    errors = sorted(_validator(schema_name).iter_errors(body), key=lambda e: list(e.path))
    if errors:
        lines = [f"  {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]
        raise AssertionError(f"Response does not match schema '{schema_name}':\n" + "\n".join(lines))
