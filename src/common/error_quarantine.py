"""Si una fila no se puede ingestar/enriquecer, se guarda aquí en vez de
parar el proceso, para poder inspeccionarla o reprocesarla después."""
import json
import os
import re
import time


def quarantine(source: str, author_name_raw: str, error: Exception, payload: dict | None = None) -> str:
    error_dir = os.path.join("data", "errors", source)
    os.makedirs(error_dir, exist_ok=True)

    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", author_name_raw)[:60]
    filename = f"{int(time.time() * 1000)}_{safe_name}.json"
    path = os.path.join(error_dir, filename)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "author_name_raw": author_name_raw,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "payload": payload,
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )
    return path
