from __future__ import annotations

import pytest
from ingestion.chunking.tokenizer import CharTokenCounter


@pytest.fixture
def counter() -> CharTokenCounter:
    return CharTokenCounter()
