# Tiles del mapa

Este directorio aloja los tiles del mapa servidos como archivo estático (§07.0.A).

- **No se commitean** los tiles ni los artefactos de build (ver `.gitignore` de la raíz): son
  grandes y se regeneran/suben al hosting. Sólo se versionan este README y el `.gitkeep`.
- **Generación (un comando):** `scripts/generar-tiles.sh` (requiere Java 21+; ver el script).
- **Procedimiento completo y decisiones:** `docs/tiles-mapa.md`.
- **Config del front:** `NEXT_PUBLIC_TILES_URL` (por defecto `/tiles/{z}/{x}/{y}.png`, pirámide
  raster). Si se usa PMTiles (vectorial), hace falta el adaptador `protomaps-leaflet` en el front.

Mientras no haya tiles, el mapa muestra un aviso claro ("mapa no disponible") en vez de un
rectángulo en blanco (`apps/web/src/components/MapaPicker.tsx`).
