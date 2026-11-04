# ruff: noqa: E501  (layout tables: one coordinate list per line reads better than wrapped)
"""Architecture diagram in the AWS reference-architecture style (light and dark SVG).

Conventions taken from the AWS Architecture Icons guidelines: nested groups with an icon and
label at the top-left corner, service icons with the label below (no boxes), one consistent
line weight with open arrowheads, numbered black callouts that map to a step list, one color
per flow and dashed lines for the return path.

Usage: `python scripts/diagrams/architecture.py` -> docs/diagrams/architecture-{light,dark}.svg
Brand glyphs: Simple Icons 16.28.0 (CC0), docs/diagrams/icons/simple-icons.json. Trademarks
belong to their owners; they are used only to identify each component.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "diagrams"
ICONS: dict[str, str] = json.loads((OUT / "icons" / "simple-icons.json").read_text())

W, H = 1240, 980
ICON = 56  # service icon size
FONT = "Inter, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"

THEMES = {
    "light": {
        "bg": "#ffffff",
        "ink": "#16191f",
        "muted": "#5f6b7a",
        "line": "#16191f",
        "query": "#1d6fd8",
        "ingest": "#d4590b",
        "logical": "#8d99a8",
        "docker": "#2496ed",
        "docker_bg": "#f4f9fe",
        "net": "#7d8998",
        "net_bg": "#fafbfc",
        "data": "#147eba",
        "data_bg": "#eaf4fb",
        "callout": "#16191f",
        "callout_ink": "#ffffff",
        "panel": "#f7f8fa",
        "panel_line": "#e3e7ec",
        "tile_ring": "#ffffff00",
    },
    "dark": {
        "bg": "#0f141b",
        "ink": "#e8edf3",
        "muted": "#9aa7b6",
        "line": "#e8edf3",
        "query": "#5aa2ff",
        "ingest": "#ff8a3d",
        "logical": "#6b7686",
        "docker": "#4aa8f5",
        "docker_bg": "#111c27",
        "net": "#7d8998",
        "net_bg": "#131a22",
        "data": "#3fa3dd",
        "data_bg": "#12222f",
        "callout": "#e8edf3",
        "callout_ink": "#0f141b",
        "panel": "#151c25",
        "panel_line": "#263140",
        "tile_ring": "#3a4656",
    },
}

# Service icons: (id, x, y, glyph, tile color, glyph color, label, sublabel, label position)
SERVICES = [
    ("user", 70, 400, "user", "#5f6b7a", "#ffffff", "Usuario", "navegador", "below"),
    (
        "frontend",
        270,
        410,
        "nextdotjs",
        "#000000",
        "#ffffff",
        "Frontend",
        "Next.js · :3000",
        "below",
    ),
    (
        "agent",
        490,
        410,
        "langgraph",
        "#1c3c3c",
        "#7fc8ff",
        "Agent",
        "FastAPI + LangGraph · :8000",
        "below",
    ),
    (
        "tei",
        760,
        270,
        "huggingface",
        "#ffd21e",
        "#16191f",
        "Embeddings",
        "TEI · Qwen3-Embedding-0.6B",
        "below",
    ),
    (
        "qdrant",
        760,
        410,
        "qdrant",
        "#dc244c",
        "#ffffff",
        "Qdrant",
        "vectores · HNSW · :6333",
        "below",
    ),
    (
        "postgres",
        760,
        550,
        "postgresql",
        "#4169e1",
        "#ffffff",
        "Postgres",
        "documents · checkpoints",
        "below",
    ),
    (
        "ingestion",
        1030,
        410,
        "fastapi",
        "#009688",
        "#ffffff",
        "Ingestion",
        "FastAPI · :8001",
        "above",
    ),
    (
        "init",
        270,
        600,
        "python",
        "#3776ab",
        "#ffd43b",
        "init",
        "one-shot: migraciones + colección",
        "below",
    ),
    ("llm", 400, 74, "llm", "#191919", "#ffffff", "LLM API", "Anthropic o Gemini", "below"),
    ("forum", 600, 74, "odoo", "#714b67", "#ffffff", "Odoo Forum", "ddgs + site:", "below"),
]

QUERY_STEPS = [
    ("1", "El usuario pregunta en el chat del frontend."),
    ("2", "El proxy reenvía a POST /query/stream del agent."),
    ("3", "El agent embebe la pregunta con TEI (/embed)."),
    ("4", "Busca los chunks más cercanos en Qdrant (HNSW, top 10)."),
    ("5", "Llama al LLM de cada rol: router, grader, generator…"),
    ("6", "Solo en la ruta research: busca y lee posts del foro."),
    ("7", "Lee y guarda la memoria del thread (checkpointer)."),
    ("8", "Devuelve la respuesta con citas [n] en streaming (SSE)."),
]
INGEST_STEPS = [
    ("A", "Sube un PDF, MD o TXT: proxy → POST /documents."),
    ("B", "Parsea, parte en chunks y los embebe con TEI."),
    ("C", "Upsert de vectores en Qdrant, con doc_id en el payload."),
    ("D", "Registra el documento en la tabla documents (mismo doc_id)."),
]


def glyph(name: str, x: float, y: float, size: float, color: str) -> str:
    """A 24x24 glyph centered at (x, y)."""
    s = size / 24
    tx, ty = x - size / 2, y - size / 2
    if name == "user":
        return (
            f'<g transform="translate({tx:.1f} {ty:.1f}) scale({s:.3f})" fill="{color}">'
            '<circle cx="12" cy="7.5" r="4.5"/><path d="M3 21c0-4.6 4-7.5 9-7.5s9 2.9 9 7.5z"/></g>'
        )
    return (
        f'<path transform="translate({tx:.1f} {ty:.1f}) scale({s:.3f})" '
        f'fill="{color}" d="{ICONS[name]}"/>'
    )


def tile(x: float, y: float, size: float, fill: str, ring: str, rx: float = 10) -> str:
    h = size / 2
    stroke = f' stroke="{ring}" stroke-width="1"' if not ring.endswith("00") else ""
    return (
        f'<rect x="{x - h:.1f}" y="{y - h:.1f}" width="{size}" height="{size}" rx="{rx}" '
        f'fill="{fill}"{stroke}/>'
    )


def service(t: dict[str, str], spec: tuple) -> str:
    _id, x, y, name, fill, gcolor, label, sub, pos = spec
    ring = t["tile_ring"]
    parts = [f'<g id="svc-{_id}">']
    if name == "llm":  # two providers share one tile
        parts.append(tile(x, y, ICON, fill, ring))
        parts.append(glyph("anthropic", x - 12, y, 20, "#ffffff"))
        parts.append(glyph("googlegemini", x + 12, y, 20, "#8e75b2"))
    else:
        parts.append(tile(x, y, ICON, fill, ring))
        parts.append(glyph(name, x, y, 32, gcolor))
    if pos == "below":
        ly, sy = y + ICON / 2 + 18, y + ICON / 2 + 34
    else:
        ly, sy = y - ICON / 2 - 26, y - ICON / 2 - 11
    parts.append(
        f'<text x="{x}" y="{ly}" text-anchor="middle" font-size="13.5" font-weight="700" '
        f'fill="{t["ink"]}">{escape(label)}</text>'
    )
    parts.append(
        f'<text x="{x}" y="{sy}" text-anchor="middle" font-size="11" fill="{t["muted"]}">'
        f"{escape(sub)}</text>"
    )
    parts.append("</g>")
    return "".join(parts)


def group(t: dict[str, str], x, y, w, h, label, color, bg, icon=None, dashed=False) -> str:
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{bg}" stroke="{color}" '
        f'stroke-width="1.5"{dash}/>'
    ]
    tx = x + 10
    if icon:
        out.append(f'<rect x="{x}" y="{y}" width="30" height="30" fill="{color}"/>')
        out.append(glyph(icon, x + 15, y + 15, 18, "#ffffff"))
        tx = x + 40
    out.append(
        f'<text x="{tx}" y="{y + 20}" font-size="12.5" font-weight="700" fill="{t["ink"]}">'
        f"{escape(label)}</text>"
    )
    return "".join(out)


def path(points, color, dashed=False, marker="query", width=2) -> str:
    d = "M" + " L".join(f"{px} {py}" for px, py in points)
    dash = ' stroke-dasharray="7 5"' if dashed else ""
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash} '
        f'stroke-linejoin="round" marker-end="url(#arrow-{marker})"/>'
    )


def callout(t: dict[str, str], x, y, text) -> str:
    return (
        f'<g><circle cx="{x}" cy="{y}" r="11" fill="{t["callout"]}"/>'
        f'<text x="{x}" y="{y + 4.2}" text-anchor="middle" font-size="12" font-weight="800" '
        f'fill="{t["callout_ink"]}">{text}</text></g>'
    )


def legend(t: dict[str, str]) -> str:
    x0, y0 = 40, 740
    out = [
        f'<rect x="{x0}" y="{y0}" width="{W - 80}" height="{H - y0 - 30}" rx="8" '
        f'fill="{t["panel"]}" stroke="{t["panel_line"]}"/>'
    ]

    def column(x, title, color, steps):
        col = [
            f'<rect x="{x}" y="{y0 + 22}" width="22" height="4" rx="2" fill="{color}"/>',
            f'<text x="{x + 30}" y="{y0 + 28}" font-size="13" font-weight="700" '
            f'fill="{t["ink"]}">{title}</text>',
        ]
        for i, (n, text) in enumerate(steps):
            cy = y0 + 56 + i * 21
            col.append(callout(t, x + 11, cy - 4, n).replace('r="11"', 'r="9"'))
            col.append(
                f'<text x="{x + 30}" y="{cy}" font-size="12" fill="{t["ink"]}">{escape(text)}</text>'
            )
        return "".join(col)

    out.append(column(x0 + 24, "Consulta", t["query"], QUERY_STEPS))
    out.append(column(x0 + 520, "Ingesta", t["ingest"], INGEST_STEPS))
    kx, ky = x0 + 520, y0 + 160
    keys = [
        (t["query"], False, "flujo de consulta"),
        (t["ingest"], False, "flujo de ingesta"),
        (t["query"], True, "respuesta al usuario"),
        (t["logical"], True, "relación lógica (no es una conexión de red)"),
    ]
    for i, (color, dashed, text) in enumerate(keys):
        x = kx + (i % 2) * 300
        y = ky + (i // 2) * 22
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        out.append(
            f'<line x1="{x}" y1="{y - 4}" x2="{x + 26}" y2="{y - 4}" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
            f'<text x="{x + 34}" y="{y}" font-size="12" fill="{t["muted"]}">{escape(text)}</text>'
        )
    return "".join(out)


def build(theme: str) -> str:
    t = THEMES[theme]
    q, g = t["query"], t["ingest"]
    half = ICON / 2
    body: list[str] = []

    # Groups (outermost first)
    body.append(group(t, 330, 16, 410, 128, "Internet", t["net"], t["net_bg"], dashed=True))
    body.append(
        group(
            t,
            150,
            168,
            1000,
            552,
            "Docker Compose · red interna",
            t["docker"],
            t["docker_bg"],
            "docker",
        )
    )
    body.append(group(t, 668, 206, 184, 432, "Datos y embeddings", t["data"], t["data_bg"]))

    # Query flow (blue): steps 1-7
    body.append(path([(70 + half, 396), (270 - half - 3, 396)], q))  # 1 user -> frontend
    body.append(path([(270 + half, 396), (490 - half - 3, 396)], q))  # 2 frontend -> agent
    body.append(
        path([(490 + half, 396), (612, 396), (612, 270), (760 - half - 3, 270)], q)
    )  # 3 TEI
    body.append(path([(490 + half, 410), (760 - half - 3, 410)], q))  # 4 Qdrant
    body.append(path([(478, 410 - half), (478, 74), (400 + half + 3, 74)], q))  # 5 LLM
    body.append(
        path([(502, 410 - half), (502, 74), (600 - half - 3, 74)], q, dashed=False)
    )  # 6 forum
    body.append(
        path([(490 + half, 424), (632, 424), (632, 550), (760 - half - 3, 550)], q)
    )  # 7 memory
    # 8 response back to the user (dashed)
    body.append(path([(490 - half, 418), (270 + half + 3, 418)], q, dashed=True))
    body.append(path([(270 - half, 418), (70 + half + 3, 418)], q, dashed=True))

    # Ingestion flow (orange): steps A-D
    body.append(
        path(
            [(270 + half, 428), (380, 428), (380, 676), (1030, 676), (1030, 410 + half + 3)],
            g,
            marker="ingest",
        )
    )
    body.append(
        path(
            [(1030 - half, 396), (908, 396), (908, 270), (760 + half + 3, 270)], g, marker="ingest"
        )
    )
    body.append(path([(1030 - half, 410), (760 + half + 3, 410)], g, marker="ingest"))
    body.append(
        path(
            [(1030 - half, 424), (888, 424), (888, 550), (760 + half + 3, 550)], g, marker="ingest"
        )
    )

    # Logical link: the same doc_id ties Qdrant points to the documents row
    body.append(
        f'<line x1="760" y1="482" x2="760" y2="{550 - half - 4}" stroke="{t["logical"]}" '
        f'stroke-width="1.6" stroke-dasharray="3 4"/>'
        f'<text x="768" y="507" font-size="11" font-style="italic" fill="{t["muted"]}">doc_id</text>'
    )

    for spec in SERVICES:
        body.append(service(t, spec))

    # Numbered callouts, placed beside the line they describe (see QUERY_STEPS / INGEST_STEPS)
    query_spots = [
        (170, 382),
        (380, 382),
        (650, 256),
        (690, 396),
        (464, 205),
        (516, 205),
        (690, 536),
        (170, 434),
    ]
    ingest_spots = [(700, 690), (840, 256), (830, 396), (840, 536)]
    for (x, y), (n, _) in zip(query_spots, QUERY_STEPS, strict=True):
        body.append(callout(t, x, y, n))
    for (x, y), (n, _) in zip(ingest_spots, INGEST_STEPS, strict=True):
        body.append(callout(t, x, y, n))

    body.append(legend(t))

    defs = "".join(
        f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" '
        f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>'
        for name, color in (("query", q), ("ingest", g))
    )
    title = "Odoo RAG: arquitectura (consulta e ingesta)"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'font-family="{FONT}" role="img" aria-labelledby="t">'
        f'<title id="t">{title}</title><defs>{defs}</defs>'
        f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>{"".join(body)}</svg>\n'
    )


def main() -> None:
    for theme in THEMES:
        out = OUT / f"architecture-{theme}.svg"
        out.write_text(build(theme), encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
