# Tiles del mapa (archivo estático)

Acá van los tiles del mapa de San Juan, servidos como **archivo estático** desde el propio
hosting (no dependemos del tile server público de OpenStreetMap).

- El frontend los pide en `NEXT_PUBLIC_TILES_URL` (por defecto `/tiles/{z}/{x}/{y}.png`).
- **No hay ningún servicio corriendo**: son archivos.
- El procedimiento **reproducible** de generación (de dónde se baja el extracto, con qué
  herramienta se genera, cuánto pesa, cómo se sube y cómo se verifica) está en
  [`docs/tiles-mapa.md`](../../../../docs/tiles-mapa.md).

Este archivo es un marcador para que el directorio exista en git. Los tiles reales no se
commitean (pesan cientos de MB): se generan y suben aparte, según el procedimiento.
