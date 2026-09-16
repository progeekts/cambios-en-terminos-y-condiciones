# Interfaz V2.1

La portada prioriza una lectura no técnica: empresa, fecha, tipo de documento, relevancia, explicación sencilla y materias detectadas. El diff queda plegado hasta que la persona decide consultarlo.

Los filtros combinables permiten reducir el historial por empresa, tipo de documento, materia y relevancia. El buscador incluye esos mismos campos y el resumen.

La interfaz mantiene compatibilidad con registros históricos anteriores a V2.1 mediante fallback de `document_type` a `type`, de `categories` a `impacts` y de `relevance` a `severity`.
