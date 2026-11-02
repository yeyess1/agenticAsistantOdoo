# Backlog y Bitácora — Prueba Técnica AI Developer

Asistente agéntico de conocimiento para desarrolladores (RAG orquestado como grafo de agentes).


## Leyenda

**Estado:** `⬜ Por hacer` · `🔄 En curso` · `✅ Hecho` · `⏸️ Bloqueado` · `❌ Descartado`
**Tipo:** `OBL` obligatorio · `OPC` reto opcional (bonus hasta +15%) · `ENT` entregable · `DEC` decisión de diseño
**Prioridad:** P0 (crítico) · P1 (importante) · P2 (deseable)

> Regla de oro de diseño: los retos opcionales (A–F) deben poder añadirse sin cambios estructurales.
> Cada decisión se registra en la sección "Registro de decisiones" y se referencia desde la tarea.

## Criterios de evaluación (para priorizar)

| Criterio | Peso |
|---|---|
| Diseño agéntico y multi-agente | 30% |
| Justificación y evaluación | 20% |
| Calidad del RAG | 15% |
| Calidad de código | 15% |
| Infraestructura | 10% |
| Documentación e interfaz | 10% |
| Retos opcionales | +15% |

## Reglas innegociables

- [ ] Ninguna API key en repo ni en historial Git (`.env.example` documentado).
- [ ] Sin plataformas no-code ni agentes prefabricados: grafo con código propio.
- [ ] Levantar en máquina limpia solo agregando API keys al `.env`.
- [ ] Historial de commits que muestre el avance.

---

## 0. Decisiones iniciales (fase actual)

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| D-01 | DEC | Alcance: qué retos opcionales se implementan y en qué orden | ✅ Hecho | P0 | Núcleo: E → C → F → A. Stretch: D → B. Todos con enganche desde inicio. Ver ADR D-01 |
| D-02 | DEC | Framework de grafos (LangGraph / otro) y modelado del estado tipado | ✅ Hecho | P0 | LangGraph; estado TypedDict + reducers; Pydantic para salidas LLM y API; docs agent como subgrafo; tool loop propio. Ver ADR D-02 |
| D-03 | DEC | LLM(s) a usar (supervisor/grader/generator) y proveedor | ✅ Hecho | P0 | Anthropic. Haiku 5.5: router/grader/rewriter/contextualizador. Sonnet 5.5: generator/investigación. Opus 5.5: juez eval (D-12). Modelo por rol vía `.env`. Ver ADR D-03 |
| D-04 | DEC | Modelo de embeddings | ✅ Hecho | P0 | `Qwen/Qwen3-Embedding-0.6B` vía sentence-transformers, GPU con fallback CPU, tras interfaz `Embedder`. Ver ADR D-04 |
| D-05 | DEC | Base de datos vectorial y parámetros del índice (HNSW) | ✅ Hecho | P0 | Qdrant; `dense` 1024 coseno + `sparse` BM25/IDF reservado; HNSW m=16, ef_construct=200, hnsw_ef=128; payload indexes previos; recall HNSW vs exacto medido. Ver ADR D-05 |
| D-06 | DEC | Estrategia de chunking (tamaño, solapamiento, encabezados/semántico) | ✅ Hecho (condicional) | P0 | Jerárquico: normalizar a MD → corte por H1–H3 → recursivo ~512 tok / overlap ~64; código nunca se corta. Revisar al cerrar D-11. Ver ADR D-06 |
| D-07 | DEC | Herramienta externa del subagente de investigación (Tavily / DDG / GitHub) | ✅ Hecho | P1 | Tools propias: `search_odoo_forum` (ddgs + `site:` + allowlist) y `read_forum_post`. SearXNG solo plan B documentado. Ver ADR D-07 |
| D-08 | DEC | Persistencia de memoria por `thread_id` (checkpointer) | ✅ Hecho | P1 | `AsyncPostgresSaver` + tabla `documents` (registro relacional); recorte de historial; nodo de contextualización de consulta. Ver ADR D-08 |
| D-09 | DEC | Stack de interfaz de chat | ✅ Hecho | P1 | Next.js 16 + React 19 + Tailwind 4 adaptando frontend propio previo (agenteBBVA) + dashboard recharts. Fases v1/v2/v3. Ver ADR D-09 |
| D-10 | DEC | Arquitectura de servicios y estructura del monorepo | ✅ Hecho | P0 | frontend, agent, ingestion, init, embeddings (TEI), qdrant, postgres + profiles opcionales; revisado con skills `docker/skills`. Ver ADR D-10 |
| D-11 | DEC | Dataset de documentación técnica (20–100 docs, ≥1 PDF) | ✅ Hecho | P0 | ~60 páginas curadas de Odoo 19 Developer (CC BY-SA 4.0) por scraping → snapshot MD versionado + PDF de Coding guidelines. Ver ADR D-11 |
| D-12 | DEC | Framework de evaluación (Ragas / DeepEval / LLM-as-judge propio) | ✅ Hecho | P1 | Implementación propia sin Ragas: métricas deterministas sobre golden set + LLM-juez Opus 5.5 (faithfulness, answer relevancy, answer correctness). Ver ADR D-12 |
| D-13 | DEC | Contrato de extensibilidad para retos opcionales (puntos de enganche) | ✅ Hecho | P0 | Interfaces por `.env`, modelo de eventos tipado, feature flags, `/search`, nodo `confirm_external_search` pasivo. Ver ADR D-13 |
| D-14 | DEC | Gestión de dependencias, lint, tests y convenciones de código | ✅ Hecho | P2 | uv workspace, Python 3.12, Ruff, mypy, pydantic-settings, pytest, gitleaks, pre-commit, Makefile, GH Actions; commits `[ADD]/[FIX]/[DEL] módulo: mensaje` en inglés. Ver ADR D-14 |

---

## 1. Fundación del proyecto

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| F-01 | OBL | Crear repo Git, estructura de carpetas (`services/ingestion`, `services/agent`, `frontend`, `eval`, `docs`) | ⬜ Por hacer | P0 | |
| F-02 | OBL | `.gitignore`, `.env.example` documentado, política de secretos | ⬜ Por hacer | P0 | |
| F-03 | OBL | Configuración de linting/formato/tipado y base de tests | ⬜ Por hacer | P2 | D-14: Ruff, mypy, pytest, pre-commit |
| F-04 | OBL | uv workspace (`pyproject.toml` raíz + miembros) + `uv.lock` | ⬜ Por hacer | P0 | D-14 |
| F-05 | OBL | gitleaks en pre-commit y CI | ⬜ Por hacer | P0 | D-14; regla de no-secretos |
| F-06 | OBL | Makefile (`up`, `up-gpu`, `seed`, `eval`, `test`, `lint`, `down`) | ⬜ Por hacer | P1 | D-14 |
| F-07 | OBL | GitHub Actions: lint, mypy, tests, gitleaks | ⬜ Por hacer | P2 | D-14 |

## 2. Req. 1 — Servicio de ingesta

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| I-01 | OBL | Endpoint de ingesta de PDF, TXT y MD | ⬜ Por hacer | P0 | |
| I-02 | OBL | Parsers por formato (PDF con página; MD con encabezados) | ⬜ Por hacer | P0 | |
| I-03 | OBL | Chunking + justificación documentada (tamaño, overlap, headers/semántico) | ⬜ Por hacer | P0 | |
| I-04 | OBL | Metadatos por chunk: documento origen, página/sección, fecha de ingesta | ⬜ Por hacer | P0 | |
| I-05 | OBL | Generación de embeddings y escritura en vector DB | ⬜ Por hacer | P0 | |
| I-06 | OBL | Endpoints auxiliares (listar/eliminar documentos) | ⬜ Por hacer | P2 | |
| I-07 | OBL | Tests básicos de ingesta y chunking | ⬜ Por hacer | P1 | |
| I-08 | OBL | Scraper CLI: lista curada versionada (config), httpx con pausas + User-Agent, extracción de artículo, HTML→MD con encabezados, anclas y código con lenguaje | ⬜ Por hacer | P0 | D-11 |
| I-09 | OBL | Snapshot `data/corpus/odoo19-dev/*.md` con frontmatter (url, title, fetched_at, license CC BY-SA 4.0) + atribución en README | ⬜ Por hacer | P0 | D-11 |
| I-10 | OBL | Generar PDF de *Coding guidelines* (Chromium headless) e incluirlo en el corpus | ⬜ Por hacer | P1 | D-11; requisito ≥1 PDF |
| I-11 | OBL | Script de carga (`make seed`) que ingesta el snapshot vía endpoint de ingesta | ⬜ Por hacer | P0 | D-11 |
| I-12 | OBL | Calibrar chunking (512/64) con distribución real de tamaños de sección del snapshot | ⬜ Por hacer | P1 | Revisión pendiente D-06 |

