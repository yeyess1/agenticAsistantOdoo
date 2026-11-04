-- One row per answered turn (insights view). Idempotent.
-- turn_id: checkpoint id of the turn's last checkpoint (agentic) or the run id (linear),
-- so the live hook and the checkpoint backfill write the same key.
CREATE TABLE IF NOT EXISTS query_log (
  turn_id             TEXT PRIMARY KEY,
  thread_id           TEXT NOT NULL,
  origin              TEXT NOT NULL CHECK (origin IN ('ui','eval')),
  mode                TEXT NOT NULL CHECK (mode IN ('agentic','linear')),
  question            TEXT NOT NULL,
  standalone_question TEXT NOT NULL DEFAULT '',
  answered_by         TEXT,
  route               TEXT,
  topic               TEXT NOT NULL,
  answer_tokens       INT  NOT NULL DEFAULT 0,   -- output tokens of the answering node
  answer_chars        INT  NOT NULL DEFAULT 0,
  input_tokens        INT  NOT NULL DEFAULT 0,
  output_tokens       INT  NOT NULL DEFAULT 0,
  cost_usd            DOUBLE PRECISION NOT NULL DEFAULT 0,
  latency_ms          INT  NOT NULL DEFAULT 0,
  no_context          BOOLEAN NOT NULL DEFAULT false,
  sources             JSONB NOT NULL DEFAULT '[]', -- [{kind, title, url, cited}]
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS query_log_created_idx ON query_log (created_at);
CREATE INDEX IF NOT EXISTS query_log_origin_idx ON query_log (origin);
