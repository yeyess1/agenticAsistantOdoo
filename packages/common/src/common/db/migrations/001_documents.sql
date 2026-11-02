-- Document registry (V-05, D-08). Idempotent.
CREATE TABLE IF NOT EXISTS documents (
  doc_id          UUID PRIMARY KEY,
  name            TEXT NOT NULL,
  source          TEXT NOT NULL UNIQUE,          -- URL or file name
  mime_type       TEXT NOT NULL,
  content_hash    CHAR(64) NOT NULL,             -- sha256 of the normalized content
  embedding_model TEXT NOT NULL,
  n_chunks        INT  NOT NULL DEFAULT 0,
  status          TEXT NOT NULL CHECK (status IN ('processing','indexed','failed')),
  error           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  ingested_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS documents_status_idx ON documents (status);
