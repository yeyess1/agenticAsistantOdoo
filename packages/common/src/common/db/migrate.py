"""Apply idempotent SQL migrations in order (V-05; no external tool)."""

from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path

import psycopg

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(str(resources.files("common.db") / "migrations"))


def list_migrations(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """Migration files `NNN_*.sql`, sorted by name."""
    return sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))


async def apply_migrations(dsn: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Run every migration file. Files must be idempotent (`IF NOT EXISTS`)."""
    applied: list[str] = []
    async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
        for path in list_migrations(directory):
            await conn.execute(path.read_text(encoding="utf-8"))
            applied.append(path.name)
            log.info("applied migration %s", path.name)
    return applied
