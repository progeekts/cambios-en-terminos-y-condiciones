# Arquitectura del observatorio

`targets.json` → descarga de fuentes → limpieza de HTML → comparación con snapshot anterior → clasificación temática → relevancia → resumen sencillo → `diffs.json` → interfaz web.

`status.json` registra el estado de la última ejecución para que la web pueda mostrar cuándo se realizó la comprobación y cuántas fuentes se procesaron correctamente.

Los snapshots de `tracked_policies/` son la referencia utilizada para comparar la siguiente versión descargada de cada documento.

La V2.1 mantiene la clasificación basada en reglas deliberadamente separada de la interfaz. Esto permite mejorar el clasificador o incorporar otros métodos en el futuro sin cambiar el formato básico de consulta del historial.
