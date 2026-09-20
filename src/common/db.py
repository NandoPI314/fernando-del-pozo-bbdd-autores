"""Conexión a Postgres y utilidades mínimas compartidas por el pipeline."""
import os
import time
from contextlib import contextmanager

import psycopg


def get_dsn() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'authors_db')} "
        f"user={os.environ.get('POSTGRES_USER', 'authors')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'authors')}"
    )


@contextmanager
def get_connection(retries: int = 10, delay_seconds: float = 2.0):
    """Conecta con reintentos: el contenedor de la app puede arrancar antes
    de que Postgres esté realmente listo para aceptar conexiones."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg.connect(get_dsn(), autocommit=False)
            try:
                yield conn
            finally:
                conn.close()
            return
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise ConnectionError(f"No se pudo conectar a Postgres tras {retries} intentos") from last_error


def apply_schema(conn, sql_dir: str) -> None:
    import glob

    for path in sorted(glob.glob(os.path.join(sql_dir, "*.sql"))):
        with open(path, "r", encoding="utf-8") as fh:
            sql = fh.read()
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def log_run_step(conn, step: str, rows_ok: int, rows_error: int, started_at, finished_at, notes: str = "") -> None:
    duration = (finished_at - started_at).total_seconds()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.run_log (step, rows_ok, rows_error, started_at, finished_at, duration_seconds, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (step, rows_ok, rows_error, started_at, finished_at, duration, notes),
        )
    conn.commit()
