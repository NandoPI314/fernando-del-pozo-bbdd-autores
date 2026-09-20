-- Capa core: una fila por autor del seed, enriquecida y deduplicada.
-- author_name_raw es la clave natural (viene del CSV); author_id es la
-- surrogate key entera para joins futuros baratos.

CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.author (
    author_id               SERIAL PRIMARY KEY,
    author_name_raw         TEXT NOT NULL UNIQUE,
    author_name_normalized  TEXT,

    -- Identidad / desambiguación (Wikidata)
    wikidata_qid            VARCHAR(16),
    birth_year              INTEGER,
    death_year              INTEGER,
    nationality             TEXT,
    is_public_domain        BOOLEAN,
    public_domain_basis     TEXT,

    -- Catálogo (Open Library)
    open_library_id         VARCHAR(32),
    ol_work_count           INTEGER,
    ol_top_work             TEXT,

    -- Control de calidad del matching
    match_status            VARCHAR(16) NOT NULL DEFAULT 'pending',
        -- pending | exact | ambiguous | not_found | special_case
    match_confidence        NUMERIC(3,2),
    match_notes             TEXT,

    -- Deduplicación (dos nombres del seed que resuelven a la misma entidad,
    -- p.ej. pseudónimos)
    duplicate_of_author_id  INTEGER REFERENCES core.author (author_id),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_core_author_qid ON core.author (wikidata_qid);
CREATE INDEX IF NOT EXISTS idx_core_author_status ON core.author (match_status);

CREATE TABLE IF NOT EXISTS core.run_log (
    run_id            BIGSERIAL PRIMARY KEY,
    step              VARCHAR(64) NOT NULL,
    rows_ok           INTEGER NOT NULL DEFAULT 0,
    rows_error        INTEGER NOT NULL DEFAULT 0,
    started_at        TIMESTAMPTZ NOT NULL,
    finished_at       TIMESTAMPTZ NOT NULL,
    duration_seconds  NUMERIC(10, 2) NOT NULL,
    notes             TEXT
);
