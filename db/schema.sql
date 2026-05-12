-- Datasheet RAG schema
-- Requires: PostgreSQL 15+ with pgvector extension
--
-- Embedding model: sentence-transformers/all-MiniLM-L6-v2 (dim=384)
-- Change vector(384) if switching to a different model.
--
-- Embedding text strategy per table:
--   max_ratings              "{symbol} {parameter}: {value_raw} {unit}[, {condition_raw}]"
--   thermal_characteristics  "{symbol} {parameter}: {typ} {unit}"
--   electrical_characteristics "[{section}] {symbol} {parameter}[, {condition_raw}]: typ/max/min {unit}"
--   typical_charts           "{caption}"
--   footnotes                "Note {marker}: {text}"

CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------
-- parts  (no embedding — structured lookup only)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parts (
    part_id     TEXT    NOT NULL,
    package     TEXT    NOT NULL,
    marking     TEXT    NOT NULL,
    packing     TEXT,
    source_page INTEGER NOT NULL,
    table_ref   TEXT    NOT NULL,
    PRIMARY KEY (part_id)
);

-- -----------------------------------------------------------------------
-- max_ratings
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS max_ratings (
    part_id              TEXT    NOT NULL,
    symbol               TEXT    NOT NULL,
    parameter            TEXT    NOT NULL,
    condition_raw        TEXT,
    condition_kv         JSONB,
    condition_normalized TEXT    NOT NULL DEFAULT '',
    value_raw            TEXT    NOT NULL,
    value_num            REAL,
    value_min            REAL,
    value_max_num        REAL,
    unit                 TEXT    NOT NULL,
    footnote_ref         TEXT,
    source_page          INTEGER NOT NULL,
    table_ref            TEXT    NOT NULL,
    embedding            vector(384),
    PRIMARY KEY (part_id, symbol, condition_normalized)
);

CREATE INDEX IF NOT EXISTS max_ratings_part_id_idx ON max_ratings (part_id);

-- -----------------------------------------------------------------------
-- thermal_characteristics
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS thermal_characteristics (
    part_id     TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    parameter   TEXT    NOT NULL,
    typ         REAL    NOT NULL,
    unit        TEXT    NOT NULL,
    source_page INTEGER NOT NULL,
    table_ref   TEXT    NOT NULL,
    embedding   vector(384),
    PRIMARY KEY (part_id, symbol)
);

CREATE INDEX IF NOT EXISTS thermal_part_id_idx ON thermal_characteristics (part_id);

-- -----------------------------------------------------------------------
-- electrical_characteristics
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS electrical_characteristics (
    part_id              TEXT    NOT NULL,
    symbol               TEXT    NOT NULL,
    parameter            TEXT    NOT NULL,
    section              TEXT    NOT NULL,
    condition_raw        TEXT,
    condition_kv         JSONB,
    condition_normalized TEXT    NOT NULL DEFAULT '',
    min                  REAL,
    typ                  REAL,
    max                  REAL,
    value_raw            TEXT,
    unit                 TEXT    NOT NULL,
    footnote_ref         TEXT,
    source_page          INTEGER NOT NULL,
    table_ref            TEXT    NOT NULL,
    embedding            vector(384),
    PRIMARY KEY (part_id, symbol, condition_normalized)
);

CREATE INDEX IF NOT EXISTS elec_part_id_idx ON electrical_characteristics (part_id);
CREATE INDEX IF NOT EXISTS elec_symbol_idx  ON electrical_characteristics (symbol);

-- -----------------------------------------------------------------------
-- typical_charts
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS typical_charts (
    part_id     TEXT    NOT NULL,
    caption     TEXT    NOT NULL,
    source_page INTEGER NOT NULL,
    minio_key   TEXT    NOT NULL,
    table_ref   TEXT    NOT NULL,
    embedding   vector(384),
    PRIMARY KEY (part_id, minio_key)
);

CREATE INDEX IF NOT EXISTS charts_part_id_idx ON typical_charts (part_id);

-- -----------------------------------------------------------------------
-- footnotes
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS footnotes (
    part_id   TEXT NOT NULL,
    marker    TEXT NOT NULL,
    text      TEXT NOT NULL,
    embedding vector(384),
    PRIMARY KEY (part_id, marker)
);

-- -----------------------------------------------------------------------
-- Vector indexes — enable after data is loaded
-- HNSW gives best query speed; tune m/ef_construction to dataset size.
--
-- CREATE INDEX elec_emb_idx    ON electrical_characteristics USING hnsw (embedding vector_cosine_ops);
-- CREATE INDEX max_emb_idx     ON max_ratings                USING hnsw (embedding vector_cosine_ops);
-- CREATE INDEX thermal_emb_idx ON thermal_characteristics    USING hnsw (embedding vector_cosine_ops);
-- CREATE INDEX charts_emb_idx  ON typical_charts             USING hnsw (embedding vector_cosine_ops);
-- CREATE INDEX fn_emb_idx      ON footnotes                  USING hnsw (embedding vector_cosine_ops);
-- -----------------------------------------------------------------------
