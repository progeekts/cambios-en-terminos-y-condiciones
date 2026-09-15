# Observatorio de Términos y Privacidad

Proyecto abierto para registrar cambios en políticas de privacidad y términos de servicio de servicios digitales.

## Qué hace

Un workflow de GitHub Actions ejecuta periódicamente `scripts/tracker.py`. El rastreador descarga los documentos configurados en `scripts/targets.json`, extrae el texto relevante y lo compara con la versión almacenada en `tracked_policies/`.

Cuando detecta una modificación, guarda un registro en `docs/diffs.json` con:

- fecha de detección;
- líneas añadidas y eliminadas;
- categorías potencialmente afectadas;
- clasificación automática de relevancia;
- diff textual para poder comprobar el cambio.

`docs/status.json` contiene el estado de la última comprobación y la web de `docs/` presenta los resultados mediante GitHub Pages.

## Clasificación

La clasificación es automática y orientativa. Busca expresiones relacionadas con datos personales, terceros, transferencias internacionales, IA y entrenamiento, publicidad, conservación de datos, propiedad/licencias de contenido, arbitraje, jurisdicción, suscripciones y derechos del usuario.

Una coincidencia no implica que el cambio sea perjudicial, ilegal o aplicable a todos los usuarios. El documento oficial enlazado desde cada registro es la fuente que debe consultarse para interpretar el cambio.

## Añadir una fuente

Añade una entrada a `scripts/targets.json` con un identificador único, nombre de plataforma, tipo de documento y URL pública. En la primera ejecución se crea una copia de referencia; las ejecuciones posteriores se comparan contra ella.

## Estructura

- `.github/workflows/monitor.yml` — automatización diaria.
- `scripts/tracker.py` — descarga, normalización, comparación y clasificación.
- `scripts/targets.json` — documentos vigilados.
- `tracked_policies/` — última versión textual conocida.
- `docs/diffs.json` — historial de cambios.
- `docs/status.json` — estado de la última comprobación.
- `docs/index.html` — interfaz pública.

## Limitaciones

Las páginas web pueden cambiar de estructura, bloquear solicitudes automatizadas o incluir contenido dinámico. También pueden producirse modificaciones técnicas sin relevancia contractual. El observatorio registra y prioriza señales; no sustituye una revisión jurídica del documento original.
