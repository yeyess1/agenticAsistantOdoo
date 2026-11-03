"""E-01: the golden set loads, validates and matches its declared composition."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError
from runners.golden import GoldenItem, GoldenSet, load_golden
from runners.run_eval import select_items, units


def test_golden_set_loads_with_expected_counts() -> None:
    golden = load_golden()
    assert len(golden.items) == 31
    assert golden.counts() == {"covered": 17, "not_covered": 6, "out_of_scope": 4, "follow_up": 4}
    assert set(golden.threads()) == {"fu-relations", "fu-services"}
    pdf_keys = {k for i in golden.items for k in i.section_keys if k[2] is not None}
    assert ("coding_guidelines.pdf", None, 8) in pdf_keys


def _item(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "q99",
        "category": "covered",
        "question": "¿?",
        "question_en": "?",
        "expected_answer": "x",
        "relevant_sections": ["https://e.com/a.html#b"],
        "expected_agent": "docs",
    }
    return {**base, **over}


@pytest.mark.parametrize(
    "over",
    [
        {"expected_agent": "research"},  # category/agent mismatch
        {"relevant_sections": []},  # covered without sections
        {"relevant_sections": ["https://e.com/a.html"]},  # no anchor
        {"category": "follow_up"},  # follow_up without thread/turn
        {"category": "out_of_scope", "expected_agent": "direct"},  # out_of_scope with sections
    ],
)
def test_invalid_items_are_rejected(over: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        GoldenItem.model_validate(_item(**over))


def test_threads_must_have_consecutive_turns() -> None:
    a = _item(id="q01", category="follow_up", thread="t", turn=1)
    b = _item(id="q02", category="follow_up", thread="t", turn=3)
    with pytest.raises(ValidationError):
        GoldenSet.model_validate({"items": [a, b]})
    with pytest.raises(ValidationError):
        GoldenSet.model_validate({"items": [_item(), _item()]})  # duplicated id


def test_select_items_pulls_earlier_turns_and_units_keep_order() -> None:
    golden = load_golden()
    ids = [i.id for i in select_items(golden, ["q29", "q01"])]
    assert ids == ["q01", "q28", "q29"]
    groups = units(select_items(golden, ["q29", "q01"]), "agentic")
    assert [[i.id for i in g] for g in groups] == [["q01"], ["q28", "q29"]]
    # linear has no memory: every item runs on its own
    assert len(units(select_items(golden, ["q29"]), "linear")) == 2
