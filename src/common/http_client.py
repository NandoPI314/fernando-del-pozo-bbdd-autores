"""Cliente HTTP con reintentos y User-Agent identificable, como piden las
políticas de uso de Wikidata/Open Library para tráfico automatizado."""
import time

import requests

USER_AGENT = "fernando-del-pozo-bbdd-autores/1.0 (prueba tecnica; contacto: nando.pozo.ituero@gmail.com)"


def get_json(url: str, params: dict | None = None, timeout: int = 15, retries: int = 3, backoff_seconds: float = 1.5):
    """GET con reintentos exponenciales. Devuelve (status_code, json_or_none).
    Lanza la última excepción si todos los intentos fallan."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return resp.status_code, resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff_seconds * attempt)
    raise last_exc
