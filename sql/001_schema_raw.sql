-- Capa raw: respuesta cruda de cada API, tal cual llega, con marca de tiempo.
-- Un único formato de tabla para todas las fuentes: permite reprocesar (recalcular
-- core.author) sin volver a golpear las APIs externas, y deja rastro de qué se
-- consultó y cuándo para el informe de calidad.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.api_response (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(32) NOT NULL,      -- 'wikidata' | 'open_library'
    endpoint        VARCHAR(64) NOT NULL,      -- p.ej. 'wbsearchentities', 'wbgetentities', 'search_authors'
    author_name_raw TEXT NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    http_status     INTEGER,
    response_json   JSONB
);

CREATE INDEX IF NOT EXISTS idx_raw_api_response_author
    ON raw.api_response (author_name_raw, source, endpoint);
