# Evaluación (Fase 4, D-12)

Implementación propia, sin Ragas ni DeepEval: métricas deterministas en `metrics/` (con tests en `tests/`), jueces LLM con prompts versionados en `prompts/` (juez `claude-opus-5-5`, distinto del generator para evitar autoevaluación) y runners en `runners/`.

| Pieza | Archivo |
|---|---|
| Golden set (E-01): 31 preguntas (17 cubiertas, 6 no cubiertas, 4 fuera de alcance, 4 de seguimiento en 2 hilos) | `golden/golden_set.yaml`, validado por `runners/golden.py` |
| Recuperación: recall@k, precision@k, MRR, context precision, corrección de citas | `metrics/retrieval.py`, `metrics/citations.py` |
| Precisión del supervisor (E-04): accuracy + matriz 3×3 con P/R por clase | `metrics/routing.py` |
| Faithfulness, answer relevancy (E-03), answer correctness (E-10), comportamiento esperado | `metrics/{faithfulness,relevancy,correctness,judge}.py` + `prompts/*.md` |
| Lineal vs agéntico (E-05), HITL, hilos de seguimiento | `runners/run_eval.py`, `runners/client.py` |
| HNSW vs exacto (V-04) | `runners/hnsw_vs_exact.py` |
| Español vs inglés (E-09) | `runners/crosslingual.py` |
| Reporte JSON + tablas (E-12) | `runners/report.py` → `reports/<ts>.json`, `latest.json`, `latest.md`, `dashboard.json` |

## Cómo se ejecuta

```bash
make eval                                     # profile `eval` de Compose (E-13): corre dentro de la red interna
make eval ARGS="--only q01,q29"               # subconjunto (un turno de seguimiento arrastra los turnos previos de su hilo)
make eval ARGS="--from-report /app/eval/reports/latest.json --no-hnsw"  # reutiliza respuestas y veredictos; solo re-juzga los que fallaron
```

`make eval` construye la imagen `eval`, la ejecuta con el UID del host (escribe en `eval/reports/`) y copia `reports/dashboard.json` a `frontend/public/eval/latest.json`, que lee `/analytics` (U-12; hay que reconstruir el frontend para publicarlo). Flags útiles: `--no-judges`, `--no-queries`, `--no-hnsw`, `--rejudge`, `--concurrency`.

Cómo se mide:
- Cada pregunta pasa por `POST /query` en `mode=agentic` y `mode=linear` (mismo retriever, mismo generator; solo cambia la orquestación). Los turnos de seguimiento se ejecutan en orden sobre el mismo `thread_id` (en lineal, sin memoria por diseño). Si la respuesta trae un `interrupt` HITL, se aprueba con `POST /query/resume` y se suman pasos, tokens y latencia.
- Contexto juzgado: los chunks que llegan al generator (post-grader en agéntico, los 10 recuperados en lineal). El texto se recupera de Qdrant por `chunk_id`, que ahora viaja en cada `SourceRef`.
- Relevancia de un chunk: coincidencia exacta de `url#anchor` (H1–H4), o de `(coding_guidelines.pdf, página)` para el PDF.
- Faithfulness, relevancy y correctness se aplican a las preguntas con documentación (cubiertas y de seguimiento). En las no cubiertas y fuera de alcance, la `expected_answer` describe un comportamiento, así que el juez da un veredicto pasa/no pasa (`prompts/behaviour.md`) en lugar de un F1.
- Latencia medida en el cliente, por turno completo; tokens y costo desde `usage`/`steps` de la API (precios de `common/pricing.py`).

## Resultados (corrida 2026-11-03, git `76b466c`)

> Muestra pequeña (n entre paréntesis). **El juez quedó incompleto**: el saldo de la API de Anthropic se agotó durante el juicio y 23 veredictos de 7 preguntas (q02, q05, q07, q12, q13, q16, q31) no se obtuvieron. Las 62 respuestas sí se completaron. Por eso las medias de cada modo usan subconjuntos distintos; la línea «Pareado» compara solo las preguntas juzgadas en ambos modos. Para completarlo: `make eval ARGS="--from-report /app/eval/reports/latest.json --no-hnsw"` (re-juzga solo lo que falló, unos 0,6 USD).

