# Diseño e implementación del pipeline de enriquecimiento de autores

**Fecha:** 2026-09-21
**Proyecto/directorio:** fernando-del-pozo-bbdd-autores

## Contexto y objetivo

Continuación de la prueba técnica "Senior Data Engineer — Base de datos de autores"
(ver `Prueba Técnica Data.pdf` y el enriquecimiento previo documentado en
`ai-usage/definicion-datos-enriquecimiento-autores-2026-09-20-2050.md`). En esta
sesión se pasó de la propuesta de arquitectura a la implementación completa,
ejecución real contra APIs públicas (Wikidata, Open Library) y una revisión de
código guiada por el usuario para poder defenderlo con conocimiento propio.

El usuario planteó una arquitectura inicial (Docker + Postgres + Python, tricapa
staging/enrichment/datawarehouse, framework de manifiestos genérico para futuras
tablas, surrogate keys, sistema de logs/alertas, cuarentena de filas erróneas) y
pidió primero asesoramiento y después ayuda para construirla.

## Decisiones tomadas

- **Simplificar la tricapa a dos capas físicas (`raw` y `core`) en el mismo
  Postgres** — el enunciado recomienda 2-3 horas y valora explícitamente una
  solución acotada y defendible sobre una grande y difícil de verificar; con una
  sola entidad (autor) y tres fuentes conocidas, una capa intermedia física de
  transformación no aportaba más que complejidad. `raw` guarda el JSON crudo de
  cada llamada a API con timestamp (permite reprocesar sin re-consumir cuota de
  las APIs); `core.author` es la tabla final enriquecida.
- **Descartar el framework de manifiestos genérico para "futuras tablas"** —
  decisión tomada explícitamente por el usuario tras planteársela como disyuntiva:
  con solo 3 fuentes conocidas, construir un motor de mapeo/casting configurable
  resolvía un problema hipotético no pedido por el enunciado. Se optó por un
  script Python explícito por fuente (`src/sources/<fuente>.py`) siguiendo siempre
  el mismo patrón (fetch → guarda raw → parsea → actualiza `core.author`); escalar
  a una fuente nueva es copiar el patrón, no configurar un motor.
- **Descartar el sistema de alertas** en favor de una tabla `core.run_log`
  (filas OK/error, duración por paso) más logging a consola y fichero — para un
  entregable de una sola ejecución, sin nadie monitorizando en producción,
  alerting activo era coste sin beneficio real.
- **Mantener**: Docker + Docker Compose (reproducibilidad real, se comprobó que
  la propia máquina de desarrollo no tenía ni Docker arrancado ni Python
  instalado), PostgreSQL, la capa `raw` de JSON crudo, y la cuarentena de filas
  fallidas en `data/errors/<fuente>/` con log de error — estas sí atacan
  directamente los objetivos de reproducibilidad y control de calidad sin coste
  añadido significativo.
- **Wikidata como fuente de identidad/desambiguación antes que cualquier otro
  enriquecimiento**, reafirmando la decisión de la sesión anterior: con 500
  nombres hay riesgo real de homónimos y pseudónimos, y sin un ID canónico
  fiable ningún otro dato colgado de ese autor es defendible. Se añadió un
  esquema explícito de confianza de matching (`match_status`, `match_confidence`,
  `match_notes`) para poder generar el informe de "casos dudosos" que pide el
  enunciado directamente desde datos, no a mano.
- **Corrección de un fallo real de calidad descubierto al ejecutar el pipeline
  completo por primera vez**: la heurística inicial marcaba como `ambiguous`
  cualquier autor cuya búsqueda en Wikidata devolviera más de un candidato — y
  resultó que `wbsearchentities` casi siempre devuelve varios resultados (obras,
  ediciones, bibliotecas homónimas) aunque el autor no sea ambiguo en absoluto,
  lo que producía un 63% de autores muy conocidos marcados como dudosos. Se
  diagnosticó inspeccionando la respuesta real de la API y se corrigió la
  heurística para usar el campo `description` (gratuito, ya incluido en la
  búsqueda) más la ocupación (P106) en vez de contar candidatos. Tras relanzar
  desde cero: 97.8% `exact`, 1.8% `ambiguous`, 0% `not_found`, 0 errores sobre
  los 500 autores, y 7 duplicados por pseudónimo detectados correctamente
  (Mark Twain/Samuel Clemens, Dr. Seuss, George Eliot, Lewis Carroll, etc.).
- **"Dominio público" sigue siendo un campo derivado** (año de fallecimiento +
  regla UE de 70 años post-mortem), no un dato pedido a ninguna API, coherente
  con la decisión ya tomada en la sesión anterior.
- **Open Library limitado a señal de catálogo** (nº de obras, obra más
  conocida), sin descargar materias/subjects por autor, para mantener el
  alcance acotado dado el tiempo disponible.
- **`ingest_seed` se deja como "insert-if-new" (`ON CONFLICT DO NOTHING`), no
  upsert** — se documentó como mejora pendiente en el README en vez de
  resolverse en esta pasada: cambiar esto exige antes decidir una política de
  re-enriquecimiento/refresco que no formaba parte del alcance de esta prueba.
- **Se conserva `.env.example`** tras valorar borrarlo: no contiene secretos
  reales (`.env`, con los valores reales, está en `.gitignore` y nunca se sube),
  y documentar las variables configurables (p. ej. el puerto de Postgres) sirve
  al objetivo de reproducibilidad en distintos entornos.
- Durante la revisión de código guiada por el usuario se corrigieron dos
  defectos de estilo/documentación que habían quedado desincronizados del código
  real: uso de `__import__("json")` en vez de un `import json` normal (en
  `wikidata.py` y `open_library.py`), una variable muerta (`status_map`) en
  `generate_report.py`, y dos bloques de comentarios/informe que seguían
  describiendo la heurística de matching antigua después de haberla sustituido.

## Prompts y peticiones relevantes

- Petición inicial: actuar como experto en ingeniería de datos, primero asesorar
  sobre la propuesta de arquitectura y después ayudar a construirla, con foco en
  reproducibilidad, escalabilidad, control de calidad y utilidad de negocio.
- Tras la revisión, el usuario decidió explícitamente simplificar el framework
  de manifiestos en vez de mantenerlo genérico.
- El usuario indicó que Docker ya se estaba iniciando en su máquina y pidió
  instalar Python, que faltaba — se instaló Python 3.12 vía `winget`.
- Construcción completa del pipeline y primera ejecución real contra Wikidata y
  Open Library sobre los 500 autores; detección y corrección en caliente del
  problema de la heurística de ambigüedad antes de dar el resultado por bueno.
- El usuario pidió una explicación completa y paso a paso de todo el código
  (Docker, esquema SQL, cada módulo Python) para poder defenderlo, lo que llevó
  a encontrar y corregir los defectos de estilo/documentación ya mencionados.
- Preguntas puntuales de operativa resueltas durante la revisión: cómo conectar
  con DBeaver a la base de datos ya en marcha, y si `.env.example` quedaría
  visible en el repositorio de Git al subirlo (sí, pero sin datos sensibles,
  a diferencia de `.env`).
- El usuario pidió guardar primero, en un commit separado, solo el informe de
  calidad generado por el pipeline, antes de comprometer el resto del código.
- Petición final de esta sesión: hacer el commit definitivo con el resto del
  proyecto y subirlo al repositorio remoto de Git.
