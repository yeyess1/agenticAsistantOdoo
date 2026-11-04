"""Basic NLP for the insights view: normalization, n-grams and lexicon topics (no LLM).

Topic = keyword hits on the question (weight 2 each) + one vote per retrieved documentation
source mapped by its URL path (cited 1.0, retrieved but not cited 0.5). Highest score wins;
no signal at all -> `general`. Cheap, deterministic and easy to explain.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

TOPICS: dict[str, str] = {
    "orm": "ORM y modelos",
    "views": "Vistas",
    "frontend": "Frontend / OWL",
    "security": "Seguridad",
    "api": "API y controladores",
    "reports": "Reportes",
    "modules": "Módulos y datos",
    "actions": "Acciones y menús",
    "testing": "Testing",
    "upgrades": "Migraciones",
    "performance": "Rendimiento",
    "general": "General",
}

# Normalized (lowercase, no accents). Keys of 5+ chars match as word prefixes (`comput` ->
# `computado`); shorter ones only as whole words (`js`, `form`, `data`).
LEXICON: dict[str, tuple[str, ...]] = {
    "orm": (
        "orm",
        "modelo",
        "model",
        "campo",
        "field",
        "comput",
        "compute",
        "recordset",
        "registro",
        "record",
        "dominio",
        "domain",
        "onchange",
        "constraint",
        "restriccion",
        "herencia",
        "inherit",
        "many2one",
        "one2many",
        "many2many",
        "relacion",
        "relational",
        "browse",
        "unlink",
        "api.depends",
        "api.model",
        "sql",
        "mixin",
        "_inherit",
        "related",
    ),
    "views": (
        "vista",
        "view",
        "form",
        "formulario",
        "tree",
        "list",
        "lista",
        "kanban",
        "search view",
        "arch",
        "xpath",
        "calendar",
        "pivot",
        "graph",
        "widget",
        "attrs",
        "invisible",
        "readonly",
        "notebook",
        "statusbar",
    ),
    "frontend": (
        "owl",
        "javascript",
        "js",
        "componente",
        "component",
        "hook",
        "registry",
        "servicio",
        "service",
        "asset",
        "scss",
        "css",
        "patch",
        "client action",
        "template",
        "plantilla",
        "qweb",
        "frontend",
        "web client",
        "usestate",
    ),
    "security": (
        "seguridad",
        "security",
        "acceso",
        "access",
        "permiso",
        "permission",
        "grupo",
        "group",
        "regla",
        "rule",
        "ir.model.access",
        "ir.rule",
        "sudo",
        "multi-company",
        "multicompania",
        "compania",
        "company",
        "privilegio",
        "csv",
    ),
    "api": (
        "api externa",
        "external api",
        "xml-rpc",
        "xmlrpc",
        "json-rpc",
        "jsonrpc",
        "rpc",
        "controller",
        "controlador",
        "http",
        "route",
        "ruta",
        "endpoint",
        "request",
        "webhook",
        "json2",
    ),
    "reports": ("reporte", "report", "pdf", "informe", "imprimir", "print", "wkhtmltopdf"),
    "modules": (
        "modulo",
        "traduc",
        "translat",
        "i18n",
        "module",
        "manifest",
        "__manifest__",
        "addon",
        "data",
        "datos",
        "xml",
        "noupdate",
        "demo",
        "scaffold",
        "instalar",
        "install",
        "dependencia",
    ),
    "actions": ("accion", "action", "menu", "menuitem", "cron", "server action", "boton", "button"),
    "testing": ("test", "tests", "prueba", "tour", "unittest", "transactioncase", "httpcase"),
    "upgrades": (
        "upgrade",
        "migra",
        "migro",
        "openupgrade",
        "actualizar version",
        "nueva version",
        "upgrade script",
    ),
    "performance": (
        "rendimiento",
        "performance",
        "prefetch",
        "cache",
        "optimiz",
        "lento",
        "slow",
        "n+1",
    ),
}

# Documentation URL path fragment -> topic (first match wins; order matters).
DOC_TOPICS: tuple[tuple[str, str], ...] = (
    ("security", "security"),
    ("restrict_data_access", "security"),
    ("company", "security"),
    ("view_", "views"),
    ("firstui", "views"),
    ("basicviews", "views"),
    ("qwebintro", "views"),
    ("sprinkles", "views"),
    ("reports", "reports"),
    ("pdf_reports", "reports"),
    ("external_api", "api"),
    ("external_rpc_api", "api"),
    ("/http", "api"),
    ("testing", "testing"),
    ("unit_tests", "testing"),
    ("upgrades", "upgrades"),
    ("translations", "modules"),
    ("coding_guidelines", "modules"),
    ("performance", "performance"),
    ("actions", "actions"),
    ("frontend", "frontend"),
    ("javascript", "frontend"),
    ("owl", "frontend"),
    ("user_interface", "frontend"),
    ("module", "modules"),
    ("data", "modules"),
    ("newapp", "modules"),
    ("architecture", "modules"),
    ("other_module", "modules"),
    ("cli", "modules"),
    ("orm", "orm"),
    ("mixins", "orm"),
    ("basicmodel", "orm"),
    ("relations", "orm"),
    ("compute", "orm"),
    ("constraints", "orm"),
    ("inheritance", "orm"),
)

_STOPWORDS_TEXT = """
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun cada como con contra
cual cuales cuando de del desde donde dos e el ella ellas ellos en entre era es esa esas ese
eso esos esta estan estas este esto estos fue ha hay hace hacer haga hago la las le les lo los
mas me mi mis mucho muy necesito ni no nos o otra otro para pero poco por puede pueden puedo
que quiero se sea ser si sin sobre son su sus tambien tan te tengo ti tiene tienen todo todos
tu tus un una unas uno unos usar uso y ya yo debo deberia existe hola gracias favor dime
explica explicame pueda puedes hago otros otras manera forma solo ver bien algun cosa
the and or of to in on for with is are be can how do does what which when where why i my
me you your it its this that these those an as at by from use using should would will
odoo
"""
STOPWORDS: frozenset[str] = frozenset(_STOPWORDS_TEXT.split())

_WORD = re.compile(r"[a-z0-9_][a-z0-9_.+-]*[a-z0-9_]|[a-z0-9]")


def normalize(text: str) -> str:
    """Lowercase and strip accents (`Cómo` -> `como`)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    return _WORD.findall(normalize(text))