**Lineal vs agéntico (E-05)**: mismas preguntas vía `POST /query`; medias por pregunta (`n` entre paréntesis).

| Ámbito | Métrica | Agéntico | Lineal |
|---|---|---|---|
| docs_questions | Faithfulness | 0.97 (17) | 0.97 (17) |
| docs_questions | Answer relevancy | 0.68 (17) | 0.67 (18) |
| docs_questions | Answer correctness (F1) | 0.65 (17) | 0.62 (17) |
| docs_questions | Context precision | 0.89 | 0.68 |
| docs_questions | Context recall (secciones) | 0.60 | 0.61 |
| docs_questions | Chunks al generator | 4.0 | 10.0 |
| docs_questions | Corrección de citas | 0.80 | 0.60 |
| not_covered | Comportamiento esperado (juez) | 1.00 (6) | 1.00 (6) |
| out_of_scope | Comportamiento esperado (juez) | 1.00 (4) | 0.75 (4) |
| all | Latencia p50 (s) | 14.0 | 8.3 |
| all | Latencia p95 (s) | 48.0 | 12.7 |
| all | Tokens de entrada (media) | 8487 | 5032 |
| all | Tokens de salida (media) | 1629 | 1054 |
| all | Costo por pregunta (USD) | 0.0169 | 0.0206 |
| all | Costo total (USD) | 0.523 | 0.639 |

Pareado (solo preguntas juzgadas en ambos modos): faithfulness 0.97 vs 0.96 (n=14, gana agéntico 5, lineal 6); relevancy 0.66 vs 0.67 (n=15, gana agéntico 6, lineal 8); correctness F1 0.64 vs 0.63 (n=14, gana agéntico 7, lineal 5).

**Supervisor (E-04)**: agente final correcto en 30/31 (accuracy 0.97); decisión del router 0.90.

| Esperado \ Obtenido | docs | research | direct | ninguno | Recall |
|---|---|---|---|---|---|
| docs | 21 | 0 | 0 | 0 | 1.00 |
| research | 1 | 5 | 0 | 0 | 0.83 |
| direct | 0 | 0 | 4 | 0 | 1.00 |

**Recuperación (`/search`, top 10, n=19) y cross-lingual (E-09)**

| Consulta | Recall@1 | Recall@5 | Recall@10 | Precision@5 | MRR | Context prec.@10 |
|---|---|---|---|---|---|---|
| Español (original) | 0.25 | 0.54 | 0.64 | 0.47 | 0.82 | 0.74 |
| Inglés (`question_en`) | 0.25 | 0.52 | 0.64 | 0.45 | 0.86 | 0.79 |

**HNSW vs exacto (V-04)**: 62 consultas, top 10, 832 puntos (832 indexados en HNSW, 8 segmentos, m=16, ef_construct=200). Exacto: p50 1.21 ms, p95 1.46 ms.

| hnsw_ef | Recall@1 | Recall@5 | Recall@10 | Recall@10 mín. | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|
| 10 | 0.984 | 0.987 | 0.982 | 0.80 | 1.16 | 1.37 |
| 16 | 1.000 | 1.000 | 0.997 | 0.90 | 1.27 | 1.61 |
| 32 | 1.000 | 1.000 | 1.000 | 1.00 | 1.20 | 1.41 |
| 64 | 1.000 | 1.000 | 1.000 | 1.00 | 1.26 | 1.64 |
| 128 | 1.000 | 1.000 | 1.000 | 1.00 | 1.25 | 1.48 |
| 256 | 1.000 | 1.000 | 1.000 | 1.00 | 1.20 | 1.32 |

**Costo por nodo (agéntico)**