## 3. Req. 7 — Base de datos vectorial

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| V-01 | OBL | Levantar vector DB y crear colección/esquema | ⬜ Por hacer | P0 | |
| V-02 | OBL | Configurar índice eficiente (HNSW) y documentar parámetros (m, ef_construct, ef…) | ⬜ Por hacer | P0 | |
| V-03 | OBL | Filtrado por metadatos (p. ej. por documento) | ⬜ Por hacer | P0 | Payload indexes creados antes de ingestar (HNSW filtrable) |
| V-05 | OBL | Postgres: tabla `documents` (doc_id, nombre, fuente, content_hash, modelo de embeddings, n_chunks, estado, fechas) + migraciones | ⬜ Por hacer | P0 | D-08; base para I-06, O-F, O-D |
| V-04 | OBL | Medir recall@k de HNSW vs búsqueda exacta (`exact=true`) con preguntas de eval + latencia | ⬜ Por hacer | P1 | Evidencia empírica de parámetros D-05; forzar construcción HNSW (umbrales) |

## 4. Req. 2 — Supervisor

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| S-01 | OBL | Definir estado tipado del grafo (TypedDict/Pydantic) | ⬜ Por hacer | P0 | |
| S-02 | OBL | Nodo clasificador/router: docs · investigación · respuesta directa | ⬜ Por hacer | P0 | |
| S-03 | OBL | Nodo de respuesta directa (saludo / fuera de alcance) | ⬜ Por hacer | P0 | |
| S-04 | OBL | Delegación a investigación cuando docs responde "sin contexto" | ⬜ Por hacer | P0 | |
| S-05 | OBL | Tests del enrutamiento | ⬜ Por hacer | P1 | |
| S-06 | OBL | Nodo de contextualización: reescribe preguntas de seguimiento como pregunta independiente usando el historial (Haiku), antes del router | ⬜ Por hacer | P0 | D-08 |

## 5. Req. 3 — Subagente de documentación (RAG)

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| R-01 | OBL | Subgrafo con nodos: retriever, grader, rewriter, generator | ⬜ Por hacer | P0 | |
| R-02 | OBL | Grader: relevancia por chunk | ⬜ Por hacer | P0 | |
| R-03 | OBL | Arista condicional + ciclo controlado rewriter → retriever (límite de iteraciones) | ⬜ Por hacer | P0 | |
| R-04 | OBL | Generator con citas (documento + sección) por afirmación | ⬜ Por hacer | P0 | |
| R-05 | OBL | Señal explícita de "sin contexto" hacia el supervisor | ⬜ Por hacer | P0 | |
| R-06 | OBL | Tests del subgrafo (ciclo, límite, sin contexto) | ⬜ Por hacer | P1 | |
| R-07 | OBL | Rewriter bilingüe: puede reformular y/o traducir la consulta ES → EN (corpus en inglés); la respuesta final siempre en español | ⬜ Por hacer | P0 | Consultas en español sobre corpus en inglés (2026-11-02). Medido en E-09 |

## 6. Req. 4 — Subagente de investigación

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| X-01 | OBL | Herramienta externa con esquema tipado (tool calling) | ⬜ Por hacer | P0 | |
| X-02 | OBL | Manejo de errores: timeout, resultado vacío, reintentos | ⬜ Por hacer | P0 | |
| X-03 | OBL | Respuesta marcada como fuente externa + enlaces usados | ⬜ Por hacer | P0 | |
| X-04 | OBL | Tests con herramienta simulada (mock) | ⬜ Por hacer | P1 | |

## 7. Req. 5 — API de consultas

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| A-01 | OBL | Endpoint de consulta en lenguaje natural | ⬜ Por hacer | P0 | |
| A-02 | OBL | Memoria conversacional por `thread_id` | ⬜ Por hacer | P0 | |
| A-03 | OBL | Respuesta con: agente que respondió, nodos recorridos, fuentes | ⬜ Por hacer | P0 | |
| A-04 | OBL | Manejo de errores y validación de esquemas (OpenAPI/Swagger) | ⬜ Por hacer | P1 | |
| A-05 | OBL | Health checks | ⬜ Por hacer | P2 | |
| A-06 | OBL | Modelo de eventos tipado (Pydantic): `node_started`, `node_finished`, `token`, `sources`, `interrupt`, `final`; REST agrega eventos | ⬜ Por hacer | P0 | D-13; base de A-03 y reto C |
| A-07 | OBL | Endpoint `/search` (recuperación pura, filtros, top-k) | ⬜ Por hacer | P0 | D-13; usado por eval (recall@k) y reto A |
| A-08 | OBL | Interfaces en `packages/common`: `Embedder`, `Retriever` (`DenseRetriever`), `Reranker` (no-op), `SearchProvider`, LLM por rol; selección por `.env` | ⬜ Por hacer | P0 | D-13 |
| A-09 | OBL | Feature flags en settings: `HITL_ENABLED`, `RETRIEVER`, `RERANKER`, `TRACING`, `SEARCH_PROVIDER` | ⬜ Por hacer | P1 | D-13 |
| S-07 | OBL | Nodo `confirm_external_search` pasivo (pass-through si `HITL_ENABLED=false`) antes de `search_odoo_forum` | ⬜ Por hacer | P1 | D-13; enganche reto D |

## 8. Req. 6 — Interfaz de chat

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| U-01 | OBL | Chat funcional contra la API | ⬜ Por hacer | P0 | |
| U-02 | OBL | Carga de documentos desde la UI | ⬜ Por hacer | P0 | |
| U-03 | OBL | Mostrar fuentes citadas, agente que respondió y pasos recorridos | ⬜ Por hacer | P0 | |
| U-04 | OBL | Copia limpia del frontend base a `frontend/` (sin `.git`, `.env`, `.vercel`, `node_modules`, `tsconfig.tsbuildinfo`) + rebranding total (eliminar marca BBVA) + tema propio | ⬜ Por hacer | P0 | D-09, fase v1 |
| U-05 | OBL | Tipos TS generados desde OpenAPI de FastAPI (`openapi-typescript`) | ⬜ Por hacer | P1 | Contrato primero |
| U-06 | OBL | Render Markdown + bloques de código con resaltado (`react-markdown`, `remark-gfm`, resaltador) | ⬜ Por hacer | P0 | Fase v1 |
| U-07 | OBL | Citas: tarjetas (documento, sección, enlace) + marcadores `[n]` en el texto | ⬜ Por hacer | P0 | Fase v1 |
| U-08 | OBL | Badge de agente + timeline de nodos recorridos | ⬜ Por hacer | P0 | Fase v1 |
| U-09 | OBL | Panel de documentos: carga, listado, eliminación | ⬜ Por hacer | P0 | Fase v1 |
| U-10 | OPC | Cliente SSE (`fetch` + ReadableStream, máquina de estados de eventos) | ⬜ Por hacer | P1 | Fase v2, reto C |
| U-11 | OPC | Tarjeta de confirmación HITL (aprobar/rechazar `interrupt`) | ⬜ Por hacer | P2 | Fase v2, reto D |
| U-12 | OBL | Adaptar dashboard `/analytics`: resultados de eval (lineal vs agéntico, precisión supervisor, recall HNSW, ES vs EN), latencia/tokens/costo | ⬜ Por hacer | P1 | Fase v3; diferencial visual |
| U-13 | OBL | Dockerfile frontend con `output: "standalone"` | ⬜ Por hacer | P1 | C-01 |

