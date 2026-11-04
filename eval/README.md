# Evaluación (Fase 4, D-12)

Implementación propia, sin Ragas ni DeepEval: métricas deterministas en `metrics/` (con tests en `tests/`), jueces LLM con prompts versionados en `prompts/` (juez = `LLM_MODEL_JUDGE`, distinto del generator para evitar autoevaluación: `gemini-3.6-flash` en la corrida actual, `claude-opus-5-5` en la anterior) y runners en `runners/`.

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

## Resultados (corrida 2026-11-03, git `a4f12e0`, Gemini)

Corrida completa: 31 preguntas × 2 modos, con los 146 veredictos del juez y 0 errores. Modelos: `gemini-3.5-flash-lite` (contextualizer, router, grader, rewriter, direct), `gemini-3.8-flash` (generator, research) y juez `gemini-3.6-flash`. Settings: `RETRIEVER_TOP_K=10`, `MAX_REWRITES=2`, `QDRANT_HNSW_EF=128`, retriever `dense`, sin reranker y sin HITL. Los costos usan los precios del tier pagado (`common/pricing.py`); en el tier gratis la corrida cuesta 0.

**Lineal vs agéntico (E-05)**: mismas preguntas vía `POST /query`; medias por pregunta (`n` entre paréntesis).

| Ámbito | Métrica | Agéntico | Lineal |
|---|---|---|---|
| docs_questions | Faithfulness | 0.98 (21) | 1.00 (21) |
| docs_questions | Answer relevancy | 0.65 (21) | 0.66 (21) |
| docs_questions | Answer correctness (F1) | 0.72 (21) | 0.76 (21) |
| docs_questions | Context precision | 0.90 | 0.68 |
| docs_questions | Context recall (secciones) | 0.52 | 0.61 |
| docs_questions | Chunks al generator | 2.8 | 10.0 |
| docs_questions | Corrección de citas | 0.81 | 0.73 |
| not_covered | Comportamiento esperado (juez) | 0.83 (6) | 0.50 (6) |
| out_of_scope | Comportamiento esperado (juez) | 1.00 (4) | 0.50 (4) |
| all | Latencia p50 (s) | 13.1 | 9.5 |
| all | Latencia p95 (s) | 35.6 | 13.4 |
| all | Tokens de entrada (media) | 5263 | 3757 |
| all | Tokens de salida (media) | 1328 | 907 |
| all | Costo por pregunta (USD) | 0.0069 | 0.0062 |
| all | Costo total (USD) | 0.215 | 0.193 |

Pareado (solo preguntas juzgadas en ambos modos): faithfulness 0.98 vs 1.00 (n=21, gana agéntico 0, lineal 1); relevancy 0.65 vs 0.66 (n=21, gana agéntico 9, lineal 12); correctness F1 0.72 vs 0.76 (n=21, gana agéntico 5, lineal 11).

**Supervisor (E-04)**: agente final correcto en 31/31 (accuracy 1.00); decisión del router 0.94.

| Esperado \ Obtenido | docs | research | direct | ninguno | Recall |
|---|---|---|---|---|---|
| docs | 21 | 0 | 0 | 0 | 1.00 |
| research | 0 | 6 | 0 | 0 | 1.00 |
| direct | 0 | 0 | 4 | 0 | 1.00 |

**Recuperación (`/search`, top 10, n=19) y cross-lingual (E-09)**

| Consulta | Recall@1 | Recall@5 | Recall@10 | Precision@5 | MRR | Context prec.@10 |
|---|---|---|---|---|---|---|
| Español (original) | 0.25 | 0.54 | 0.64 | 0.47 | 0.82 | 0.74 |
| Inglés (`question_en`) | 0.25 | 0.52 | 0.64 | 0.45 | 0.86 | 0.79 |

