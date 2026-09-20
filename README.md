# fernando-del-pozo-bbdd-autores

Base de datos de autores enriquecida a partir de `authors_seed.csv` (500 nombres),
usando Wikidata (identidad/desambiguación) y Open Library (catálogo) como fuentes
públicas y gratuitas. Prueba técnica "Senior Data Engineer" — ver
[`Prueba Técnica Data.pdf`](./Prueba%20Técnica%20Data.pdf).

## Cómo ejecutarlo

Requisitos: Docker + Docker Compose. Nada más — no hace falta Python ni Postgres
instalados en el host.

```bash
cp .env.example .env      # credenciales de desarrollo, no son secretas
docker compose up -d db   # arranca Postgres
docker compose run --rm pipeline   # ejecuta el pipeline completo (10-15 min: llama a APIs reales)
```

El pipeline es idempotente por pasos ya ingestados vía `author_name_raw` (clave
natural `UNIQUE`), pero **el enriquecimiento por autor no se repite una vez que
sale de `pending`** (evita volver a llamar a las APIs en cada rerun). Para
reprocesar todo desde cero:

```bash
docker exec authors_db psql -U authors -d authors_db -c \
  "TRUNCATE core.author, core.run_log, raw.api_response RESTART IDENTITY;"
docker compose run --rm pipeline
```

Para consultar la base de datos resultante:

```bash
docker exec -it authors_db psql -U authors -d authors_db
```

El informe de calidad se regenera en cada ejecución en
[`reports/informe_calidad.md`](./reports/informe_calidad.md).

## Arquitectura

Dos capas en el mismo Postgres (no una tricapa completa: con una sola entidad
"autor" y tres fuentes conocidas, una capa intermedia física de transformación
no aportaba más que complejidad):

- **`raw`**: JSON crudo de cada llamada a Wikidata/Open Library, con timestamp.
  Permite reprocesar sin volver a golpear las APIs y da trazabilidad completa
  para el informe de calidad.
- **`core`**: `core.author` (una fila por autor del seed, `author_id` como
  surrogate key entera, `author_name_raw` como clave natural) y `core.run_log`
  (métricas de cada paso: filas OK, filas en error, duración).

Orquestación en Python (`src/run_pipeline.py`), transformaciones en SQL
ejecutado desde Python. Cada fuente vive en `src/sources/<fuente>.py` con el
mismo patrón (fetch → guarda raw → parsea → actualiza `core.author`); añadir
una fuente nueva es copiar ese patrón, no configurar un motor genérico.

Si una fila falla (red, JSON inesperado...) se captura, se guarda en
`data/errors/<fuente>/` con el error y el pipeline continúa con el resto.

## Decisiones técnicas (resumen)

- **Wikidata como fuente de identidad, no la primera fuente "de contenido"**:
  con 500 nombres hay riesgo real de homónimos y pseudónimos (p. ej. "Azorín").
  Sin un ID canónico fiable, cualquier otro dato enganchado a ese autor no es
  defendible.
- **Confianza de matching explícita** (`match_status`, `match_confidence`,
  `match_notes` en `core.author`): la búsqueda de Wikidata devuelve casi
  siempre varios resultados aunque el nombre no sea ambiguo (ediciones, obras,
  calles con el mismo nombre), así que el criterio no es "cuántos resultados
  hay" sino si el mejor candidato tiene coincidencia exacta de nombre y su
  descripción/ocupación confirma que es escritor/a. Ver el detalle y los casos
  dudosos en `reports/informe_calidad.md`.
- **"Dominio público" como campo derivado** (año de fallecimiento + regla UE
  de 70 años post-mortem), no como dato pedido directamente a ninguna API.
- **Open Library solo como señal de catálogo** (nº de obras, obra más
  conocida), no para desambiguar identidad.
- **Se descartó el precio/valor de reventa** como campo de enriquecimiento:
  ninguna API gratuita lo da a nivel de autor (vive a nivel de edición/ISBN).
- Más contexto y el razonamiento completo en [`ai-usage/`](./ai-usage/).

## Mejoras pendientes (conocidas, no bloqueantes)

- **`ingest_seed` es "insert-if-new", no "upsert"**: usa `ON CONFLICT (author_name_raw) DO NOTHING`.
  Si el CSV de origen cambiara (se corrige un nombre, se añade una fila), un autor
  que ya existe en `core.author` no se actualiza solo — hay que borrar esa fila
  o truncar y relanzar todo. Es una decisión consciente para no re-enriquecer
  (y volver a golpear las APIs) en cada rerun, pero significa que hoy no hay
  forma de refrescar datos de un autor concreto sin intervención manual.
- En la misma línea, campos que cambian con el tiempo (`ol_work_count`,
  popularidad) no se re-consultan una vez enriquecidos: no hay un mecanismo de
  caducidad/TTL para volver a pedirlos periódicamente.

## Estructura del repositorio

```
docker-compose.yml / Dockerfile   infraestructura reproducible
sql/                              esquema de raw y core
src/                              pipeline Python (orquestación + fuentes)
data/errors/                      filas que fallaron, para inspección
reports/informe_calidad.md        informe de calidad, generado automáticamente
ai-usage/                         registro de uso de IA y decisiones
```