## 9. Req. 8 — Evaluación y justificación de lo agéntico

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| E-01 | OBL | Golden set: ≥10 preguntas con respuesta esperada (cubiertas / no cubiertas / fuera de alcance) | ⬜ Por hacer | P0 | Único conjunto etiquetado (no hay entrenamiento; el corpus indexado no se etiqueta). Etiquetas por pregunta: respuesta esperada, secciones/chunks relevantes (para recall/precision de recuperación, V-04 y E-09), agente esperado (precisión del supervisor) |
| E-02 | OBL | Implementar RAG lineal baseline (recuperar → generar) | ⬜ Por hacer | P0 | |
| E-03 | OBL | Script de evaluación: faithfulness, answer relevancy, context precision | ⬜ Por hacer | P0 | D-12: módulo propio `eval/metrics/`; prompts del juez en `eval/prompts/` |
| E-10 | OBL | Answer correctness (F1 de afirmaciones vs respuesta esperada, juez Opus 5.5) | ⬜ Por hacer | P1 | D-12 |
| E-11 | OBL | Tests unitarios de métricas deterministas (context precision, recall@k, precision@k, MRR, routing accuracy) | ⬜ Por hacer | P1 | D-12; calidad de código |
| E-13 | OBL | Profile Compose `eval`: runner de evaluación dentro de la red interna (acceso a agent y TEI no publicados) | ⬜ Por hacer | P1 | GAP 2 de ARCHITECTURE.md |
| E-12 | OBL | Exportar resultados a JSON consumible por dashboard (U-12) + tabla en README | ⬜ Por hacer | P1 | D-12 |
| E-04 | OBL | Métrica de precisión del supervisor al elegir agente | ⬜ Por hacer | P0 | |
| E-05 | OBL | Comparación RAG lineal vs grafo agéntico (mismas preguntas), incl. latencia y tokens | ⬜ Por hacer | P0 | |
| E-06 | OBL | Análisis de ≥2 casos donde el sistema falla | ⬜ Por hacer | P0 | |
| E-07 | OBL | Sección «¿Por qué agéntico?» por agente/nodo: problema, ejemplo, costo | ⬜ Por hacer | P0 | |
| E-09 | OBL | Experimento cross-lingual: recall@k y precision@k de recuperación con consulta original en español vs traducida a inglés (mismas preguntas de eval) | ⬜ Por hacer | P1 | Justifica empíricamente la capacidad de cambio de idioma del rewriter (R-07) |
| E-08 | OBL | Mini-benchmark de recuperación (recall@k, MRR) de embeddings sobre corpus propio: Qwen3 vs Harrier vs e5 | ❌ Descartado | P1 | Descartado por tiempo; Qwen3 adoptado sin comparación (ver ADR D-04) |

## 10. Req. 9 — Contenerización

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| C-01 | OBL | Dockerfile multi-stage por servicio | ⬜ Por hacer | P0 | |
| C-02 | OBL | Docker Compose: todo con un solo comando | ⬜ Por hacer | P0 | |
| C-03 | OBL | Variables/secretos por `.env`; prueba en máquina limpia | ⬜ Por hacer | P0 | |
| C-04 | OBL | Servicio `init` one-shot: tablas Postgres + colección Qdrant + payload indexes antes de ingestar | ⬜ Por hacer | P0 | D-10; garantiza regla D-05 |
| C-05 | OBL | Healthchecks (pg_isready, Qdrant `/readyz`, TEI `/health`, servicios Python vía `python -c`) + `depends_on: service_healthy` | ⬜ Por hacer | P0 | Verificar curl en imágenes; sidecar si falta |
| C-06 | OBL | `compose.gpu.yaml` (TEI GPU + reserva de dispositivo) y `compose.override.yaml` (dev, `develop.watch`, Qdrant en loopback) | ⬜ Por hacer | P1 | D-10 |
| C-07 | OBL | `additional_contexts` para `packages/common` en builds de agent/ingestion/init | ⬜ Por hacer | P0 | Verificar Compose ≥ 2.17 |

## 11. Retos opcionales (bonus hasta +15%)

Mejor uno bien hecho que varios a medias. Priorizar según D-01.

| ID | Tipo | Reto | Dificultad | Estado | Punto de enganche previsto | Decisión / Contexto |
|---|---|---|---|---|---|---|
| O-A | OPC | A. Servidor MCP (≥2 tools: `search_docs`, `ingest_document`) + demo con cliente MCP | Baja–media | ⬜ Por hacer | Capa de servicios reutilizable por API y MCP | |
| O-B | OPC | B. Búsqueda híbrida (vector + BM25) + reranker, con mejora medida en eval | Media | ⬜ Por hacer | Retriever intercambiable tras interfaz | |
| O-C | OPC | C. Streaming SSE/WebSocket de respuesta y pasos | Baja | ⬜ Por hacer | Ejecución del grafo con `astream` | |
| O-D | OPC | D. Human-in-the-loop (confirmar eliminar doc / búsqueda externa) | Baja–media | ⬜ Por hacer | Checkpointer + interrupts del grafo | |
| O-E | OPC | E. Observabilidad (Langfuse/LangSmith/Phoenix/OTel): latencia, tokens, costo | Baja | ⬜ Por hacer | Callbacks/handlers configurables por entorno | |
| O-F | OPC | F. Ingesta incremental: detección de duplicados y modificados (hash) | Baja | ⬜ Por hacer | Hash de contenido en metadatos desde el inicio | |

## 12. Entregables

| ID | Tipo | Tarea | Estado | Prioridad | Decisión / Contexto |
|---|---|---|---|---|---|
| ENT-01 | ENT | Repositorio GitHub con estructura clara e historial de commits | ⬜ Por hacer | P0 | |
| ENT-02 | ENT | README: pasos para levantar localmente | ⬜ Por hacer | P0 | |
| ENT-03 | ENT | README: documentación de API (curl/Bruno/Postman + Swagger) | ⬜ Por hacer | P0 | |
| ENT-04 | ENT | README: diagrama de arquitectura y diagrama del grafo (Mermaid) | ⬜ Por hacer | P0 | |
| ENT-05 | ENT | README: decisiones de arquitectura/stack, incluyendo lo descartado y por qué | ⬜ Por hacer | P0 | |
| ENT-06 | ENT | README: «¿Por qué agéntico?», resultados de eval, ≥2 casos de falla | ⬜ Por hacer | P0 | |
| ENT-07 | ENT | Video demo ≤5 min: ingesta · consulta con citas · rewriter activo · caída a investigación · fuera de alcance | ⬜ Por hacer | P0 | |
| ENT-08 | ENT | Preparar sesión técnica de 45 min (defensa de decisiones) | ⬜ Por hacer | P1 | |
| ENT-09 | ENT | Auditoría final: sin secretos en historial, prueba en máquina limpia | ⬜ Por hacer | P0 | |
| ENT-10 | ENT | Script único `scripts/export_graph.py`: `get_graph(xray=True).draw_mermaid()` → pegar en README (sin endpoint) | ⬜ Por hacer | P1 | GAP 1 de ARCHITECTURE.md; se ejecuta una vez |

---

## Registro de decisiones (ADR ligero)

Plantilla — copiar por cada decisión:

```
### D-XX — Título
- Fecha:
- Estado: Propuesta | Aceptada | Reemplazada
- Contexto / requerimiento:
- Opciones consideradas:
- Decisión:
- Por qué (y qué se descartó):
- Impacto en retos opcionales:
- Tareas afectadas:
```

### D-01 — Alcance de retos opcionales
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: retos A–F suman hasta +15%; "mejor uno bien hecho que varios a medias".
- Opciones consideradas: implementar todos; solo los de dificultad baja; selección por costo/beneficio.
- Decisión: núcleo comprometido E (observabilidad) → C (streaming) → F (ingesta incremental) → A (MCP). Stretch si sobra tiempo: D (HITL) → B (híbrida + rerank).
- Por qué (y qué se descartó): E alimenta obligatorios (latencia/tokens para «¿Por qué agéntico?»); C visible en chat y demo; F casi gratis con hash en metadatos; A reutiliza capa de servicios. B queda último: costo medio y exige medición comparativa adicional. Descartado comprometer los 6: riesgo de calidad.
- Impacto en retos opcionales: los 6 se diseñan con punto de enganche desde el inicio (ver D-13).
- Tareas afectadas: O-A…O-F, D-13.

### D-02 — Framework de grafos y estado tipado
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: supervisor + subagentes con estado tipado, arista condicional, ciclo controlado, diagrama del grafo. Criterio de mayor peso (30%).
- Opciones consideradas: LangGraph; LlamaIndex Workflows; PydanticAI Graph.
- Decisión: LangGraph. Estado del grafo en `TypedDict` con reducers `Annotated` (acumular `messages`, `steps`, `sources`). Pydantic para salidas estructuradas del LLM (router, grader) y esquemas API. Subagente de documentación compilado como subgrafo e insertado como nodo del supervisor. Loop de tool-calling del subagente de investigación escrito a mano (sin `create_react_agent`).
- Por qué (y qué se descartó): LangGraph trae nativo checkpointer, `interrupt`, `astream`, `draw_mermaid()` y callbacks. LlamaIndex Workflows descartado: HITL/checkpoint menos maduros, diagrama menos claro. PydanticAI Graph descartado: ecosistema joven, persistencia y streaming manuales. Estado Pydantic en el grafo descartado: validación en cada paso y fricción con reducers.
- Impacto en retos opcionales: C vía `astream_events`; D vía `interrupt` + checkpointer; E vía callbacks Langfuse. Memoria por `thread_id` (D-08) vía checkpointer.
- Tareas afectadas: S-01…S-04, R-01…R-05, X-01, A-02, D-08, O-C, O-D, O-E.