**HNSW vs exacto (V-04)**: 62 consultas, top 10, 832 puntos (832 indexados en HNSW, 8 segmentos, m=16, ef_construct=200). Exacto: p50 1.29 ms, p95 1.88 ms.

| hnsw_ef | Recall@1 | Recall@5 | Recall@10 | Recall@10 mín. | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|
| 10 | 0.984 | 0.987 | 0.982 | 0.80 | 1.25 | 1.88 |
| 16 | 1.000 | 1.000 | 0.997 | 0.90 | 1.40 | 1.71 |
| 32 | 1.000 | 1.000 | 1.000 | 1.00 | 1.34 | 1.61 |
| 64 | 1.000 | 1.000 | 1.000 | 1.00 | 1.49 | 1.93 |
| 128 | 1.000 | 1.000 | 1.000 | 1.00 | 1.46 | 1.90 |
| 256 | 1.000 | 1.000 | 1.000 | 1.00 | 1.39 | 2.10 |

**Costo por nodo (agéntico)**

| Nodo | Llamadas | Duración media (ms) | Tokens entrada | Costo (USD) | % costo |
|---|---|---|---|---|---|
| generator | 21 | 9744 | 1390 | 0.1110 | 51.5 |
| grader | 27 | 1799 | 3362 | 0.0545 | 25.3 |
| research_llm | 24 | 3665 | 1359 | 0.0424 | 19.7 |
| router | 31 | 1026 | 252 | 0.0053 | 2.5 |
| rewriter | 4 | 1053 | 335 | 0.0011 | 0.5 |
| direct_answer | 4 | 838 | 206 | 0.0007 | 0.3 |
| contextualize | 31 | 62 | 19 | 0.0003 | 0.1 |
| retriever | 27 | 366 | 0 | 0.0000 | 0.0 |
| confirm_external_search | 6 | 0 | 0 | 0.0000 | 0.0 |
| tools | 18 | 4664 | 0 | 0.0000 | 0.0 |
| finalize_external | 6 | 0 | 0 | 0.0000 | 0.0 |
| no_context | 2 | 0 | 0 | 0.0000 | 0.0 |

Costo de la corrida: agente agentic $0.215, linear $0.193; juez $0.719; total $1.127.

Lectura rápida:
- **Calidad sobre documentación: el lineal gana por poco.** F1 0,72 vs 0,76 (el agéntico gana 5 preguntas y pierde 11 de 21), relevancy 0,65 vs 0,66 y faithfulness 0,98 vs 1,00. Cuando el corpus cubre la pregunta, el top-10 denso ya trae lo necesario.
- **Lo agéntico mejora el contexto, pero aquí filtra de más.** Context precision 0,90 vs 0,68, corrección de citas 0,81 vs 0,73 y un 65 % menos de tokens en el generator (1.390 vs 3.965). El grader con Flash-Lite deja 2,8 chunks y el context recall baja a 0,52 vs 0,61 (caso 1).
- **Decisiones: aquí sí gana el agéntico.** Agente final 31/31 (router 0,94 al primer intento), comportamiento en fuera de alcance 4/4 vs 2/4 y en no cubiertas 5/6 vs 3/6. Es el juicio del mismo rubric en los dos modos; el lineal no puede delegar por diseño.
- **Costo y latencia por categoría** (media por pregunta, agéntico vs lineal):

  | Categoría | Costo (USD) | Latencia media (s) |
  |---|---|---|
  | Cubiertas | 0,0079 vs 0,0071 | 13,6 vs 10,4 |
  | No cubiertas | 0,0094 vs 0,0053 | 32,6 vs 7,8 (máx. 48,7) |
  | Fuera de alcance | 0,0003 vs 0,0043 | 1,7 vs 5,5 |
  | Seguimientos | 0,0058 vs 0,0058 | 10,5 vs 7,8 |

  El agente es 14 veces más barato y 3 veces más rápido en lo que no es de Odoo, y es el caso caro en lo no cubierto, porque reescribe, delega y busca en el foro.
