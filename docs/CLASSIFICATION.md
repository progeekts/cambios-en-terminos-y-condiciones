# Modelo de clasificación de cambios

El observatorio separa dos conceptos para que el historial sea comprensible y escalable.

## Tipo de documento

Cada fuente se configura con uno de estos tipos:

- Términos y condiciones
- Términos de servicio
- Política de privacidad
- Condiciones de licenciamiento
- Acuerdo de tratamiento de datos
- Seguridad y cumplimiento
- Otro documento legal

El tipo describe **qué documento se está vigilando** y se define en `scripts/targets.json`.

## Materia afectada

Cuando aparece una diferencia, el clasificador analiza el texto añadido y eliminado y puede asignar una o varias materias:

- IA y entrenamiento
- Datos personales
- Terceros y cesión de datos
- Transferencias internacionales
- Conservación y eliminación
- Publicidad y personalización
- Propiedad y licencias
- Arbitraje y disputas
- Jurisdicción y ley aplicable
- Precios, pagos y suscripciones
- Derechos y control del usuario
- Seguridad
- Cumplimiento y auditoría
- Cuenta y acceso al servicio

Estas categorías son señales automáticas, no conclusiones jurídicas.

## Resumen en lenguaje sencillo

Cada nuevo registro incluye un resumen generado de forma determinista a partir de las materias detectadas. Su objetivo es explicar qué áreas parecen haber cambiado sin inventar consecuencias jurídicas. El `diff` exacto y el enlace al documento oficial se conservan para poder verificar el cambio.

## Relevancia

`Alta`, `Media` y `Baja` son niveles automáticos de relevancia para priorizar la revisión. No significan que un cambio sea positivo, negativo, legal o ilegal.

El registro guarda `schema_version` y `classifier_version` para que en el futuro sea posible distinguir cambios producidos por distintas versiones del sistema de clasificación.
