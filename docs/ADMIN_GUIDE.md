# Guía rápida para añadir documentos

Cada documento monitorizado se define como un objeto en `scripts/targets.json`.

Campos principales:

- `id`: identificador único y estable.
- `platform`: empresa o servicio.
- `document_type`: familia documental normalizada.
- `url`: dirección pública oficial del documento.

Tipos admitidos en V2.1:

- Términos y condiciones
- Términos de servicio
- Política de privacidad
- Condiciones de licenciamiento
- Acuerdo de tratamiento de datos
- Seguridad y cumplimiento
- Otro documento legal

Para futuras fuentes pueden añadirse metadatos como `region`, `language`, `enabled` o `notes`; el esquema está en `scripts/target.schema.json`.

Antes de incorporar una empresa nueva conviene comprobar que la URL es oficial, pública, estable y que devuelve el contenido del documento sin exigir autenticación. Las fuentes dinámicas o protegidas contra automatización requieren validación adicional antes de activarlas.
