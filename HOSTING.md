# Paquete listo para hosting

La web genera automáticamente un paquete estático independiente de GitHub Pages.

## Migración

1. Abre la ejecución más reciente de **Monitor Políticas Legales** en GitHub Actions.
2. Descarga el artefacto **web-progeekts-es**.
3. Descomprime el ZIP.
4. Sube su contenido al directorio público de tu hosting para `progeekts.es`.

No necesitas instalar Python, Node ni una base de datos en el hosting. GitHub Actions sigue realizando la monitorización y genera un paquete nuevo con los datos actualizados.

El paquete está preparado para la raíz de `https://progeekts.es/`. La exportación cambia los enlaces heredados de GitHub Pages solo dentro de la copia descargable; la web actual de GitHub Pages no se modifica.
