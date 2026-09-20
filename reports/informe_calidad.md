# Informe de calidad — base de datos de autores enriquecida

_Generado automáticamente el 2026-09-20T20:31:30.905574+00:00Z a partir de `core.author`._

## Resumen

- Autores en el seed: **500**
  - `ambiguous`: 9 (1.8%)
  - `exact`: 489 (97.8%)
  - `special_case`: 2 (0.4%)
- Duplicados detectados (mismo QID de Wikidata para dos nombres del seed): **7**
- Dominio público = sí: 173 | no: 185 | desconocido: 142
- Filas puestas en cuarentena por error (ver `data/errors/`): **0**

## Cómo se calcula la confianza de matching

Wikidata es la fuente de desambiguación (ver `ai-usage/`). La búsqueda de Wikidata
casi siempre devuelve varios resultados aunque el nombre no sea ambiguo (obras,
ediciones, bibliotecas con el mismo nombre), así que el criterio no es "cuántos
resultados hay" sino si el mejor candidato tiene nombre exacto y su descripción u
ocupación (P106) confirma que es escritor/a. Por cada autor:
- `exact` (0.95): nombre exacto y descripción/ocupación confirman escritor/a.
- `exact` (0.65): nombre exacto, pero sin dato de profesión para confirmarlo.
- `ambiguous` (0.35): nombre exacto, pero la ocupación en Wikidata no es de escritor/a (posible homónimo).
- `ambiguous` (0.55): el mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación sí es de escritor/a.
- `ambiguous` (0.3): sin coincidencia exacta de nombre ni confirmación de profesión.
- `not_found`: sin candidatos plausibles de persona en Wikidata (incluye `Anonymous` / `Various Authors`, marcados aparte como `special_case`).

## Casos dudosos (revisión manual recomendada)

| Autor (seed) | Estado | Confianza | Motivo |
|---|---|---|---|
| Anne Frank | ambiguous | 0.35 | nombre exacto pero la ocupación en Wikidata no es de escritor/a (posible homónimo) |
| Eduardo Mendoza | ambiguous | 0.35 | nombre exacto pero la ocupación en Wikidata no es de escritor/a (posible homónimo) |
| Kobo Abe | ambiguous | 0.55 | mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación es de escritor/a |
| Mariana Enríquez | ambiguous | 0.55 | mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación es de escritor/a |
| Mary Beard | ambiguous | 0.35 | nombre exacto pero la ocupación en Wikidata no es de escritor/a (posible homónimo) |
| Natsume Soseki | ambiguous | 0.55 | mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación es de escritor/a |
| Ryunosuke Akutagawa | ambiguous | 0.55 | mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación es de escritor/a |
| Thich Nhat Hanh | ambiguous | 0.55 | mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación es de escritor/a |
| Érico Veríssimo | ambiguous | 0.55 | mejor candidato no es coincidencia exacta de nombre, pero su descripción/ocupación es de escritor/a |

## Duplicados detectados

| Nombre en el seed | Duplicado de |
|---|---|
| Charles Lutwidge Dodgson | Lewis Carroll |
| Isak Dinesen | Karen Blixen |
| Mary Ann Evans | George Eliot |
| Robert Galbraith | J. K. Rowling |
| Samuel Clemens | Mark Twain |
| Theodor Seuss Geisel | Dr. Seuss |
| Émile Ajar | Romain Gary |

## Limitaciones conocidas

- La lista de ocupaciones usada para confirmar "es escritor/a" (P106 en Wikidata) es corta y cubre los casos esperables del seed, no es exhaustiva.
- Open Library se usa solo como señal de catálogo (nº de obras, obra más conocida); no se descargan materias (subjects) por autor para mantener el alcance acotado.
- El precio/valor de reventa se descartó explícitamente: ninguna API gratuita lo da a nivel de autor (ver `ai-usage/`).
- "Dominio público" se calcula con la regla UE (70 años post-mortem) a partir del año de fallecimiento de Wikidata; no contempla otras jurisdicciones.

## Ejecución del pipeline

| Paso | Filas OK | Filas error | Duración (s) | Inicio |
|---|---|---|---|---|
| ingest_seed | 500 | 0 | 0.16 | 2026-09-20 20:05:01.621658+00:00 |
| wikidata_enrichment | 498 | 0 | 923.06 | 2026-09-20 20:05:01.783534+00:00 |
| open_library_enrichment | 498 | 0 | 608.29 | 2026-09-20 20:20:24.888913+00:00 |
| dedupe | 7 | 0 | 0.01 | 2026-09-20 20:30:33.182011+00:00 |
