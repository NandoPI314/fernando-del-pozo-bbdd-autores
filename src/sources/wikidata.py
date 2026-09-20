"""Enriquecimiento de identidad/desambiguación vía Wikidata.

Es la fuente principal (así se decidió en ai-usage/definicion-datos-...):
con 500 nombres hay riesgo real de homónimos y pseudónimos, así que antes de
guardar cualquier otro dato hace falta un ID canónico y una confianza de
matching explícita.

Estrategia (deliberadamente simple, no un motor de reglas):
  1. wbsearchentities por nombre (en -> fallback es) para obtener candidatos.
     wbsearchentities casi siempre devuelve varios resultados aunque el
     nombre no sea ambiguo (obras, ediciones, bibliotecas homónimas), así que
     el número de candidatos NO se usa como señal de ambigüedad.
  2. Se descartan los candidatos que "no parecen persona" por su descripción
     (p.ej. "written work by...", "public library..."). Si no queda ninguno,
     not_found.
  3. Entre los candidatos que sí parecen persona, se elige el que tenga
     nombre exacto y/o descripción de escritor/a (ver `score()` en `_match_one`).
  4. wbgetentities del candidato elegido: fecha nacimiento/muerte (P569/P570),
     nacionalidad (P27, resuelta a label) y ocupación (P106) para confirmar
     que "huele" a escritor. El status final (`exact`/`ambiguous`) combina
     "¿nombre exacto?" + "¿descripción u ocupación confirman escritor/a?".
"""
import datetime as dt
import json
import time

from common import http_client
from common.error_quarantine import quarantine
from common.logging_setup import get_logger

logger = get_logger("wikidata")

SEARCH_URL = "https://www.wikidata.org/w/api.php"
CURRENT_YEAR = dt.date.today().year
EU_POST_MORTEM_YEARS = 70
REQUEST_DELAY_SECONDS = 0.3

# QIDs de ocupaciones que razonablemente confirman "es un/a escritor/a".
# Lista corta y explícita a propósito: cubre los casos esperables del seed,
# no pretende ser exhaustiva (se documenta como límite conocido).
WRITER_OCCUPATIONS = {
    "Q36180",    # writer
    "Q482980",   # author
    "Q6625963",  # novelist
    "Q49757",    # poet
    "Q214917",   # playwright
    "Q1930187",  # journalist
    "Q28389",    # screenwriter
    "Q11774202", # essayist
}

# wbsearchentities con limit>1 casi siempre devuelve varios resultados aunque
# el nombre no sea ambiguo: obras, ediciones, bibliotecas o calles con el
# mismo nombre que el autor. El campo "description" que ya viene en la propia
# búsqueda (sin llamada extra) permite filtrarlos sin necesidad de resolver
# cada candidato. Listas cortas y explícitas, documentadas como límite conocido.
WRITER_DESCRIPTION_KEYWORDS = (
    "writer", "novelist", "poet", "playwright", "journalist", "author", "essayist",
    "escritor", "escritora", "poeta", "poetisa", "novelista", "dramaturgo", "dramaturga",
    "periodista", "ensayista", "cuentista",
)
NON_PERSON_DESCRIPTION_KEYWORDS = (
    "written work", "edition of", "translation of", "public library", "novel by",
    "book by", "song by", "film by", "album by", "painting by", "sculpture",
    "asteroid", "crater", "genus", "species of", "railway station", "metro station",
    "street in", "square in", "library",
)


def _looks_like_person(candidate: dict) -> bool:
    description = (candidate.get("description") or "").lower()
    return not any(kw in description for kw in NON_PERSON_DESCRIPTION_KEYWORDS)


def _description_confirms_writer(candidate: dict) -> bool:
    description = (candidate.get("description") or "").lower()
    return any(kw in description for kw in WRITER_DESCRIPTION_KEYWORDS)


def _is_exact_name_match(candidate: dict, name: str) -> bool:
    label = (candidate.get("label") or "").strip().lower()
    match_text = (candidate.get("match", {}).get("text") or "").strip().lower()
    target = name.strip().lower()
    return label == target or match_text == target

_label_cache: dict[str, str] = {}


def _search_candidates(conn, name: str, language: str) -> list[dict]:
    status, data = http_client.get_json(
        SEARCH_URL,
        params={
            "action": "wbsearchentities",
            "search": name,
            "language": language,
            "format": "json",
            "type": "item",
            "limit": 5,
        },
    )
    _store_raw(conn, name, "wbsearchentities", status, data)
    return data.get("search", [])


def _get_entity(conn, name: str, qid: str) -> dict:
    status, data = http_client.get_json(
        SEARCH_URL,
        params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims|labels",
            "languages": "en|es",
            "format": "json",
        },
    )
    _store_raw(conn, name, "wbgetentities", status, data)
    return data.get("entities", {}).get(qid, {})


def _resolve_label(conn, name: str, qid: str) -> str | None:
    if qid in _label_cache:
        return _label_cache[qid]
    entity = _get_entity(conn, name, qid)
    labels = entity.get("labels", {})
    label = (labels.get("es") or labels.get("en") or {}).get("value")
    _label_cache[qid] = label
    return label