### D-03 — LLM y proveedor
- Fecha: 2026-11-02
- Estado: Aceptada (distribución inicial, revisable con resultados de eval)
- Contexto / requerimiento: LLM a elección; se requiere tool calling, salida estructurada y reporte de costo/latencia por nodo.
- Opciones consideradas: Anthropic Claude; OpenAI; Gemini; Groq; Ollama local.
- Decisión: Anthropic Claude, modelo según complejidad/volumen:
  - `claude-haiku-5-5` ($0.10/$0.50 por MTok): router del supervisor, grader, rewriter.
  - `claude-sonnet-5-5` ($2/$10 por MTok): generator, subagente de investigación.
  - `claude-opus-5-5` ($4/$20 por MTok): juez de evaluación (actualizado en D-12, 2026-11-02: evita sesgo de autoevaluación Sonnet→Sonnet; volumen mínimo).
  - Modelo por rol configurable en `.env` (`init_chat_model` / `langchain-anthropic`); cambio sin tocar código.
- Por qué (y qué se descartó): Haiku barato y rápido para tareas cortas y de alto volumen; Sonnet para síntesis con citas y tool calling. Ollama descartado (pesado en Docker, tool calling débil, choca con "máquina limpia"). Groq descartado (tool calling menos fino). Opus 5.5 no por defecto: costo sin ganancia clara en este dominio; queda como opción por config.
- Notas técnicas: modelos 5.5 → no `budget_tokens`, no forced `tool_choice` (`any`/`tool` → 400; usar `auto` + `strict: true` o structured outputs), no prefill. Controlar profundidad con `effort` (router/grader en `low`). Anthropic no ofrece embeddings → D-04.
- Impacto en retos opcionales: E reporta tokens/costo por modelo y nodo.
- Tareas afectadas: S-02, R-02, R-03, R-04, X-01, E-03, E-05, F-02 (`.env.example`).

### D-04 — Modelo de embeddings
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: consultas en español sobre documentación técnica en español (preliminar); corpus con fragmentos de código. Decisión crítica: fija dimensión de la colección y calidad de recuperación (15%). GPU local disponible (RTX serie 4090).
- Opciones consideradas: Voyage / OpenAI / Cohere (API, key extra); fastembed (ONNX, catálogo limitado: mejor multilingüe `multilingual-e5-large`, desactualizado); `Qwen/Qwen3-Embedding-0.6B`; `microsoft/harrier-oss-v1-0.6b`; `BAAI/bge-m3`.
- Decisión: `Qwen/Qwen3-Embedding-0.6B` (Apache 2.0, 100+ idiomas + código, 32K ctx, 1024 dims con MRL 32–1024, instruction-aware). Runtime: sentence-transformers + torch. Dispositivo `auto` (CUDA si existe, si no CPU) configurable por `.env`. Instrucción de tarea en consultas, no en documentos. Detrás de interfaz `Embedder`. Modelo y dimensión guardados en metadatos de la colección.
- Por qué (y qué se descartó): único candidato con score de código publicado (MTEB-Code 75.41) + buen multilingüe (MMTEB 64.33); familia con reranker propio (Qwen3-Reranker) → coherente con reto B; experiencia previa del equipo con Qwen. fastembed descartado: obliga a elegir modelo por catálogo, no por dominio. Harrier-0.6B (MMTEB v2 69.0 auto-reportado, MIT) queda como challenger sin scores de código. bge-m3 descartado: más antiguo, menor score. jina v3/v4 descartado: licencia CC-BY-NC. APIs descartadas: key extra y costo sin necesidad.
- Riesgos: evaluador sin GPU → fallback CPU (ingesta más lenta); imagen con torch → usar wheel CPU por defecto y perfil/override GPU en Compose (requiere NVIDIA Container Toolkit). Prompt de instrucción mal aplicado degrada 1–5%.
- Impacto en retos opcionales: B → Qwen3-Reranker-0.6B como reranker + BM25 para híbrida. F → hash incluye versión del modelo de embeddings.
- Validación: mini-benchmark comparativo (E-08) descartado por tiempo (2026-11-02). Se adopta Qwen3 sin comparación empírica; se declara como limitación en README.
- Actualización 2026-11-02 (D-10): runtime cambia de sentence-transformers embebido a servicio dedicado **TEI** (Hugging Face Text Embeddings Inference, soporta Qwen3). Un solo contenedor con el modelo (único con CUDA), batching dinámico; `agent` e `ingestion` sin torch. Instrucción de consulta antepuesta desde el cliente `Embedder`. Modelo sin cambios.
- Actualización 2026-11-02: el corpus pasa a ser documentación técnica de Odoo 19 en inglés (ver D-07/D-11). La decisión se mantiene y se refuerza: Qwen3 es multilingüe y soporta recuperación cross-lingual (consulta en español → documento en inglés).
- Tareas afectadas: I-05, V-01, C-01, C-02, D-11 (dataset en español), O-B.

### D-05 — Base de datos vectorial e índice
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: vector DB con índice eficiente (p. ej. HNSW) y parámetros documentados; filtrado por metadatos. Corpus estimado: 20–100 docs ≈ 2.000–6.000 chunks de 1024 dims (≈4 KB c/u). Debe habilitar reto B (híbrida) y F (incremental) sin cambios estructurales.
- Opciones consideradas:
  - Qdrant: HNSW configurable, payload indexes con HNSW filtrable, vectores densos + sparse con nombre en el mismo punto, fusión RRF en servidor, imagen liviana.
  - pgvector: HNSW + filtros SQL + `tsvector` en español; ventaja de compartir Postgres con checkpointer. Híbrida manual, tuning menos específico.
  - Chroma: simple, poco control HNSW, híbrida débil.
  - Milvus / Weaviate: sobredimensionados (Milvus requiere etcd + MinIO).
  - Pinecone: SaaS, key extra, no local.
- Decisión: **Qdrant**, una colección con dos vectores con nombre:
  - `dense`: 1024 dims, distancia `Cosine`, generado por Qwen3-Embedding-0.6B (un vector por chunk, last-token pooling, L2-normalizado → coseno ≡ producto punto; Qdrant normaliza al insertar y usa dot).
  - `sparse`: BM25 con `modifier: idf` (IDF calculado en servidor). Reservado desde el inicio para reto B; se pobla al implementar B.
- Parámetros HNSW (`dense`):

  | Parámetro | Default Qdrant | Elegido | Rango típico | Efecto / justificación |
  |---|---|---|---|---|
  | `m` | 16 | **16** | 4–64 (0 = sin grafo) | Aristas máx. por nodo (2m en capa 0). ↑ recall, ↑ memoria, ↑ tiempo de build. 16 da recall alto a esta escala; 32 duplica aristas con ganancia marginal. |
  | `ef_construct` | 100 | **200** | 64–512 | Candidatos evaluados al construir. ↑ calidad del grafo, ↑ tiempo de indexación. Costo único (segundos a esta escala); no afecta consulta. |
  | `hnsw_ef` (consulta) | = `ef_construct` | **128** | k–512 | Candidatos evaluados al buscar; debe ser ≥ k. ↑ recall, ↑ latencia. El grader recibe ~10–20 chunks → margen amplio; latencia sub-ms a esta escala. Ajustable por consulta sin reindexar. |
  | `full_scan_threshold` | 10.000 KB | Ajustar en implementación | — | Bajo este tamaño el planner hace búsqueda exacta. 10.000 KB ≈ 2.500 vectores de 1024 dims → con este corpus HNSW podría no usarse. Se ajustan umbrales (incl. `indexing_threshold` del optimizador, por verificar) para que HNSW se construya y los parámetros apliquen. Búsquedas filtradas de baja cardinalidad (un documento) caen a exacta: comportamiento correcto. |