- **ES vs EN (E-09):** recall@10 idéntico (0,64) y MRR 0,82 vs 0,86. Qwen3 recupera bien en cross-lingual; traducir la consulta no mejora el recall.
- **HNSW (V-04):** recall@10 frente al exacto de 1,00 desde `hnsw_ef=32` (0,98 con `ef=10`), con ~1,3 ms en ambos casos. Con 832 puntos el HNSW no ahorra tiempo; la corrida valida que los parámetros de D-05 no pierden recall.

### Comparación con la corrida anterior (Claude, git `76b466c`)

| Métrica | Agéntico Claude | Lineal Claude | Agéntico Gemini | Lineal Gemini |
|---|---|---|---|---|
| Correctness F1 | 0,65 | 0,62 | 0,72 | 0,76 |
| Context precision | 0,89 | 0,68 | 0,90 | 0,68 |
| Context recall | 0,60 | 0,61 | 0,52 | 0,61 |
| Chunks al generator | 4,0 | 10 | 2,8 | 10 |
| Corrección de citas | 0,80 | 0,60 | 0,81 | 0,73 |
| Agente final correcto | 30/31 | — | 31/31 | — |
| Latencia p50 | 14,0 s | 8,3 s | 13,1 s | 9,5 s |

Los jueces son distintos (Opus 5.5 vs Gemini 3.6 Flash) y la corrida de Claude quedó con 23 veredictos sin obtener, así que la comparación es indicativa. Aun así, el patrón es consistente: el grader con Haiku enviaba 4,0 chunks y no perdía recall; el de Flash-Lite envía 2,8 y pierde 9 puntos. **Lo estricto del grader depende del modelo**, y es la palanca principal de F1 en preguntas cubiertas.

## Casos de falla (E-06)

1. **q08: el grader descarta contexto necesario en una pregunta compuesta.** «Renombré un campo: ¿cómo escribo el script de migración para no perder datos ni romper filtros?». De 10 chunks, el grader conservó 2 (`rename_field` de *upgrade utils*). Descartó los que explican la estructura del script (`migrate(cr, version)`, la carpeta `migrations/<versión>/` y los prefijos `pre-`, `post-` y `end-`), porque los juzgó contra la mitad literal de la pregunta. Context recall 0,17 vs 0,67 del lineal y F1 0,42 vs 0,63. Es el caso extremo de un patrón: el agéntico tiene menos recall que el lineal en 7 de 21 preguntas (q02–q04, q06–q09) y en ninguna tiene más. Mitigación: un veredicto de **suficiencia** del conjunto en vez de relevancia por chunk, o un mínimo de chunks por subpregunta.
2. **q31: `contextualize` resuelve mal una correferencia.** Turno 1: «desde un componente OWL, ¿cómo llamo a un método Python?», cuya respuesta habla del servicio `orm`. Turno 2: «¿y si quiero crear uno de esos pero propio…?». Flash-Lite lo reescribió como «¿cómo defino un **componente OWL** propio?», cuando la referencia era un **servicio**. El agente recuperó chunks de client actions y respondió con seguridad y citas, pero a otra pregunta: 0 chunks relevantes y F1 = 0. El nodo sí recibe la respuesta anterior (recortada a 800 caracteres), y empieza con «se debe utilizar el servicio `orm`»: es un error de resolución, no de falta de información. En la corrida con Claude Haiku la misma pregunta se reescribió bien («un servicio propio… como `orm`»). Mitigación: indicar en el prompt que resuelva las referencias hacia la entidad que explicó la última respuesta, usar un modelo más capaz solo para este rol (es barato: solo corre con historial y procesa pocos tokens) y pedir aclaración si hay dos candidatos.
3. **q19: delega bien, pero no avisa.** Responde desde el foro (OpenUpgrade de v16 a v17), pero sin decir antes que la documentación indexada no cubre migraciones entre versiones mayores. El juez de comportamiento no la aprueba. Es la única no cubierta que falla (5/6). Mitigación: que `finalize_external` anteponga siempre la nota de delegación, también cuando el router manda directo a research (hoy solo se agrega cuando `delegated=true`).
4. **El router manda 2 no cubiertas a `docs` (q22, q23).** Llegan bien a research por el camino largo: 2 reescrituras, `no_context` y delegación, con 3 recuperaciones y 3 llamadas al grader de más. Por eso la decisión inicial del router es 0,94 y el agente final 1,00.
5. **El rewriter no se activa en las preguntas diseñadas para él (q15–q17, `expects_rewrite`).** Con español coloquial («datos de mentira», «se le rellenen solitos»), el grader acepta 1 o 2 chunks en la primera vuelta y el rewriter nunca corre: context recall de 0,33 en q15 y de 0,25 en q17. Solo se activó en q22 y q23. Actúa como plan B ante cero relevantes, no como mejora de recall.
6. **Limitación de la métrica en seguimientos (q28).** La faithfulness del agéntico baja a 0,67 porque el generator reutiliza un detalle del turno anterior (`buyer_id` con `copy=False`) y el juez solo ve los chunks del turno, no el historial. Penaliza un poco al agéntico, que es el único con memoria.

