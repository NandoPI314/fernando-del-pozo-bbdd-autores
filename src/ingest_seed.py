"""Carga authors_seed.csv en core.author. Idempotente: reejecutar no
duplica filas (author_name_raw es UNIQUE)."""
import csv
import datetime as dt

from common.logging_setup import get_logger

logger = get_logger("ingest_seed")

# Nombres que no son autores reales (colecciones, desconocidos...). Es una
# lista corta y explícita, no un motor de reglas: con 500 filas conocidas no
# hace falta más, y queda documentado en el informe de calidad.
SPECIAL_CASE_NAMES = {"anonymous", "various authors", "unknown", "unknown author"}


def is_special_case(author_name_raw: str) -> bool:
    return author_name_raw.strip().lower() in SPECIAL_CASE_NAMES


def run(conn, csv_path: str) -> tuple[int, int]:
    started_at = dt.datetime.now(dt.timezone.utc)
    rows_ok = 0
    rows_error = 0

    with open(csv_path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        with conn.cursor() as cur:
            for row in reader:
                name = (row.get("author_name") or "").strip()
                if not name:
                    rows_error += 1
                    logger.warning("Fila vacía/sin author_name en el seed, se ignora")
                    continue
                status = "special_case" if is_special_case(name) else "pending"
                cur.execute(
                    """
                    INSERT INTO core.author (author_name_raw, match_status)
                    VALUES (%s, %s)
                    ON CONFLICT (author_name_raw) DO NOTHING
                    """,
                    (name, status),
                )
                rows_ok += 1
    conn.commit()

    finished_at = dt.datetime.now(dt.timezone.utc)
    logger.info("ingest_seed: %s filas procesadas, %s errores", rows_ok, rows_error)
    return rows_ok, rows_error, started_at, finished_at