- Payload indexes (creados **antes** de ingestar, requisito para HNSW filtrable; añadirlos después obliga a reconstruir): `doc_id`, `source`, `section`, `content_hash` (reto F), `ingested_at`.
- Configuraciones alternativas documentadas (no aplican a esta escala): memoria limitada / millones de vectores → `m=8` + cuantización (`int8` 4×, binaria 32×) con rescore; recall máximo a gran escala → `m=32–64`, `ef_construct≥400`; ingesta masiva → `m=0` durante carga y construir al final; corpus muy pequeño → búsqueda exacta pura.
- Por qué (y qué se descartó): Qdrant cubre filtros, híbrida y RRF nativos con un único servicio liviano. pgvector descartado: híbrida y fusión manuales; la ventaja de compartir Postgres con el checkpointer no compensa (checkpointer se decide en D-08). Chroma, Milvus, Weaviate, Pinecone descartados por las razones listadas.
- Por qué BM25 además de denso (reto B): el denso captura significado ("proteger mi API" ↔ "autenticación") pero falla en términos exactos (`APIRouter`, códigos de error, versiones); BM25 los acierta. Fusión RRF combina rankings.
- Evidencia empírica: V-04 mide recall@k de HNSW vs `exact=true` y latencia sobre las preguntas de evaluación.
- Actualización 2026-11-02: corpus en inglés (D-11) → BM25 en **inglés** (idioma del corpus); el rewriter aporta la variante EN de la consulta (R-07). Reemplaza la mención a español.
- Riesgos / por verificar: (obsoleto: configurar español; ver actualización) confirmar parámetro de idioma de BM25; confirmar si agregar un vector con nombre a colección existente exige recrearla (motivo de reservar `sparse` ya); confirmar default y nombre de `indexing_threshold`.
- Impacto en retos opcionales: B → `sparse` + fusión RRF + Qwen3-Reranker sin migración de esquema. F → `content_hash` indexado para detección de duplicados/modificados.
- Tareas afectadas: V-01, V-02, V-03, V-04, I-04, I-05, R-01, O-B, O-F.

### D-06 — Estrategia de chunking
- Fecha: 2026-11-02
- Estado: Aceptada condicionalmente — revisar al cerrar D-11 (dataset). Preliminar: corpus por web scraping de documentación en español, sin PDFs.
- Contexto / requerimiento: justificar tamaño, solapamiento y criterio de división; metadatos de página/sección por chunk; citas por sección.
- Opciones consideradas: tamaño fijo con overlap; recursivo por separadores; por encabezados; semántico (por similitud entre oraciones).
- Decisión: chunking jerárquico consciente de estructura:
  1. Normalización a Markdown: HTML (scraping) → MD; PDF → MD con `pymupdf4llm` (conserva encabezados y página); MD nativo tal cual; TXT sin estructura → directo a paso 3.
  2. Corte primario por encabezados H1–H3; ruta de encabezados guardada en `section` (p. ej. "Seguridad > OAuth2 > Scopes").
  3. Corte secundario recursivo (párrafo → línea → oración) si la sección supera ~512 tokens, overlap ~64 tokens (~12%). Conteo con tokenizer de Qwen3.
  4. Bloques de código nunca se dividen; secciones < ~100 tokens se fusionan con la vecina.
  5. Ruta de sección antepuesta al texto que se vectoriza (no al mostrado) para contextualizar chunks.
  6. Tamaño y overlap configurables por `.env`.
- Por qué (y qué se descartó): documentación técnica ya está estructurada → los encabezados son la mejor frontera semántica y dan `section` para citas sin costo. ~512 tokens: cabe un concepto + ejemplo, citas precisas, grader barato (~10 chunks ≈ 5K tokens en Haiku); chunks grandes diluyen el vector aunque Qwen3 admita 32K. Tamaño fijo descartado: corta código y temas a ciegas. Semántico descartado: costoso, no determinista y redundante con la estructura existente.
- Revisión pendiente (al cerrar D-11): verificar que el HTML scrapeado conserva jerarquía de encabezados y bloques de código; calibrar 512/64 con la distribución real de tamaños de sección; definir qué reemplaza "página" como metadato en web (URL + ancla de sección). El endpoint debe seguir soportando PDF (requerimiento); la prueba recomienda ≥1 PDF en el dataset.
- Impacto en retos opcionales: F → `content_hash` por documento y por chunk; B → mismo chunk alimenta `dense` y `sparse`.
- Tareas afectadas: I-02, I-03, I-04, R-04, D-11.

### D-07 — Herramientas externas del subagente de investigación
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: ≥1 herramienta externa con esquema tipado (tool calling), manejo de timeout y resultado vacío, respuesta marcada como externa con enlaces. Caso de uso definido: asistente sobre documentación técnica de Odoo 19; lo no cubierto se consulta **solo en foros especializados** (Odoo Forum), no en toda la web. Preferencia: open source, sin API keys extra.
- Hallazgo clave: `robots.txt` de odoo.com contiene `Disallow: *?*search=*` → el buscador interno del foro no debe usarse de forma automatizada. Los posts individuales (`/forum/help-1/<slug>-<id>`) sí están permitidos. Se respeta y se documenta.
- Opciones consideradas:
  - Tavily: búsqueda para LLMs; requiere key (descartado por preferencia open source / sin key).
  - web_search server-side de Anthropic: sin esquema propio ni manejo de errores propio, costo por búsqueda (descartado: no demuestra lo evaluado).
  - agent-browser (Vercel Labs, Apache-2.0): automatización de navegador para agentes de desarrollo (skill de Claude Code); no busca, solo navega; Node + Chromium en el contenedor; herramienta prefabricada que resta frente a tool tipado propio (descartado).
  - Scraping del buscador interno del foro: viola `robots.txt` (descartado).
  - SearXNG self-hosted (AGPL-3.0, contenedor aparte): metabuscador robusto multi-motor; sobreingeniería para un único dominio (plan B).
  - `ddgs` (librería Python, sin key, sin infraestructura): soporta `site:`; API no oficial con riesgo de rate limit (elegido).
  - API de GitHub (issues `odoo/odoo`): descartado, no aporta al caso de uso.
- Decisión: dos herramientas propias con esquema Pydantic:
  - `search_odoo_forum(query, max_results)`: búsqueda vía `ddgs` con `site:odoo.com/forum` + post-filtro de URLs por allowlist de dominios en código (no se confía solo en `site:`). Salida: `{title, url, snippet}` + `status` (`ok` / `empty` / `timeout` / `error`).
  - `read_forum_post(url)`: httpx + parser HTML; extrae pregunta, respuesta aceptada y respuestas más votadas. Solo URLs de la allowlist.
  - Ambas: timeout explícito, reintentos con backoff, caché de resultados, estados explícitos que el agente interpreta (reformular, o responder "no encontrado" sin inventar). User-Agent identificable y ritmo de peticiones moderado.
  - Interfaz `SearchProvider` con `ddgs` como implementación por defecto.
  - Respuesta marcada como "fuente externa: Odoo Forum" con los enlaces efectivamente usados.
- Plan B (solo decisión, no se implementa salvo que fallen las pruebas): SearXNG como servicio opcional de Compose detrás de la misma interfaz `SearchProvider`, seleccionable por `.env`.
- Valor agéntico: el foro se busca por palabras clave, no semánticamente → el agente debe transformar la pregunta (posiblemente en español) en términos de búsqueda (módulo, modelo, versión, en inglés). Ejemplo para «¿Por qué agéntico?».
- Impacto en retos opcionales: D → `interrupt` antes de `search_odoo_forum` para confirmar búsqueda externa. E → trazas por tool call.
- Tareas afectadas: X-01…X-04, RK-03, RK-04, O-D, D-11.

### D-08 — Memoria conversacional y persistencia de estado
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: memoria por `thread_id` para preguntas de seguimiento. Reto D exige que el estado sobreviva entre peticiones HTTP (pausa con `interrupt` y reanudación posterior) y a reinicios.
- Opciones consideradas: `InMemorySaver` (volátil, un proceso); `AsyncSqliteSaver` (archivo en volumen, un escritor); `AsyncPostgresSaver` (servicio extra, concurrente, patrón de producción); Redis saver (persistencia a configurar, sin ventaja).
- Decisión:
  - Checkpointer `AsyncPostgresSaver` (async por streaming, reto C). `InMemorySaver` solo en tests.
  - El mismo Postgres aloja la tabla `documents` (registro relacional de documentos: `doc_id`, nombre, fuente/URL, `content_hash`, modelo de embeddings, `n_chunks`, estado, fechas).
  - Separación de responsabilidades: Qdrant = vectores + payload de chunk; Postgres = estado de conversaciones + registro de documentos.
  - Historial: reducer `add_messages`; recorte a últimas N rondas / tope de tokens al invocar el LLM (configurable).
  - Nodo de contextualización (Haiku) antes del router: reescribe preguntas de seguimiento como pregunta independiente ("¿y eso aplica en la v18?" → pregunta completa). Sin él, el retriever busca referencias vacías.
