"""Export the agent graph as Mermaid (`draw_mermaid`) to compare with ARCHITECTURE §3.1.

Usage: `uv run python scripts/export_graph.py [output.mmd]` (default: docs/graph.mmd).
Builds the graph with inert dependencies: no network, no API key needed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from agent.graph.runtime import GraphDeps
from agent.graph.supervisor import build_graph
from agent.tools.forum import ForumTools
from common.search_provider import DdgsProvider
from common.settings import Settings


def main() -> None:
    settings = Settings(_env_file=None)
    retriever: Any = object()  # never called: only the topology is drawn
    deps = GraphDeps(
        settings=settings,
        retriever=retriever,
        forum=ForumTools(DdgsProvider(), settings),
        models={},
    )
    mermaid = build_graph(deps).get_graph(xray=True).draw_mermaid()
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/graph.mmd")
    out.write_text(mermaid + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
