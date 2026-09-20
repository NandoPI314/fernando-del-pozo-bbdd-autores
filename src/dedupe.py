"""Deduplicación: el seed no tiene filas repetidas exactas, pero dos nombres
distintos (p.ej. un pseudónimo y el nombre real) pueden resolver al mismo
QID de Wikidata. Se marca la fila más reciente como duplicado de la primera
que apareció con ese QID; no se borra nada, para mantener trazabilidad."""
import datetime as dt

from common.logging_setup import get_logger

logger = get_logger("dedupe")


def run(conn) -> tuple[int, int, dt.datetime, dt.datetime]:
    started_at = dt.datetime.now(dt.timezone.utc)

    with conn.cursor() as cur:
        cur.execute(
            """
            WITH ranked AS (
                SELECT author_id,
                       wikidata_qid,
                       ROW_NUMBER() OVER (PARTITION BY wikidata_qid ORDER BY author_id) AS rn
                FROM core.author
                WHERE wikidata_qid IS NOT NULL
            )
            UPDATE core.author a
            SET duplicate_of_author_id = first.author_id,
                updated_at = now()
            FROM ranked first
            JOIN ranked dupe ON dupe.wikidata_qid = first.wikidata_qid AND first.rn = 1 AND dupe.rn > 1
            WHERE a.author_id = dupe.author_id
            """
        )
        rows_ok = cur.rowcount
    conn.commit()

    finished_at = dt.datetime.now(dt.timezone.utc)
    logger.info("dedupe: %s filas marcadas como duplicadas", rows_ok)
    return rows_ok, 0, started_at, finished_at
