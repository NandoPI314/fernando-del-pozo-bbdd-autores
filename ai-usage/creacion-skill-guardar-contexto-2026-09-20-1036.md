# Creación de la skill "guardar-contexto"

**Fecha:** 2026-09-20
**Proyecto/directorio:** C:\Users\--\--\--\--\Proyectos (carpeta general de proyectos, no un repositorio concreto)

## Contexto y objetivo

El usuario quería una skill de uso frecuente para guardar el contexto de sus conversaciones con Claude en un archivo .md, con doble finalidad: (1) que sirva de contexto recuperable para Claude en futuras sesiones sobre el mismo proyecto, especialmente al acercarse a los límites de contexto de la conversación, y (2) que sirva de resumen para que un tercero entienda las decisiones principales tomadas sin tener que leer la conversación completa.

## Decisiones tomadas

- **Nivel de detalle: resumen ejecutivo, sin citas textuales largas** — se descartó la opción de incluir prompts citados literalmente porque el objetivo prioritario es la legibilidad para un tercero y la compacidad para recuperar contexto, no preservar el "cómo se dijo".
- **Secciones del documento: contexto/objetivo, decisiones tomadas, prompts/peticiones relevantes** — se descartaron explícitamente las secciones de "archivos modificados" y "pendientes/próximos pasos" porque el usuario las consideró innecesarias para el propósito de esta skill.
- **Cada decisión debe llevar su justificación ("por qué")** — sin el razonamiento detrás, una decisión registrada es solo un hecho que no permite juzgar más adelante si sigue siendo válida.
- **Ubicación y nombre del archivo: proponer un valor por defecto y pedir confirmación, en vez de preguntar en blanco** — reduce fricción en el uso frecuente de la skill sin perder el control del usuario sobre dónde se guarda cada resumen.
- **Carpeta por defecto fijada como `Context/` en la raíz del proyecto actual** — el usuario, al probar la skill por primera vez, prefirió esta convención simple y fija frente a la heurística inicial (buscar carpetas existentes tipo `docs`/`notes`/`memory`), y pidió que quedara como comportamiento por defecto para futuras ejecuciones.
- **El nombre final del archivo siempre termina en un timestamp** (`YYYY-MM-DD-HHmm`) — evita que ejecuciones sucesivas de la skill sobre el mismo proyecto se sobrescriban entre sí, preservando el histórico de resúmenes.
- **El contenido lo redacta Claude en el momento, sintetizando la conversación real** — se descartó deliberadamente que la skill fuera un script que parsea logs, porque el valor está en el criterio editorial de qué merece quedar documentado.
- **Ubicación de la skill: `~/.claude/skills/guardar-contexto/` (fuera de la carpeta `synced/`)** — se comprobó que `synced/` está reservada al bundle de skills gestionado por Anthropic (docx, pdf, pptx, skill-creator, etc.), por lo que la nueva skill personal se instaló como carpeta hermana para que no quede sujeta a esa sincronización.
- **Se omitió el proceso completo de evals/benchmarks del skill-creator** — al tratarse de una skill de salida subjetiva (una síntesis narrativa), se optó por iterar directamente con el usuario probando la skill en vivo, en línea con la propia guía del skill-creator para este tipo de casos.

## Prompts y peticiones relevantes

- El usuario pidió crear una skill de uso frecuente para guardar el contexto de las conversaciones en un .md, con la doble finalidad de recuperación de contexto y resumen para terceros, dejando abierto que Claude preguntara nombre y ubicación del archivo según el proyecto, y pidiendo que el nombre siempre incluyera un timestamp al final.
- Ante la pregunta sobre nivel de detalle, secciones a incluir y comportamiento de nombre/ubicación, el usuario optó por: resumen ejecutivo, las tres secciones ya mencionadas (sin archivos modificados ni pendientes), y sugerir-y-confirmar en vez de preguntar en blanco.
- El usuario pidió construir la skill vía el flujo de skill-creator.
- Al ejecutar la skill por primera vez como prueba sobre esta misma conversación, el usuario corrigió la ubicación propuesta inicialmente y fijó como comportamiento por defecto crear una carpeta `Context/` dentro del directorio de trabajo del proyecto.
