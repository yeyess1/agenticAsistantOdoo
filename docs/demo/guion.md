# Guion del video demo (ENT-07, ≤ 5 min)

Cubre lo que pide la prueba: **ingesta → consulta con citas → rewriter activo → caída a
investigación → fuera de alcance**. Cada pregunta se probó contra el stack real el 2026-11-03
(modelos Gemini) y se indica lo que debe verse en pantalla.

## Antes de grabar

- [ ] `make ps`: todos los servicios en healthy, con `LLM_PROVIDER=google` en el `.env`.
- [ ] El documento de demo **no** está cargado: el panel de documentos muestra 59 documentos y
      ninguno es *System configuration*. Si quedó de un ensayo, bórralo desde el panel o con
      `curl -X DELETE localhost:8001/documents/98410570-35c6-5eed-8376-2473dc323327`.
- [ ] Archivo a subir: `~/Descargas/system-configuration-odoo19.md` (copia de
      `data/demo/administration__on_premise__deploy.md`). Es la página oficial *System
      configuration* (despliegue on-premise), que no está en el corpus, convertida a Markdown con el
      mismo extractor del scraper. Su frontmatter trae la URL oficial, así que las citas apuntan
      a odoo.com.
- [ ] Pestañas abiertas: http://localhost:3000 (chat, modo **Agéntico**) y
      http://localhost:6333/dashboard (Qdrant).
- [ ] Usa una **conversación nueva por pregunta**: así `contextualize` no mezcla los temas.
- [ ] Primera pregunta de calentamiento fuera de cámara: carga los modelos y evita la latencia
      fría en la toma.

## Flujo

| # | Tiempo | Escena | Qué mostrar |
|---|---|---|---|
| 0 | 0:00–0:20 | Intro | El chat y, en una frase, qué hace: asistente agéntico sobre la documentación de Odoo 19 con supervisor, agente de documentación y agente de investigación |
| 1 | 0:20–0:50 | El documento no existe | Panel de documentos: 59 documentos, sin *System configuration*. En Qdrant, colección `odoo19_dev`: 832 puntos |
| 2 | 0:50–1:30 | Ingesta | Subir `system-configuration-odoo19.md` desde el panel. Resultado: **29 chunks**, estado *indexed*, ~80 s en CPU (se puede cortar en la edición) |
| 3 | 1:30–2:00 | Verlo en Qdrant | Colección `odoo19_dev`: **861 puntos** (832 + 29). En la pestaña **Console**, ejecutar la consulta de abajo para ver los chunks con `doc_id`, `section` y `url` |
| 4 | 2:00–2:45 | Pregunta sobre el documento nuevo | Pregunta A. La respuesta cita *System configuration* y hace el cálculo |
| 5 | 2:45–3:30 | Rewriter activo | Pregunta B. En los pasos del agente: `grader` (0 relevantes) → **`rewriter`** → `retriever` → `grader` (2–3 relevantes) → `generator` |
| 6 | 3:30–4:20 | Caída a investigación | Pregunta C. Ruta `research`, posts del foro como fuente externa |
| 7 | 4:20–4:45 | Fuera de alcance | Pregunta D. `direct_answer` en ~2 s, sin recuperar nada |
| 8 | 4:45–5:00 | Cierre | Opcional: `/analytics` con los resultados de la evaluación |

### Consulta en la consola de Qdrant (escena 3)

```
POST collections/odoo19_dev/points/scroll
{
  "filter": { "must": [ { "key": "doc_id", "match": { "value": "98410570-35c6-5eed-8376-2473dc323327" } } ] },
  "limit": 5,
  "with_payload": true,
  "with_vector": false
}
```

El `doc_id` es determinista (uuid5 de la URL del documento), así que es el mismo en cada ensayo.
Para contar los chunks del documento, usa `POST collections/odoo19_dev/points/count` con el mismo
`filter` y `"exact": true`: debe dar 29.

## Preguntas

### A. Sobre el documento recién cargado

> **Según la documentación oficial de Odoo 19, ¿cómo calculo el número de workers y la RAM necesaria para un servidor con 4 CPU y 60 usuarios concurrentes?**

- **Esperado:** ruta `docs` con fuentes de *System configuration › Builtin server › memory size
  calculation* y *› Configuration sample*. La respuesta hace el cálculo: 60 / 6 = 10 workers por
  usuarios, (4 × 2) + 1 = 9 como máximo por CPU, y 8 workers + 1 cron en la configuración
  de ejemplo, con la RAM según la proporción 80/20 de peticiones livianas y pesadas. Tarda ~14 s.
