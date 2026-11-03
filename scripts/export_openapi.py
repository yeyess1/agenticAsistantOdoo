"""Dump the OpenAPI specs of agent and ingestion for the frontend types (U-05).

Usage: `uv run python scripts/export_openapi.py [out_dir]` (default: frontend/openapi).
Builds the FastAPI apps without running their lifespans: no services, no API key needed.
Then `npm run gen:api` (in frontend/) turns them into `src/lib/api/*.gen.ts`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agent.main import create_app
from ingestion.main import app as ingestion_app


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "frontend/openapi")
    out.mkdir(parents=True, exist_ok=True)
    specs = {
        "agent": create_app(with_lifespan=False).openapi(),
        "ingestion": ingestion_app.openapi(),
    }
    for name, spec in specs.items():
        path = out / f"{name}.json"
        path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path} ({len(spec['paths'])} paths)")


if __name__ == "__main__":
    main()