def content_tokens(text: str) -> list[str]:
    return [t for t in tokenize(text) if t not in STOPWORDS and len(t) > 1 and not t.isdigit()]


def ngrams(tokens: Sequence[str], n: int) -> list[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def frequent_phrases(
    questions: Iterable[str], *, n: int, top: int = 15, min_count: int = 2
) -> list[tuple[str, int]]:
    """Most frequent n-grams of content words, counted once per question (document frequency)."""
    counts: Counter[str] = Counter()
    for q in questions:
        counts.update(set(ngrams(content_tokens(q), n)))
    return [(p, c) for p, c in counts.most_common(top) if c >= min_count]


def _key_pattern(key: str) -> str:
    escaped = re.escape(normalize(key))
    return escaped if len(key) >= 5 else escaped + r"(?![a-z0-9_])"


def _lexicon_patterns() -> dict[str, re.Pattern[str]]:
    return {
        topic: re.compile(r"(?<![a-z0-9_])(?:" + "|".join(_key_pattern(k) for k in keys) + ")")
        for topic, keys in LEXICON.items()
    }


_PATTERNS = _lexicon_patterns()


def doc_topic(url: str) -> str | None:
    """Topic of a documentation source from its URL / file name; None for unknown sources."""
    path = normalize(url).replace("__", "/")
    for fragment, topic in DOC_TOPICS:
        if fragment in path:
            return topic
    return None


def topic_scores(question: str, sources: Sequence[Mapping[str, Any]] = ()) -> dict[str, float]:
    text = normalize(question)
    scores: dict[str, float] = {}
    for topic, pattern in _PATTERNS.items():
        hits = len(pattern.findall(text))
        if hits:
            scores[topic] = scores.get(topic, 0.0) + 2.0 * hits
    for s in sources:
        if s.get("kind", "doc") != "doc":
            continue
        doc = doc_topic(str(s.get("url") or s.get("title") or ""))
        if doc:
            scores[doc] = scores.get(doc, 0.0) + (1.0 if s.get("cited") else 0.5)
    return scores


def classify_topic(question: str, sources: Sequence[Mapping[str, Any]] = ()) -> str:
    scores = topic_scores(question, sources)
    if not scores:
        return "general"
    # Ties: the order of TOPICS decides (stable, deterministic).
    order = list(TOPICS)
    return max(scores, key=lambda t: (scores[t], -order.index(t)))
