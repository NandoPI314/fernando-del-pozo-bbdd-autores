"""Enriquecimiento de catálogo vía Open Library: señal secundaria y barata
de "cuánta obra publicada tiene este autor" (útil de cara a negocio: volumen
de catálogo disponible). No se usa para desambiguar identidad -eso lo hace
Wikidata-, solo se cuelga sobre el nombre ya normalizado.

Se deja fuera a propósito el desglose de materias (subjects) por autor: exige
una llamada extra por autor a /authors/{olid}/works.json y no aporta lo
suficiente para el tiempo disponible en esta prueba. Queda como limitación
documentada en el informe de calidad.
"""
import datetime as dt
import json
import time

from common import http_client
from common.error_quarantine import quarantine
from common.logging_setup import get_logger

logger = get_logger("open_library")

SEARCH_URL = "https://openlibrary.org/search/authors.json"
REQUEST_DELAY_SECONDS = 0.3


def _store_raw(conn, author_name_raw: str, status: int, data: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw.api_response (source, endpoint, author_name_raw, http_status, response_json)
            VALUES ('open_library', 'search_authors', %s, %s, %s)
            """,
            (author_name_raw, status, json.dumps(data)),
        )
    conn.commit()


def run(conn) -> tuple[int, int, dt.datetime, dt.datetime]:
    started_at = dt.datetime.now(dt.timezone.utc)
    rows_ok = 0
    rows_error = 0

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT author_name_raw, COALESCE(author_name_normalized, author_name_raw)
            FROM core.author
            WHERE match_status IN ('exact', 'ambiguous')
            ORDER BY author_id
            """
        )
        targets = cur.fetchall()

    logger.info("open_library: %s autores a consultar", len(targets))

    for author_name_raw, search_name in targets:
        try:
            status, data = http_client.get_json(SEARCH_URL, params={"q": search_name, "limit": 1})
            _store_raw(conn, author_name_raw, status, data)

            docs = data.get("docs", [])
            if docs:
                doc = docs[0]
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE core.author
                        SET open_library_id = %s,
                            ol_work_count = %s,
                            ol_top_work = %s,
                            updated_at = now()
                        WHERE author_name_raw = %s
                        """,
                        (doc.get("key"), doc.get("work_count"), doc.get("top_work"), author_name_raw),
                    )
                conn.commit()
            rows_ok += 1
        except Exception as exc:  # noqa: BLE001
            conn.rollback()
            quarantine("open_library", author_name_raw, exc)
            logger.error("open_library: fallo enriqueciendo '%s': %s", author_name_raw, exc)
            rows_error += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    finished_at = dt.datetime.now(dt.timezone.utc)
    logger.info("open_library: %s ok, %s errores", rows_ok, rows_error)
    return rows_ok, rows_error, started_at, finished_at
