"""Deterministic identifiers (ARCHITECTURE §6.1): re-ingesting the same source is idempotent."""

from __future__ import annotations

from uuid import UUID, uuid5

NAMESPACE = UUID("6f0c1a52-9d1e-5c3b-8a47-0d2f4b7e9a11")


def doc_id_for(source: str) -> UUID:
    return uuid5(NAMESPACE, source)


def point_id_for(doc_id: UUID | str, chunk_index: int) -> UUID:
    return uuid5(NAMESPACE, f"{doc_id}:{chunk_index}")
