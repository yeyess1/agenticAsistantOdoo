# frontend

Chat and analytics UI for the Odoo 19 agentic RAG assistant (D-09). Next.js 16, React 19, Tailwind 4.

- `/`: chat (U-01…U-09).
- `/analytics`: evaluation dashboard (U-12).

Design tokens live in `src/app/globals.css` (white base, plum primary `#714B67`, IBM Plex Sans + JetBrains Mono). Components use the semantic utilities (`bg-primary`, `text-ink-muted`, `border-line`…), never raw hex.

```bash
npm ci
npm run dev   # http://localhost:3000
```

Adapted from a previous project of the author; the original branding was removed (U-04). API wiring to the agent and ingestion services comes in Phase 3.
