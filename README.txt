REEMPLAZO PARA GITHUB PAGES - USPP SATIPO

Reemplaza SOLO tu index.html actual por este archivo.
Mantén tu carpeta data/ exactamente donde está:

produccion-satipo/
  index.html
  logo.png
  data/
    manifest.json
    base_YYYY_MM.json

No uses INICIAR_DASHBOARD.bat para GitHub Pages.

El nuevo index:
- funciona en dominio raíz y en subruta de GitHub Pages;
- valida manifest.json;
- valida HTTP y JSON de cada mes;
- muestra el error real en pantalla en vez de dejar los KPI vacíos;
- usa cache=no-store para evitar que GitHub Pages sirva una versión vieja del JSON.
