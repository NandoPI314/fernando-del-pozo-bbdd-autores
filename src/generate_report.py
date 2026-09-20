"""Genera reports/informe_calidad.md a partir del estado final de core.author.
Es el entregable de "calidad, limitaciones y casos dudosos" que pide el
enunciado: se genera desde datos reales, no se escribe a mano."""
import datetime as dt
import glob
import os

from common.logging_setup import get_logger

logger = get_logger("generate_report")


def _count_error_files() -> int:
    return len(glob.glob(os.path.join("data", "errors", "**", "*.json"), recursive=True))


def run(conn, output_path: str = os.path.join("reports", "informe_calidad.md")) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM core.author")
        total = cur.fetchone()[0]

        cur.execute("SELECT match_status, count(*) FROM core.author GROUP BY match_status ORDER BY match_status")
        status_counts = cur.fetchall()

        cur.execute("SELECT count(*) FROM core.author WHERE duplicate_of_author_id IS NOT NULL")
        duplicate_count = cur.fetchone()[0]

        cur.execute(
            "SELECT is_public_domain, count(*) FROM core.author GROUP BY is_public_domain"
        )
        pd_counts = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute(
            """
            SELECT author_name_raw, match_status, match_confidence, match_notes
            FROM core.author
            WHERE match_status IN ('ambiguous', 'not_found')
            ORDER BY match_status, author_name_raw
            """
        )
        dudosos = cur.fetchall()

        cur.execute(
            """
            SELECT a.author_name_raw, d.author_name_raw
            FROM core.author a
            JOIN core.author d ON d.author_id = a.duplicate_of_author_id
            ORDER BY a.author_name_raw
            """
        )
        duplicates = cur.fetchall()

        cur.execute("SELECT step, rows_ok, rows_error, duration_seconds, started_at FROM core.run_log ORDER BY started_at")
        run_log = cur.fetchall()

    error_files = _count_error_files()

    lines = []
    lines.append("# Informe de calidad — base de datos de autores enriquecida")
    lines.append("")
    lines.append(f"_Generado automáticamente el {dt.datetime.now(dt.timezone.utc).isoformat()}Z a partir de `core.author`._")
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    lines.append(f"- Autores en el seed: **{total}**")
    for status, count in status_counts:
        pct = (count / total * 100) if total else 0
        lines.append(f"  - `{status}`: {count} ({pct:.1f}%)")
    lines.append(f"- Duplicados detectados (mismo QID de Wikidata para dos nombres del seed): **{duplicate_count}**")
    lines.append(f"- Dominio público = sí: {pd_counts.get(True, 0)} | no: {pd_counts.get(False, 0)} | desconocido: {pd_counts.get(None, 0)}")
    lines.append(f"- Filas puestas en cuarentena por error (ver `data/errors/`): **{error_files}**")
    lines.append("")

    lines.append("## Cómo se calcula la confianza de matching")
    lines.append("")
    lines.append("Wikidata es la fuente de desambiguación (ver `ai-usage/`). La búsqueda de Wikidata")
    lines.append("casi siempre devuelve varios resultados aunque el nombre no sea ambiguo (obras,")
    lines.append("ediciones, bibliotecas con el mismo nombre), así que el criterio no es \"cuántos")
    lines.append("resultados hay\" sino si el mejor candidato tiene nombre exacto y su descripción u")
    lines.append("ocupación (P106) confirma que es escritor/a. Por cada autor:")
    lines.append("- `exact` (0.95): nombre exacto y descripción/ocupación confirman escritor/a.")
    lines.append("- `exact` (0.65): nombre exacto, pero sin dato de profesión para confirmarlo.")
    lines.append("- `ambiguous` (0.35): nombre exacto, pero la ocupación en Wikidata no es de escritor/a (posible homónimo).")
    lines.append("- `ambiguous` (0.55): el mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación sí es de escritor/a.")
    lines.append("- `ambiguous` (0.3): sin coincidencia exacta de nombre ni confirmación de profesión.")
    lines.append("- `not_found`: sin candidatos plausibles de persona en Wikidata (incluye `Anonymous` / `Various Authors`, marcados aparte como `special_case`).")
    lines.append("")

    lines.append("## Casos dudosos (revisión manual recomendada)")
    lines.append("")
    if dudosos:
        lines.append("| Autor (seed) | Estado | Confianza | Motivo |")
        lines.append("|---|---|---|---|")
        for name, status, confidence, notes in dudosos:
            lines.append(f"| {name} | {status} | {confidence} | {notes or ''} |")
    else:
        lines.append("Ninguno.")
    lines.append("")

    lines.append("## Duplicados detectados")
    lines.append("")
    if duplicates:
        lines.append("| Nombre en el seed | Duplicado de |")
        lines.append("|---|---|")
        for dupe_name, original_name in duplicates:
            lines.append(f"| {dupe_name} | {original_name} |")
    else:
        lines.append("Ninguno.")
    lines.append("")

    lines.append("## Limitaciones conocidas")
    lines.append("")
    lines.append("- La lista de ocupaciones usada para confirmar \"es escritor/a\" (P106 en Wikidata) es corta y cubre los casos esperables del seed, no es exhaustiva.")
    lines.append("- Open Library se usa solo como señal de catálogo (nº de obras, obra más conocida); no se descargan materias (subjects) por autor para mantener el alcance acotado.")
    lines.append("- El precio/valor de reventa se descartó explícitamente: ninguna API gratuita lo da a nivel de autor (ver `ai-usage/`).")
    lines.append("- \"Dominio público\" se calcula con la regla UE (70 años post-mortem) a partir del año de fallecimiento de Wikidata; no contempla otras jurisdicciones.")
    lines.append("")

    lines.append("## Ejecución del pipeline")
    lines.append("")
    lines.append("| Paso | Filas OK | Filas error | Duración (s) | Inicio |")
    lines.append("|---|---|---|---|---|")
    for step, rows_ok, rows_error, duration, started_at in run_log:
        lines.append(f"| {step} | {rows_ok} | {rows_error} | {duration:.2f} | {started_at} |")
    lines.append("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    logger.info("Informe de calidad generado en %s", output_path)
