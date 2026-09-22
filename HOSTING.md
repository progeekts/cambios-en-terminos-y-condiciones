# Paquete listo para hosting

Este repositorio genera automáticamente un paquete estático independiente de GitHub Pages.

## Migración

1. Abre la ejecución más reciente de **Monitor Políticas Legales** en GitHub Actions.
2. Descarga el artefacto **web-progeekts-es**.
3. Descomprime el ZIP.
4. Sube **el contenido de la carpeta** al directorio público de tu hosting para `progeekts.es`.

No necesitas instalar Python, Node, una base de datos ni ejecutar scripts en el hosting.

GitHub Actions sigue realizando la monitorización y genera un paquete nuevo con los datos actualizados en cada ejecución.

## Importante

El paquete está preparado para publicarse en la raíz de `https://progeekts.es/`.

La web usa rutas relativas para sus HTML, JSON, RSS, Atom y recursos. El generador sustituye en la copia exportable los enlaces permanentes heredados de GitHub Pages, pero no modifica la web que actualmente está funcionando en GitHub Pages.

El ZIP descargable contiene únicamente los archivos necesarios para servir la web; la documentación técnica Markdown queda fuera.