| Nodo | Llamadas | Duración media (ms) | Tokens entrada | Costo (USD) | % costo |
|---|---|---|---|---|---|
| generator | 22 | 8175 | 2394 | 0.3496 | 66.8 |
| research_llm | 15 | 3946 | 2588 | 0.1470 | 28.1 |
| grader | 29 | 3160 | 4939 | 0.0217 | 4.1 |
| router | 31 | 1675 | 673 | 0.0037 | 0.7 |
| rewriter | 5 | 1974 | 942 | 0.0008 | 0.2 |
| direct_answer | 4 | 1171 | 296 | 0.0003 | 0.1 |
| contextualize | 31 | 87 | 52 | 0.0002 | 0.0 |
| retriever | 29 | 274 | 0 | 0.0000 | 0.0 |
| confirm_external_search | 5 | 0 | 0 | 0.0000 | 0.0 |
| tools | 10 | 9947 | 0 | 0.0000 | 0.0 |
| finalize_external | 5 | 0 | 0 | 0.0000 | 0.0 |
| no_context | 2 | 0 | 0 | 0.0000 | 0.0 |

Costo de la corrida: agente agentic $0.523, linear $0.639; juez $2.488; total $3.650.

Lectura rápida:
- **Calidad en preguntas con documentación: empate técnico.** Pareado, F1 0,64 vs 0,63, faithfulness 0,97 vs 0,96 y relevancy 0,66 vs 0,67. Con n=14–15, las diferencias no son significativas. El generator (Sonnet 5.5) casi no alucina en ningún modo.
- **Lo agéntico cambia el contexto, no tanto la redacción:** el grader sube la context precision de 0,68 a 0,89 y la corrección de citas de 0,60 a 0,80, y baja el contexto del generator de 10 a 4 chunks (de 5.280 a 2.424 tokens de entrada) sin perder context recall (0,60 vs 0,61).
- **Costo y latencia:** en cubiertas, el agéntico es un 22 % más barato (0,018 vs 0,023 USD por pregunta), porque el ahorro de tokens del generator paga router y grader, pero un 44 % más lento (13,8 vs 9,6 s, por las llamadas en serie de router y grader). En fuera de alcance cuesta 0,00017 vs 0,013 USD (unas 80 veces menos) y tarda 2,5 vs 4,4 s. En no cubiertas es el caso caro: 36 s de media y 62 s en el peor caso, porque reescribe, delega y busca en el foro.
- **ES vs EN:** recall@10 idéntico (0,64) y MRR 0,82 vs 0,86. Qwen3 recupera bien en cross-lingual y la traducción manual no mejora el recall (E-09).
- **HNSW (V-04):** con el índice ya construido (832/832 vectores), el recall@10 frente al exacto es 1,00 desde `hnsw_ef=32` y 0,98 con `ef=10`. La latencia es ~1,2 ms en ambos casos: con 832 puntos el HNSW no ahorra tiempo, solo valida que los parámetros de D-05 no pierden recall.

## Casos de falla (E-06)

