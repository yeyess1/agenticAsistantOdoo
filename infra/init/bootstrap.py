"""One-shot bootstrap (C-04): Postgres tables, checkpointer tables, Qdrant collection.

Runs before `agent` and `ingestion` start, so the payload indexes exist before any
point is ingested (D-05). Everything is idempotent: re-running is safe.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from common.db.migrate import apply_migrations
from common.qdrant_repo import ensure_collection
from common.settings import Settings, get_settings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from qdrant_client import AsyncQdrantClient

log = logging.getLogger("init")


async def setup_postgres(settings: Settings) -> None:
    dsn = settings.resolved_database_url
    applied = await apply_migrations(dsn)
    log.info("postgres migrations: %s", ", ".join(applied) or "none")
    # Creates checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations.
    async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
        await saver.setup()
    log.info("langgraph checkpointer tables ready")


async def setup_qdrant(settings: Settings) -> None:
    client = AsyncQdrantClient(url=settings.qdrant_url)
    try:
        created = await ensure_collection(client, settings)
    finally:
        await client.close()
    log.info(
        "qdrant collection %s %s",
        settings.qdrant_collection,
        "created" if created else "already present",
    )


async def run(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    await setup_postgres(settings)
    await setup_qdrant(settings)


def main() -> int:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(name)s %(message)s")
    try:
        asyncio.run(run(settings))
    except Exception:
        log.exception("bootstrap failed")
        return 1
    log.info("bootstrap done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