- Por qué (y qué se descartó): Postgres da concurrencia real (varios workers), persistencia para HITL y además el registro relacional que necesitan listar/eliminar documentos e ingesta incremental. SQLite descartado: un escritor y sin registro relacional cómodo. InMemory descartado fuera de tests. Redis descartado: sin ventaja.
- Impacto en retos opcionales: D → estado pausado persistente; F → comparación de `content_hash` en `documents` antes de reindexar; C → saver async compatible con `astream_events`.
- Tareas afectadas: A-02, S-06, V-05, I-06, C-02, O-C, O-D, O-F.

### D-09 — Stack de interfaz de chat
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: chat contra la API con carga de documentos; mostrar fuentes, agente y pasos. Retos C (streaming) y D (confirmación). Peso 10% (doc + interfaz) y primera impresión en el video demo.
- Opciones consideradas:
  - Chainlit: pasos anidados, fuentes, upload, `AskActionMessage` y streaming nativos (~1–1,5 días); aspecto genérico; mantenido por la comunidad desde mayo 2025.
  - Streamlit: robusto; modelo de re-ejecución complica streaming y reanudación HITL.
  - Gradio: `ChatInterface` con metadatos de pasos; menos flexible para paneles y confirmaciones.
  - Next.js desde cero: control total; ~4–5 días.
  - **Next.js adaptando frontend propio previo** (proyecto agenteBBVA): Next 16, React 19, Tailwind 4, TS; chat funcional (burbujas, fuentes, typing, estado vacío) + dashboard recharts (StatCards, latencia, tokens, costo) + Dockerfile multi-stage; ~2,5–3,5 días.
- Decisión: Next.js adaptando el frontend previo. Cliente delgado de la FastAPI, sin lógica de negocio. Por fases:
  - v1 (cumple obligatorio, sin streaming): copia limpia + rebranding, Markdown con código resaltado, citas con tarjetas y marcadores, badge de agente + timeline de nodos, panel de documentos, `thread_id`.
  - v2: cliente SSE (reto C) + tarjeta de confirmación HITL (reto D).
  - v3: dashboard de evaluación adaptado (lineal vs agéntico, precisión del supervisor, recall HNSW vs exacto, ES vs EN, latencia/tokens/costo por nodo).
  - Contrato primero: tipos TS generados desde OpenAPI (`openapi-typescript`).
  - Docker con `output: "standalone"` (imagen más liviana que copiar `node_modules`).
- Por qué (y qué se descartó): impacto visual y control total del resultado; base funcional propia ahorra layout, estilos, dashboard e infraestructura; el dashboard de evaluación con gráficos es un diferencial que Chainlit/Streamlit no dan. Chainlit descartado: aspecto genérico y riesgo de mantenimiento (queda como alternativa documentada). Streamlit/Gradio descartados por streaming/HITL y flexibilidad. Desde cero descartado: tiempo.
- Riesgos: el frontend base no tiene streaming, Markdown, pasos, upload ni HITL (se construyen); copia debe excluir `.env` (contiene keys), `.git`, `.vercel` y toda marca BBVA.
- Impacto en retos opcionales: C → U-10; D → U-11; E → dashboard puede mostrar métricas de trazas.
- Tareas afectadas: U-01…U-13, C-01, A-03.

### D-10 — Arquitectura de servicios y estructura del monorepo
- Fecha: 2026-11-02
- Estado: Aceptada (revisada con skills `docker-project-foundations`, `docker-build-strategies`, `docker-compose-patterns` de `github.com/docker/skills`, instaladas en `.claude/skills/`)
- Contexto / requerimiento: estructura sugerida `services/ingestion`, `services/agent`, `frontend`, `eval`, `docs`; Dockerfile multi-stage por servicio; Compose con un solo comando; secrets fuera del código.
- Servicios:

  | Servicio | Responsabilidad | Imagen | Publicado | Depende de |
  |---|---|---|---|---|
  | `frontend` | Next.js; proxy `/api/agent/*`, `/api/ingestion/*` (mismo origen, sin CORS) | build propio, standalone, no-root | `127.0.0.1:3000` | agent, ingestion |
  | `agent` | FastAPI + LangGraph: consultas, SSE, memoria, tools, baseline lineal (`mode=agentic\|linear`) | build propio | no | init (completed), embeddings, qdrant, postgres (healthy) |
  | `ingestion` | FastAPI: carga, parseo, chunking, scraping, listar/eliminar documentos | build propio | no | init (completed), embeddings, qdrant, postgres (healthy) |
  | `init` | One-shot: tablas Postgres, colección Qdrant, payload indexes | build propio | no | qdrant, postgres (healthy) |
  | `embeddings` | TEI + Qwen3-Embedding-0.6B | TEI CPU (tag fijo); GPU vía `compose.gpu.yaml` | no | — |
  | `qdrant` | Vectores | `qdrant/qdrant` (tag fijo) | no (loopback en dev) | — |
  | `postgres` | Checkpointer + `documents` | `postgres` alpine (tag fijo) | no | — |
  | `searxng` | Plan B D-07 | profile `searxng` | no | — |
  | `langfuse` | Reto E | profile `observability` (por decidir) | — | — |

- Estructura del repositorio:
  ```
  compose.yaml · compose.gpu.yaml · compose.override.yaml · .env.example · README.md · backlog.md
  services/agent/       grafo, nodos, tools, baseline lineal, API (Dockerfile + .dockerignore)
  services/ingestion/   parsers, chunker, scraper, API (Dockerfile + .dockerignore)
  packages/common/      config, schemas, Embedder (cliente TEI), repos Qdrant/Postgres
  frontend/             Next.js (Dockerfile + .dockerignore)
  eval/                 golden set, scripts, reportes
  docs/                 diagramas
  infra/                configuración plan B SearXNG, init
  ```
- Reglas aplicadas (de las skills Docker):
  - Nombres `compose.yaml` / `compose.*.yaml` (no legacy `docker-compose.yml`).
  - Un `Dockerfile` + `.dockerignore` por servicio en la raíz de su contexto; código compartido vía `additional_contexts` (`COPY --from=common`), ya que no se puede copiar fuera del contexto.
  - `depends_on` con `service_healthy` / `service_completed_successfully`; healthcheck en cada dependencia; `start_period` largo para TEI (descarga del modelo).
  - Solo `frontend` publicado y en loopback; datastores en red interna.
  - Tags de imagen fijos, nunca `latest`.
  - Dockerfiles: `# syntax=docker/dockerfile:1`, stages con nombre, cache mounts, manifiestos montados (bind), no-root con UID numérico, `EXPOSE`, `ENTRYPOINT` exec form; Next.js standalone sin `node_modules`.
  - Volúmenes con nombre: `qdrant-data`, `pg-data`, `hf-cache`, `documents-data`; red por defecto.
  - `env_file: .env`; sin secretos en `compose.yaml`; defaults solo-dev con `${VAR:-...}` etiquetados; `.env` en `.gitignore` y `.dockerignore`.
  - Servicios opcionales como profiles; GPU como override.
  - `restart: unless-stopped` en infraestructura.
- Por qué (y qué se descartó): separar lectura (agent) y escritura (ingestion) aclara responsabilidades; TEI evita duplicar el modelo y torch en dos imágenes; baseline lineal dentro de agent comparte retriever/generator → comparación justa; eval como caja negra contra la API. Descartados: monolito único (mezcla responsabilidades, contradice estructura sugerida); sentence-transformers embebido en cada servicio (doble carga de modelo, imágenes pesadas); contexto de build en raíz del repo (contextos grandes, builds lentos).
- Política operativa: `docker compose down -v` borra índice y conversaciones → documentado en README; nunca sin confirmación.
- Impacto en retos opcionales: A → punto de entrada MCP reutilizando `packages/common`; B → sin cambios de servicios; C → SSE en agent + proxy frontend; D → checkpointer Postgres; E → profile `observability`; F → `documents` + `content_hash`.
- Tareas afectadas: F-01, C-01…C-07, U-13, A-01.