1. **q21 (valoración FIFO, no cubierta): el sistema no delegó al foro.** El router la clasificó como `docs` («concepto de valoración de inventario cubierto por la documentación»). En la primera vuelta, el grader rechazó los 10 chunks; el rewriter tradujo y expandió la consulta (`stock valuation layer FIFO recompute … _run_fifo`) y, en la segunda vuelta, el grader aceptó 2 chunks tangenciales (`Model.invalidate_model` y `upgrade.util.recompute_fields`). Con un chunk «relevante», el subgrafo no emite `no_context`, así que nunca se delega. La respuesta dice con honestidad que la documentación no cubre `stock.valuation.layer`, pero luego rellena con herramientas genéricas de recálculo. El juez de comportamiento la aprobó (no inventa API), pero el agente es incorrecto: es el único error de la matriz (research → docs). Causa: el grader juzga relevancia temática («recalcular campos») y no si el chunk *responde* la pregunta, y el umbral de delegación es «cero chunks relevantes». Mitigaciones: un grader con veredicto de suficiencia («¿con esto se puede responder?»), o delegar cuando solo sobreviven chunks tras una reescritura con score bajo (0,47 en el top-1).
2. **Router de no cubiertas: 3/6 enviadas a `docs` (q21, q22, q23).** q22 y q23 llegan bien a research por el camino largo (2 reescrituras → `no_context` → delegación), con 48 y 62 s de latencia frente a 20–39 s de las que el router manda directo a research. La decisión inicial del router acierta 0,90 (28/31) y el agente final 0,97 (30/31). La red de seguridad del subgrafo funciona, pero cuesta ~3 recuperaciones y 3 llamadas al grader de más.
3. **El rewriter no se activa en las preguntas diseñadas para él (q15–q17, `expects_rewrite`).** Con español coloquial (p. ej. «datos de mentira» en q17), la primera recuperación trae al menos un chunk aceptable y el grader no fuerza la reescritura: context recall 0,33 en q15 y 0,25 en q17, en ambos modos. El rewriter solo corrió en q21–q23 (no cubiertas). Como el recall ES ≈ EN (E-09), traducir no habría ayudado mucho. El problema es de cobertura, no de idioma: el rewriter actúa como plan B ante cero relevantes, no como mejora de recall.
4. **Modo lineal sin memoria (q31) y sin router (q24).** El turno 2 «¿Y si quiero crear uno de esos pero propio…?» en lineal recupera 0 de 3 secciones relevantes y responde sobre *client actions*, el tema equivocado. El agéntico, gracias a `contextualize`, pregunta por «un servicio propio en el cliente web… como `orm`», y el recall@10 pasa de 0 a 0,33. En q24 («Hola, ¿qué puedes hacer?»), el lineal recupera 10 chunks y responde con citas del changelog y de la API JSON-2 (juez: no pasa).
5. **Limitación de la métrica en seguimientos:** la faithfulness marca como no respaldadas las afirmaciones que vienen del turno anterior (p. ej., «ya existe `buyer_id` en `estate.property`» en q29), porque el juez solo ve los chunks del turno y no el historial. Penaliza un poco al agéntico en seguimientos.

## ¿Por qué agéntico? (E-07)

Por nodo: problema que resuelve, ejemplo medido y costo en esta corrida (agéntico, 31 preguntas).

| Nodo | Problema | Evidencia | Costo |
|---|---|---|---|
| `contextualize` | Un seguimiento («uno de esos») no se puede recuperar solo | q31: recall@10 0 → 0,33 con la pregunta reescrita; el lineal responde sobre otro tema. q29: MRR 0,20 → 0,33 | 0,0002 USD en total, 87 ms de media (pass-through sin historial) |
| `router` | No gastar RAG ni foro en saludos u off-topic | 4/4 fuera de alcance a `direct`: 2,5 s y 0,00017 USD vs 4,4 s y 0,013 USD del lineal, que además «responde» el saludo con citas | 0,0037 USD (0,7 % del total), 1,7 s por pregunta. Falla 3/6 no cubiertas (caso 2) |
| `grader` | El top-10 trae ruido; el generator cita chunks irrelevantes | Context precision 0,68 → 0,89; citas correctas 0,60 → 0,80; contexto 10 → 4 chunks y tokens del generator 5.280 → 2.424; recall de secciones 0,61 → 0,60 | 0,022 USD (4 %), 3,2 s por llamada: es la mayor parte de la latencia extra |
| `rewriter` + ciclo | Reintentar cuando no hay nada relevante | Solo se activó en q21–q23: en q22 y q23 llevó a `no_context` y a la delegación correcta; en q21 produjo la falla 1. Sin efecto en q15–q17 (caso 3) | 0,0008 USD, 2 s por reescritura |
| `no_context` → research | La documentación no cubre la pregunta | Agente final correcto en 5/6 no cubiertas (2 por delegación); juez de comportamiento 6/6. El lineal no puede delegar: responde «no está en la documentación» (6/6 aceptables, pero sin fuentes externas) | research: 28 % del costo; 36 s de media |
| `generator` (igual en ambos modos) | — | 67 % del costo; faithfulness 0,97 en ambos modos | 0,35 USD |

Conclusión: en esta muestra, lo agéntico **no mejora la corrección de las respuestas sobre documentación** (empate). Lo que aporta es: (a) un contexto más limpio y citas más precisas al mismo costo o menor, (b) enrutamiento correcto (30/31) con una respuesta directa barata para lo que no es de Odoo, (c) memoria conversacional (sin ella, los seguimientos fallan) y (d) delegación a fuentes externas. El precio es la latencia: +4 s en preguntas cubiertas y hasta 1 minuto en no cubiertas.
