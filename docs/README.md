# Datos públicos del observatorio

La web estática consume los siguientes archivos:

- `diffs.json`: historial de modificaciones detectadas.
- `status.json`: estado de la última comprobación automática.
- `catalog.json`: catálogo de tipos de documento, materias y niveles de relevancia que entiende la interfaz.

Los registros nuevos pueden incluir `schema_version` y `classifier_version`. Los registros históricos anteriores se mantienen compatibles mediante los campos heredados `type`, `severity` e `impacts`.