### D-11 — Dataset (corpus)
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: documentación técnica pública, 20–100 documentos, ≥1 PDF (recomendado). Caso de uso: asistente técnico de Odoo 19; consultas en español, corpus en inglés.
- Hallazgos:
  - Sección Developer de Odoo 19: ~113 páginas (tutoriales ~34, how-tos ~27, referencia ~51).
  - Licencia del repositorio `odoo/documentation`: CC BY-SA 4.0 (uso y redistribución con atribución).
  - `robots.txt` de odoo.com no restringe `/documentation`.
  - Páginas de referencia (p. ej. ORM API) se generan con Sphinx `autodoc` desde docstrings del código de Odoo → el RST del repositorio está incompleto; el contenido real solo existe en el HTML renderizado.
- Opciones consideradas: RST fuente desde GitHub (versionable por commit, pero incompleto por autodoc y con directivas Sphinx a convertir); scraping del HTML renderizado (contenido completo, URLs citables); sección Developer completa (~113, excede el rango recomendado y mete ruido de diseño web).
- Decisión: subconjunto curado de ~60 páginas, obtenido por scraping del HTML renderizado:

  | Bloque | Páginas |
  |---|---|
  | Tutorial Server framework 101 (caps. 1–15) | 15 |
  | Referencia backend (ORM + changelog, data, actions, reports, module, security, performance, testing, http, mixins) | 12 |
  | Referencia frontend (overview, assets, javascript_modules, owl_components, registries, services, hooks, patching_code, error_handling, javascript_reference, qweb) | 11 |
  | User interface (view_records, view_architectures, scss_inheritance, icons) | 4 |
  | How-tos (javascript_field, javascript_view, javascript_client_action, standalone_owl_application, company, create_reports, translations) | 7 |
  | Tutoriales (define_module_data, restrict_data_access, unit_tests, mixins, pdf_reports) | 5 |
  | CLI, external_api (JSON-2), external_rpc_api, upgrade_scripts, upgrade_utils | 5 |

  - Excluido: website themes (~27, diseño/marketing), standard modules account/payment (nicho), mobile, odoo_editor, JS unit testing (subpáginas).
  - Lista curada versionada en archivo de configuración (reproducible).
- Pipeline:
  1. Scraper CLI en `services/ingestion`: httpx con pausas y User-Agent identificable; extracción del artículo principal; HTML → Markdown conservando encabezados, anclas `#id` y bloques de código con lenguaje.
  2. Snapshot versionado `data/corpus/odoo19-dev/*.md` con frontmatter (`url`, `title`, `fetched_at`, `license: CC BY-SA 4.0`) → evaluación reproducible aunque la documentación cambie; atribución de licencia cumplida.
  3. Carga vía endpoint de ingesta (`make seed`), no por atajo interno → demuestra el endpoint.
  4. Citas = URL + ancla de sección (clic lleva a la sección exacta).
- PDF: página *Coding guidelines* (sección Contributing; fuera del corpus Developer, sin duplicar) renderizada a PDF con Chromium headless; declarada como "PDF generado desde documentación oficial". Demuestra ingesta PDF con metadato de página.
- Por qué (y qué se descartó): HTML renderizado es la única fuente completa (autodoc) y da URLs citables; ~60 páginas cubren el núcleo técnico dentro del rango recomendado. RST descartado por incompleto. Sección completa descartada por tamaño y ruido.
- Impacto en otras decisiones: confirma D-06 (Markdown primero); calibración 512/64 pendiente con el snapshot real (I-12); páginas enormes (`orm.html`, `view_architectures.html`) ponen a prueba el corte por encabezados. Golden set (E-01) se construye sobre este corpus + preguntas reales del foro no cubiertas.
- Tareas afectadas: I-08…I-12, D-06, E-01, ENT-07.

### D-12 — Framework de evaluación
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: ≥10 preguntas con respuesta esperada (cubiertas, no cubiertas, fuera de alcance); métricas faithfulness, answer relevancy, context precision (Ragas, DeepEval o LLM-as-judge propio) + precisión del supervisor; comparación obligatoria RAG lineal vs grafo agéntico; costo en latencia/tokens. Peso 20%.
- Opciones consideradas: Ragas (nombres estándar, API inestable entre versiones, dependencia para 3 métricas); DeepEval (pesado, empuja a plataforma Confident AI, telemetría); implementación propia (control total, transparencia, manejo explícito de respuesta ES / contexto EN).
- Decisión: implementación propia en `eval/metrics/` (funciones puras + tests) y prompts del juez versionados en `eval/prompts/` con salida estructurada Pydantic. Juez: `claude-opus-5-5`.
- Golden set (E-01, ~30 preguntas): ~16 cubiertas (algunas diseñadas para activar el rewriter), ~6 no cubiertas (→ foro), ~4 fuera de alcance, ~4 de seguimiento (memoria + contextualización). Etiquetas: respuesta esperada, secciones relevantes (`url#ancla`, nivel sección para sobrevivir a recalibraciones de chunking), agente esperado, categoría.
- Métricas y cálculo:

  | Métrica | Tipo | Cálculo |
  |---|---|---|
  | Faithfulness | LLM-juez | Juez descompone la respuesta en afirmaciones atómicas; por cada una decide si es inferible del contexto. `respaldadas / totales`. Mide alucinación, no corrección. |
  | Answer relevancy | LLM-juez + embeddings | Juez genera N=3 preguntas que la respuesta contestaría; se vectorizan con Qwen3 (TEI) junto a la pregunta original. `promedio cos(original, generada_i)`. Mide pertinencia, no corrección. |
  | Answer correctness | LLM-juez | Juez compara afirmaciones de la respuesta vs respuesta esperada: VP (correctas), FP (sobrantes/erróneas), FN (faltantes). F1 = 2·VP / (2·VP + FP + FN). |
  | Context precision@K | Determinista | `v_k = 1` si la sección del chunk en posición k ∈ secciones relevantes. `Σ_k (Precision@k · v_k) / relevantes en top K`. Ej.: [1,0,1,0] → (1 + 0,667)/2 = 0,83. |
  | Recall@k / Precision@k | Determinista | Secciones relevantes recuperadas en top k / total relevantes; relevantes en top k / k. |
  | MRR | Determinista | Promedio de 1 / posición del primer relevante. |
  | Routing accuracy | Determinista | Enrutamientos correctos / total + matriz de confusión 3×3 (docs / investigación / directo) con precision/recall por clase. |
  | Corrección de citas | Determinista | Sección citada ∈ secciones relevantes. |
  | Latencia / tokens / costo | Determinista | Por nodo y por consulta, desde la respuesta de la API (nodos recorridos) y/o trazas (reto E). |

- Evidencia agéntica: en modo agéntico, context precision y faithfulness se miden sobre el contexto que llega al generator (post-grader); en modo lineal, sobre lo recuperado directamente. El delta cuantifica el aporte del grader. Mismas preguntas, mismo retriever y generator → solo cambia la orquestación.
- Agregación: por categoría (faithfulness/relevancy no aplican a saludo ni fuera de alcance; ahí se mide abstención/delegación correcta). Se reporta `n` por promedio y se declara el tamaño pequeño de muestra.
- Salida: JSON de resultados (dashboard U-12) + tabla en README.
- Por qué (y qué se descartó): las métricas son simples de implementar con rigor y el golden set etiquetado permite calcular context precision sin LLM; propio = transparente y defendible en la sesión técnica. Ragas descartado: dependencia inestable para 3 métricas. DeepEval descartado: peso y acoplamiento a plataforma. Juez Opus 5.5 en vez de Sonnet 5.5: evita sesgo de autoevaluación; costo marginal (~30 preguntas × 2 modos), a medir en la primera corrida.
- Impacto en retos opcionales: B → mismas métricas miden la mejora de híbrida + rerank; E → latencia/tokens/costo por nodo desde trazas.
- Tareas afectadas: E-01…E-07, E-09…E-12, V-04, U-12.

### D-13 — Contrato de extensibilidad para retos opcionales
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: regla de oro del proyecto — los retos A–F deben poder añadirse sin cambios estructurales. Construir solo enganches baratos y estructurales; nada de código muerto.
- Principios transversales:
  1. Interfaces en `packages/common` con implementación seleccionada por `.env`: `Embedder` (TEI), `Retriever.retrieve(query, filters, k) -> list[ScoredChunk]` (`DenseRetriever` día 1; `HybridRetriever` reto B), `Reranker` (no-op por defecto), `SearchProvider` (`ddgs`; SearXNG plan B), LLM por rol.
  2. Modelo de eventos tipado (Pydantic) emitido por el grafo: `node_started`, `node_finished`, `token`, `sources`, `interrupt`, `final`. El endpoint REST los agrega; SSE (reto C) los reenvía. "Nodos recorridos" y "agente que respondió" (obligatorios) se derivan de los eventos.
  3. Feature flags: `HITL_ENABLED`, `RETRIEVER=dense|hybrid`, `RERANKER=none|qwen3`, `TRACING=none|langfuse`, `SEARCH_PROVIDER=ddgs|searxng`.
