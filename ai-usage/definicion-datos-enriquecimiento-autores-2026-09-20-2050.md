# Definición de qué datos enriquecer y de dónde obtenerlos

**Fecha:** 2026-09-20
**Proyecto/directorio:** fernando-del-pozo-bbdd-autores

## Contexto y objetivo

El proyecto es la prueba técnica "Senior Data Engineer — Base de datos de autores": a partir de un fichero semilla (`authors_seed.csv`, 500 nombres de autores literarios de procedencias y épocas muy diversas), hay que decidir qué información adicional obtener por API, cómo normalizarla y almacenarla, y dejar un proceso reproducible. El enunciado pide explícitamente acotar el problema, justificar decisiones y entregar un informe de calidad/casos dudosos, valorando más una solución trazable y defendible que una exhaustiva.

Para guiar qué campos merece la pena enriquecer (en vez de intentar traer "todo lo que haya"), se abordó la pregunta desde un marco de negocio: si el objetivo fuera decidir qué autores priorizar en la compra/venta de libros de segunda mano al por mayor, ¿qué información sería útil y de dónde se sacaría fácilmente vía API? Ese marco sirvió para priorizar el diseño del esquema de la prueba real.

## Decisiones tomadas

- **Priorizar primero campos de desambiguación de identidad (nacimiento/muerte, nacionalidad, ID canónico) sobre cualquier otro enriquecimiento** — con 500 nombres hay alto riesgo de homónimos, pseudónimos (p. ej. "Azorín") y entradas no reales (filas "Anonymous"/"Various Authors"); sin una identidad fiable, cualquier dato adicional que se cuelgue de ese autor es poco defendible.
- **Tratar el "dominio público" como un campo derivado (año de muerte + regla jurisdiccional, p. ej. 70 años post-mortem UE) y no como un dato a pedir directamente a ninguna API** — ninguna fuente lo da como campo explícito fiable de forma universal, y calcularlo es más trazable que confiar en un tercero.
- **Descartar el precio/valor de reventa real como campo a incluir en el enriquecimiento de autor** — ninguna API gratuita lo ofrece a nivel de autor; el dato de precio vive a nivel de edición/ISBN concreto y depende de fuentes de mercado (eBay, AbeBooks/Iberlibro, Wallapop) con más fricción legal y de acceso, fuera del alcance razonable de esta prueba.
- **Elegir Wikidata como fuente principal de desambiguación e IDs canónicos, con Open Library como refuerzo de catálogo/materias, y Wikimedia Pageviews como proxy de popularidad** — las tres son gratuitas y sin necesidad de API key (salvo Google Books, que se dejó como refuerzo opcional de menor prioridad por su cuota limitada).
- **Guardar snapshots con fecha (no solo el valor final) para métricas cambiantes como popularidad o nº de obras** — permite justificar el informe de calidad pedido en el enunciado sin tener que volver a llamar a las APIs para reconstruir el razonamiento sobre casos dudosos.
- **Guardar la carpeta de registro de uso de IA en `ai-usage/` dentro del propio repo del proyecto, en vez de en una carpeta genérica `Context/`** — el enunciado de la prueba ya exige explícitamente esa carpeta con ese propósito, así que se usó la convención ya establecida por el propio proyecto en lugar de la convención por defecto de la skill.

## Prompts y peticiones relevantes

- El usuario planteó la pregunta en términos de negocio: puesto en el papel de experto en reventa de libros de segunda mano al por mayor, qué información sacable fácilmente vía API sería útil para la toma de decisiones, de dónde se obtendría, y cómo se ingestaría en su BBDD — partiendo de la lista de autores real del repo `fernando-del-pozo-bbdd-autores`.
- A partir de la respuesta (priorización de campos, APIs candidatas y esquema simple de tablas), el usuario pidió guardar el contexto de la conversación con la skill `/guardar-contexto`.