- **Mantén el "Según la documentación oficial".** Sin esa frase, el router manda la pregunta al
  foro (`research`) aunque el documento esté cargado, porque su prompt describe el índice como
  documentación de *desarrollo* y clasifica el dimensionamiento como "performance tuning".
  Es una limitación conocida (ver *Notas*).
- **Contraste opcional (+30 s):** hacer la misma pregunta *antes* de la ingesta. Responde desde
  el foro, aclarando que son opiniones de la comunidad sobre versiones anteriores. Después de la
  ingesta, responde con la documentación oficial.

### B. Rewriter activo

> **En Laravel uso los observers de Eloquent para ejecutar lógica cada vez que se crea un registro, ¿cuál es el equivalente en Odoo 19?**

- **Esperado:** en la primera vuelta el grader rechaza los 10 chunks, porque "observers de Eloquent"
  no existe en Odoo. El **rewriter** reformula la pregunta en inglés con vocabulario de Odoo (por
  ejemplo, `model create method override ORM api lifecycle triggers`). La segunda recuperación
  encuentra *Chapter 12: Inheritance › Python Inheritance*, y la respuesta explica que hay que
  sobrescribir `create()` y llamar a `super().create(vals_list)`, con cita. Se activó en
  **4 de 4** corridas, con 1 reescritura; tarda ~13 s.
- **Respaldo:** *"En Spring uso la anotación @PrePersist en mis entidades JPA, ¿cómo consigo ese
  comportamiento en Odoo 19?"*. También 4 de 4, a veces con **dos** reescrituras (se ve mejor el
  ciclo), pero tarda ~19 s.
- **Descartada:** la de Rails (`before_save`) activó el rewriter solo 5 de 7 veces. El grader
  (Flash-Lite) a veces acepta en la primera vuelta un chunk dudoso (*Constraints › SQL*), y
  entonces no reescribe.
- **Qué decir:** el agente no se queda con una mala recuperación: reconoce que no hay contexto
  útil, traduce el concepto de otro framework al vocabulario de Odoo y vuelve a buscar. El pipeline
  lineal habría respondido con los 10 chunks irrelevantes.
- **Por qué no una del golden set:** las preguntas coloquiales en español (q15–q17) no activan el
  rewriter, porque Qwen3 ya recupera bien en la primera vuelta (caso de falla 5 en
  `eval/README.md`). Hace falta un vocabulario que el corpus no usa.

### C. No cubierta: investigación en el foro

> **Tengo mi base de datos en Odoo.sh y quiero migrarla a un servidor propio on-premise. ¿Cómo descargo el backup con el filestore y lo restauro en mi servidor?**

- **Esperado:** ruta `research`: `confirm_external_search` → `research_llm` ↔ `tools` (3 búsquedas
  y lecturas) → `finalize_external`. Entre las fuentes aparece el hilo *How do I migrate/transfer
  an Odoo.sh database to on-premise?*. La respuesta aclara que viene de la comunidad. Tarda ~30 s.
- Odoo.sh no está en el corpus, y el documento recién cargado (configuración on-premise) no la
  "atrapa": el router la manda directo al foro.
- **Alternativa con el camino largo** (docs → 2 reescrituras → `no_context` → delegación), para
  mostrar la red de seguridad del subgrafo: q22 del golden set, *"¿Cómo configuro un modelo de
  conciliación bancaria (account.reconcile.model) para que case automáticamente…?"*. Tarda ~45 s.

### D. Fuera de alcance

> **¿Cuál es la capital de París?**

- **Esperado:** ruta `direct`: `contextualize` → `router` → `direct_answer`, en ~2 s. Responde que
  está fuera de su ámbito y ofrece ayuda con Odoo 19. No recupera chunks ni llama al generator.
- París es una ciudad, así que la pregunta no tiene respuesta. Si prefieres una pregunta "normal",
  *"¿Cuál es la capital de Francia?"* da el mismo resultado.

## Notas

- **Limitación del router (pregunta A):** el prompt del router fija el alcance en la
  documentación de desarrollo. Cuando se ingieren documentos de otras áreas (administración,
  despliegue), el router no lo sabe. Mejora propuesta: describir el índice como "documentación
  oficial indexada (Developer + documentos cargados)" y preferir `docs` para cualquier pregunta
  técnica de Odoo, dejando que la delegación por `no_context` cubra lo que falte.
- Las latencias son con Gemini en el tier gratis y TEI en CPU. Un 429 en `make logs` significa
  que se alcanzó el límite de peticiones: espera un minuto entre tomas.
- Atribución: el documento de demo proviene de la documentación de Odoo
  (https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html), bajo
  CC BY-SA 4.0, convertido a Markdown sin cambios de contenido.