- Matriz de enganches:

  | Reto | Enganche día 1 | Diferido |
  |---|---|---|
  | A. MCP | Endpoint `/search` en `agent` (recuperación pura; también usado por eval). Servidor MCP = cliente delgado de las APIs (como el frontend). | Servidor MCP + tools `search_docs`, `ask`, `ingest_document`, `list_documents` |
  | B. Híbrida + rerank | Vector `sparse` reservado (D-05); interfaces `Retriever`/`Reranker`; métricas D-12 | BM25 español, fusión RRF, Qwen3-Reranker |
  | C. Streaming | Modelo de eventos + saver async (D-08) | Endpoint SSE + cliente U-10 |
  | D. HITL | Checkpointer Postgres (D-08); nodo `confirm_external_search` pass-through con flag apagado | `interrupt()`, endpoint de reanudación, tarjeta U-11 |
  | E. Observabilidad | `config["callbacks"]` cableado; latencia/tokens por nodo desde eventos | Langfuse (profile `observability`) |
  | F. Ingesta incremental | `content_hash` + versión de modelo de embeddings en `documents` y payload Qdrant (D-05, D-08) | Comparación de hash previa a reindexar; borrado de chunks obsoletos |

- Por qué (y qué se descartó): concentrar el costo en interfaces y contratos (eventos, esquemas) evita refactorizaciones; ningún reto toca el esquema de Qdrant/Postgres ni la topología de servicios. Descartado implementar retos "a medias" desde el inicio (código muerto) y descartado no prever enganches (refactor por reto).
- Tareas afectadas: A-03, A-06…A-09, S-07, O-A…O-F.

### D-14 — Dependencias, calidad de código y convenciones
- Fecha: 2026-11-02
- Estado: Aceptada
- Contexto / requerimiento: calidad de código 15% (estructura, tipado, manejo de errores, tests básicos); historial de commits que muestre avance; ninguna API key en repo ni historial.
- Decisión:

  | Área | Herramienta |
  |---|---|
  | Dependencias Python | uv workspace: `pyproject.toml` raíz con miembros `services/agent`, `services/ingestion`, `packages/common`, `eval`; `uv.lock` único. Docker: `uv sync --frozen --no-dev` con cache mount y lockfile montado |
  | Python | 3.12 (compatibilidad de wheels) |
  | Lint + formato | Ruff |
  | Tipado | mypy (estricto en `packages/common`, moderado en servicios) |
  | Config | pydantic-settings (incluye feature flags D-13) |
  | Tests | pytest + pytest-asyncio + respx + `GenericFakeChatModel` (sin tokens ni red) |
  | Secretos | gitleaks en pre-commit y CI |
  | Pre-commit | ruff, ruff-format, mypy, gitleaks |
  | Frontend | npm + eslint + `tsc --noEmit` |
  | Comandos | Makefile: `up`, `up-gpu`, `seed`, `eval`, `test`, `lint`, `down` |
  | CI | GitHub Actions: lint, mypy, tests, gitleaks |

- Convención de commits (definida por el usuario): en inglés, cortos, formato `[ADD] | [FIX] | [DEL]` + módulo/sección donde aplica. Ejemplos: `[ADD] ingestion: markdown chunker`, `[FIX] agent: rewriter loop limit`, `[DEL] frontend: BBVA branding`. Commits pequeños por tarea del backlog.
- Alcance de tests básicos: chunker (código intacto, metadatos de sección), métricas deterministas (E-11), tools con mock (timeout, vacío, allowlist), enrutamiento y límite del ciclo rewriter con LLM falso. Sin e2e: lo cubre la evaluación sobre el golden set.
- Por qué (y qué se descartó): uv es rápido y reproducible y resuelve el paquete compartido localmente; Ruff unifica lint/formato; mypy hace verificable el tipado; gitleaks hace verificable la regla de secretos. Descartados: Poetry/pip-tools (más lentos, workspace menos natural), black+isort+flake8 (Ruff los reemplaza), Conventional Commits (reemplazado por convención del usuario).
- Tareas afectadas: F-03…F-07, ENT-01, ENT-09.

## Bitácora

Entradas cronológicas (más reciente arriba). Plantilla:

```
### AAAA-MM-DD — Resumen corto
- Hecho:
- Problemas / hallazgos:
- Decisiones tomadas (ref. D-XX):
- Próximos pasos:
```

### 2026-11-02 — Arranque
- Hecho: análisis de la prueba técnica; creado este backlog con todas las tareas pendientes.
- Decisiones tomadas: D-01 (alcance retos), D-02 (LangGraph), D-03 (Claude Haiku/Sonnet 5.5), D-04 (Qwen3-Embedding-0.6B), D-05 (Qdrant + HNSW), D-06 (chunking jerárquico, condicional), D-07 (tools propias sobre Odoo Forum).
- Hallazgos: caso de uso definido = asistente técnico sobre documentación Developer de Odoo 19 (inglés), consultas en español; `robots.txt` de odoo.com prohíbe su buscador del foro; fastembed descartado por catálogo limitado; Qdrant usa búsqueda exacta bajo ~2.500 vectores de 1024 dims.
- Nuevas tareas: V-04 (recall HNSW vs exacto), R-07 (rewriter bilingüe), E-09 (experimento cross-lingual ES vs EN). E-08 descartada por tiempo.
- Próximos pasos: D-08 (checkpointer) en adelante.
- Actualización (cierre de fase de decisiones): D-08…D-14 aceptadas. Las 14 decisiones iniciales quedan cerradas. Skills Docker (`docker/skills`) instaladas en `.claude/skills/` y aplicadas a D-10. Siguiente: documento de diseño y arquitectura end-to-end (`docs/ARCHITECTURE.md`) a partir de este backlog.

### 2026-11-02 — Documento de arquitectura
- Hecho: `docs/ARCHITECTURE.md` generado por agente consolidador (16 secciones, diagramas Mermaid de arquitectura, grafo, secuencia e ingesta).
- Decisiones tomadas: aprobadas las 13 propuestas del documento (rutas/puertos + evento `error`, Haiku en `direct_answer`, grader en lote, defaults numéricos, reducer por turno, citas `[n]` con post-proceso, uuid5/estados/migraciones SQL, `mode=linear` sin memoria, proxy con route handlers, `make seed` vía exec + PDF en host, golden set YAML con `question_en` y JSON a `frontend/public`, MCP stdio en host, BM25 en inglés).
- GAPs resueltos: diagrama del grafo exportado una vez por script y pegado en README, sin endpoint (ENT-10); profile `eval` (E-13); BM25 en inglés (actualización D-05).
- Pendiente: diagramas Mermaid no validados con renderizador.
- Próximos pasos: artefacto explicativo de conceptos del agente basado en grafos; luego implementación Fase 0.

## Riesgos y preguntas abiertas

| ID | Riesgo / Pregunta | Mitigación / Respuesta | Estado |
|---|---|---|---|
| RK-01 | Evaluador sin GPU: embeddings 0.6B en CPU lentos en ingesta | `device=auto` + imagen CPU por defecto; GPU como override de Compose; documentar tiempos | Abierto |
| RK-02 | ~~Dataset debe ser documentación técnica pública en español~~ → Actualizado 2026-11-02: corpus técnico de Odoo 19 (sección Developer), casi todo en inglés | Recuperación cross-lingual si consultas en español (Qwen3 multilingüe la soporta); validar en eval | Abierto |
| RK-03 | `robots.txt` de odoo.com prohíbe el buscador del foro (`Disallow: *?*search=*`) | No usar buscador interno; buscar vía motor externo con `site:` y leer posts individuales (permitidos) | Mitigado (D-07) |
| RK-04 | `ddgs` (API no oficial) puede bloquear por rate limit durante demo | Caché, reintentos con backoff, estados explícitos; plan B SearXNG solo si el test falla | Abierto |
| RK-05 | BM25 (reto B) no ayuda si consulta en español y corpus en inglés | Rewriter bilingüe (R-07) genera variante en inglés; impacto medido en E-09 | Abierto |

## Métricas de avance

_(Se actualizará: obligatorias completadas / total, retos opcionales completados.)_
