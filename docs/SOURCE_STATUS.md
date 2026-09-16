# Estado de las fuentes

`docs/status.json` representa la última ejecución del monitor.

- `targets`: número de documentos configurados.
- `ok`: documentos obtenidos y procesados correctamente en esa ejecución.
- `errors`: fuentes que no pudieron procesarse, junto con un diagnóstico abreviado.
- `changes`: documentos en los que esa ejecución encontró diferencias.
- `last_check`: fecha y hora UTC de la comprobación.

Un error de fuente no debe interpretarse como que el documento haya cambiado o dejado de existir. Puede deberse a conectividad, bloqueos automatizados, cambios técnicos de la página u otras causas. La fase V2.2 ampliará estos diagnósticos.
