"""Export and validate the FastAPI OpenAPI contract deterministically."""

import json
from pathlib import Path
from typing import Final

from fastapi.openapi.models import OpenAPI

from app.main import app

OUTPUT_PATH: Final = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    """Validate the application schema and write the canonical JSON document."""
    schema = app.openapi()
    OpenAPI.model_validate(schema)
    output = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    OUTPUT_PATH.write_text(output, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
