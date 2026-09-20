"""Punto de entrada único del pipeline. Orden de pasos:
schema -> ingesta seed -> Wikidata (identidad) -> Open Library (catálogo)
-> dedupe -> informe de calidad. Cada paso registra sus métricas en
core.run_log, y cada paso es re-ejecutable sin duplicar datos.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import dedupe
import generate_report
import ingest_seed
from common.db import apply_schema, get_connection, log_run_step
from common.logging_setup import get_logger
from sources import open_library, wikidata

logger = get_logger("run_pipeline")

CSV_PATH = os.environ.get("SEED_CSV_PATH", "authors_seed.csv")
SQL_DIR = os.environ.get("SQL_DIR", "sql")


def main() -> None:
    with get_connection() as conn:
        logger.info("Aplicando esquema SQL desde %s", SQL_DIR)
        apply_schema(conn, SQL_DIR)

        steps = [
            ("ingest_seed", lambda: ingest_seed.run(conn, CSV_PATH)),
            ("wikidata_enrichment", lambda: wikidata.run(conn)),
            ("open_library_enrichment", lambda: open_library.run(conn)),
            ("dedupe", lambda: dedupe.run(conn)),
        ]

        for step_name, fn in steps:
            logger.info("=== Paso: %s ===", step_name)
            rows_ok, rows_error, started_at, finished_at = fn()
            log_run_step(conn, step_name, rows_ok, rows_error, started_at, finished_at)

        generate_report.run(conn)

    logger.info("Pipeline completado.")


if __name__ == "__main__":
    main()