## ¿Por qué agéntico? (E-07)

Por nodo: el problema que resuelve, la evidencia medida en esta corrida (agéntico, 31 preguntas) y su costo.

| Nodo | Problema | Evidencia | Costo |
|---|---|---|---|
| `contextualize` | Un seguimiento («uno de esos») no se puede recuperar solo | Imprescindible en diseño: el lineal no tiene memoria. En esta corrida falló en q31 (caso 2); en la de Claude la resolvió bien | 0,0003 USD en total y 62 ms de media (pass-through sin historial) |
| `router` | No gastar RAG ni foro en saludos u off-topic | 4/4 fuera de alcance a `direct`: 1,7 s y 0,0003 USD vs 5,5 s y 0,0043 USD del lineal, que enumera temas con citas ante un «hola» y no reconoce que «invertir una cadena en Python» está fuera de alcance | 0,0053 USD (2,5 %) y 1,0 s por pregunta |
| `grader` | El top-10 trae ruido; el generator cita chunks irrelevantes | Context precision 0,68 → 0,90, citas 0,73 → 0,81, tokens del generator 3.965 → 1.390. Pero el recall baja de 0,61 a 0,52 (caso 1) | 0,055 USD (25 %) y 1,8 s por llamada |
| `rewriter` + ciclo | Reintentar cuando no hay nada relevante | En q22 y q23 llevó a `no_context` y a la delegación correcta. Sin efecto en q15–q17 (caso 5) | 0,0011 USD y 1,1 s por reescritura |
| `no_context` → research | La documentación no cubre la pregunta | 6/6 no cubiertas terminan en research (2 por delegación); comportamiento 5/6 vs 3/6 del lineal, que dice «no está en la documentación» sin fuentes externas | research_llm 20 % del costo; 32,6 s de media en no cubiertas |
| `generator` (igual en ambos modos) | — | 52 % del costo; faithfulness 0,98 vs 1,00 | 0,11 USD |

Conclusión: en esta muestra, lo agéntico **no mejora la corrección de las respuestas cuando la documentación cubre la pregunta**; con Flash-Lite como grader, la empeora un poco. Aporta: (a) contexto más limpio y citas más precisas con un 65 % menos de tokens en el generator, (b) enrutamiento correcto (31/31) con una respuesta directa barata y rápida para lo que no es de Odoo, (c) delegación a fuentes externas cuando la documentación no alcanza y (d) memoria conversacional. El precio es la latencia: +3 s en cubiertas y hasta 49 s en no cubiertas. Y la calidad de las decisiones intermedias (grader, contextualize) depende del modelo de cada rol.
