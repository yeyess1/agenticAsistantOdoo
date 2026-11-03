"""AsyncPostgresSaver wiring (D-08). Tables are created by `init` (V-05)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.settings import Settings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


@asynccontextmanager
async def postgres_checkpointer(settings: Settings) -> AsyncIterator[AsyncPostgresSaver]:
    """Open a connection pool and yield the saver; the pool is closed on exit."""
    pool: AsyncConnectionPool = AsyncConnectionPool(
        conninfo=settings.resolved_database_url,
        max_size=5,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    await pool.open()
    try:
        yield AsyncPostgresSaver(pool)  # type: ignore[arg-type]
    finally:
        await pool.close()