def _store_raw(conn, author_name_raw: str, endpoint: str, status: int, data: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw.api_response (source, endpoint, author_name_raw, http_status, response_json)
            VALUES ('wikidata', %s, %s, %s, %s)
            """,
            (endpoint, author_name_raw, status, json.dumps(data)),
        )
    conn.commit()


def _extract_year(claims: dict, prop: str) -> int | None:
    values = claims.get(prop)
    if not values:
        return None
    try:
        time_str = values[0]["mainsnak"]["datavalue"]["value"]["time"]  # e.g. '+1927-03-06T00:00:00Z'
        return int(time_str[1:5])
    except (KeyError, IndexError, ValueError, TypeError):
        return None


def _extract_qids(claims: dict, prop: str) -> list[str]:
    values = claims.get(prop, [])
    qids = []
    for v in values:
        try:
            qids.append(v["mainsnak"]["datavalue"]["value"]["id"])
        except (KeyError, TypeError):
            continue
    return qids


def _match_one(conn, name: str) -> dict:
    candidates = _search_candidates(conn, name, "en")
    if not candidates:
        candidates = _search_candidates(conn, name, "es")

    plausible = [c for c in candidates if _looks_like_person(c)]

    if not candidates:
        return {"match_status": "not_found", "match_confidence": 0.0, "match_notes": "sin candidatos en Wikidata"}
    if not plausible:
        return {
            "match_status": "not_found",
            "match_confidence": 0.0,
            "match_notes": "solo se encontraron resultados que no parecen personas (obras, lugares...)",
        }

    # Entre los candidatos plausibles, se prioriza: nombre exacto + descripción
    # de escritor/a > nombre exacto sin descripción de escritor/a > el resto.
    def score(c: dict) -> tuple:
        return (_is_exact_name_match(c, name), _description_confirms_writer(c))

    plausible.sort(key=score, reverse=True)
    chosen = plausible[0]
    qid = chosen["id"]
    exact_name = _is_exact_name_match(chosen, name)
    writer_desc = _description_confirms_writer(chosen)

    entity = _get_entity(conn, name, qid)
    claims = entity.get("claims", {})

    birth_year = _extract_year(claims, "P569")
    death_year = _extract_year(claims, "P570")
    occupations = _extract_qids(claims, "P106")
    occupation_confirms_writer = any(q in WRITER_OCCUPATIONS for q in occupations)

    nationality = None
    citizenships = _extract_qids(claims, "P27")
    if citizenships:
        nationality = _resolve_label(conn, name, citizenships[0])
        time.sleep(REQUEST_DELAY_SECONDS)

    writer_confirmed = writer_desc or occupation_confirms_writer

    if exact_name and writer_confirmed:
        status, confidence, notes = "exact", 0.95, "nombre exacto y descripción/ocupación confirman escritor/a"
    elif exact_name and occupations and not occupation_confirms_writer:
        status, confidence, notes = "ambiguous", 0.35, "nombre exacto pero la ocupación en Wikidata no es de escritor/a (posible homónimo)"
    elif exact_name:
        status, confidence, notes = "exact", 0.65, "nombre exacto, sin dato de profesión para confirmarlo"
    elif writer_confirmed:
        status, confidence, notes = "ambiguous", 0.55, "mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación es de escritor/a"
    else:
        status, confidence, notes = "ambiguous", 0.3, "sin coincidencia exacta de nombre ni confirmación de profesión"

    is_public_domain = None
    public_domain_basis = "sin año de fallecimiento conocido"
    if death_year is not None:
        is_public_domain = (CURRENT_YEAR - death_year) > EU_POST_MORTEM_YEARS
        public_domain_basis = (
            f"death_year={death_year}, regla UE {EU_POST_MORTEM_YEARS} años post-mortem, año actual={CURRENT_YEAR}"
        )

    return {
        "author_name_normalized": entity.get("labels", {}).get("es", entity.get("labels", {}).get("en", {})).get("value"),
        "wikidata_qid": qid,
        "birth_year": birth_year,
        "death_year": death_year,
        "nationality": nationality,
        "is_public_domain": is_public_domain,
        "public_domain_basis": public_domain_basis,
        "match_status": status,
        "match_confidence": confidence,
        "match_notes": notes,
    }


def run(conn) -> tuple[int, int, dt.datetime, dt.datetime]:
    started_at = dt.datetime.now(dt.timezone.utc)
    rows_ok = 0
    rows_error = 0

    with conn.cursor() as cur:
        cur.execute("SELECT author_name_raw FROM core.author WHERE match_status = 'pending' ORDER BY author_id")
        pending = [row[0] for row in cur.fetchall()]

    logger.info("wikidata: %s autores pendientes de enriquecer", len(pending))

    for name in pending:
        try:
            result = _match_one(conn, name)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE core.author
                    SET author_name_normalized = %(author_name_normalized)s,
                        wikidata_qid = %(wikidata_qid)s,
                        birth_year = %(birth_year)s,
                        death_year = %(death_year)s,
                        nationality = %(nationality)s,
                        is_public_domain = %(is_public_domain)s,
                        public_domain_basis = %(public_domain_basis)s,
                        match_status = %(match_status)s,
                        match_confidence = %(match_confidence)s,
                        match_notes = %(match_notes)s,
                        updated_at = now()
                    WHERE author_name_raw = %(author_name_raw)s
                    """,
                    {**result, "author_name_raw": name},
                )
            conn.commit()
            rows_ok += 1
        except Exception as exc:  # noqa: BLE001 - queremos capturar cualquier fallo por fila y seguir
            conn.rollback()
            quarantine("wikidata", name, exc)
            logger.error("wikidata: fallo enriqueciendo '%s': %s", name, exc)
            rows_error += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    finished_at = dt.datetime.now(dt.timezone.utc)
    logger.info("wikidata: %s ok, %s errores", rows_ok, rows_error)
    return rows_ok, rows_error, started_at, finished_at
