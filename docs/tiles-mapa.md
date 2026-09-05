> ## 🚫 BLOQUEANTE DE LANZAMIENTO (§08.0.C)
> El archivo de tiles **todavía no se generó**: el código y la configuración están listos, pero
> `NEXT_PUBLIC_TILES_URL` apunta a un archivo que aún no existe, así que **el mapa se ve con un
> aviso de "mapa no disponible"** (ya no un rectángulo en blanco). Antes de salir a producción
> hay que generar y subir los tiles.
>
> **Ahora (§13.0 + §14.1):** en **desarrollo** el front usa por defecto el **servidor público de
> OpenStreetMap** (`https://tile.openstreetmap.org/...`), sin configurar nada. En **producción**
> **falla cerrado**: si no está configurada `NEXT_PUBLIC_TILES_URL` con tiles propios, el mapa
> **no carga** (muestra "mapa no disponible") y **no** cae al server público — así no se filtra la
> IP ni la zona que mira cada vecino a un tercero, ni se viola la política de OSM. La distinción es
> por entorno de compilación (`NODE_ENV`), no por una bandera que se pueda olvidar
> (`apps/web/src/lib/tiles.ts`, con test de las dos ramas).
>
> **La generación es un comando:** `scripts/generar-tiles.sh` (requiere Java 21+). Descarga
> planetiler y el extracto, y produce el PMTiles. Falta **correrlo, subir el archivo al hosting y
> apuntar `NEXT_PUBLIC_TILES_URL`** — y, si se usa PMTiles, agregar el adaptador del front (ver
> "Nota sobre PMTiles"). El detalle manual de abajo queda como referencia.
>
> - **Estado:** PENDIENTE — bloqueante de lanzamiento (generación scriptada; falta ejecutar + hostear).
> - **Responsable:** _(a asignar por el municipio)_.
> - **Fecha objetivo:** _(a definir; debe estar listo antes del lanzamiento público)_.

# Mapa: generación de tiles propios de San Juan (§07.0.A)

Este documento explica, **paso a paso y reproducible por alguien ajeno al proyecto**, cómo se
generan y actualizan los tiles del mapa. El objetivo es no depender del tile server público de
OpenStreetMap (su política de uso lo reserva para desarrollo, no para una app con usuarios
reales) y **no tener ningún servicio corriendo**: los tiles son un archivo estático servido
desde el mismo hosting de la web.

> **Regenerar 1–2 veces al año** para incorporar calles nuevas. Ver "Recordatorio" al final.

---

## Decisión

- **Librería:** Leaflet 1.9.x (BSD-2, sin costo). Ver `docs/VERSIONS.md`.
- **Tiles:** extracto de **San Juan** desde datos de OpenStreetMap, servido como archivo(s)
  estático(s). Recomendado: **un único archivo PMTiles** (vectorial) o, si se prefiere lo más
  simple de servir, una **pirámide de tiles raster** `{z}/{x}/{y}.png`.
- **URL configurable:** `NEXT_PUBLIC_TILES_URL` (no está en el código). Por defecto
  `/tiles/{z}/{x}/{y}.png` (pirámide raster estática bajo `apps/web/public/tiles/`).

---

## Requisitos (una sola vez)

- ~4 GB de disco libre y una conexión razonable.
- Una de estas herramientas de generación:
  - **planetiler** (Java 21+): `planetiler.jar` — genera PMTiles/MBTiles de un extracto `.osm.pbf`.
  - o **tilemaker** (C++): alternativa liviana.
- Para raster desde MBTiles: `mb-util` o `pmtiles` CLI para extraer/convertir.

---

## Procedimiento

### 1. Bajar el extracto de San Juan

Los extractos regionales se publican en **Geofabrik**. Argentina completa está en:

```bash
curl -L -o argentina-latest.osm.pbf \
  https://download.geofabrik.de/south-america/argentina-latest.osm.pbf
```

Recortar a San Juan con un *bounding box* (aprox.) usando `osmium`:

```bash
# bbox San Juan (oeste,sur,este,norte) aproximado
osmium extract -b -69.6,-32.6,-67.2,-30.0 argentina-latest.osm.pbf -o san-juan.osm.pbf
```

> El bounding box de arriba cubre el Gran San Juan y Rivadavia con margen. Ajustar si se
> necesita más cobertura provincial.

### 2. Generar el archivo de tiles

**Opción A — PMTiles vectorial (un solo archivo, recomendado):**

```bash
java -Xmx4g -jar planetiler.jar \
  --osm-path=san-juan.osm.pbf \
  --output=san-juan.pmtiles \
  --force
```

Resultado esperado: `san-juan.pmtiles`, del orden de **decenas a ~200 MB** según cobertura.

**Opción B — Pirámide raster `{z}/{x}/{y}.png` (la más simple de servir):**

Renderizar con un estilo (p. ej. con `tilemaker` + `mbutil`, o un renderer raster) hasta el
zoom 17 para la zona urbana. Exportar a un directorio `tiles/{z}/{x}/{y}.png`.

### 3. Subir como archivo estático

- **Opción A (PMTiles):** subir `san-juan.pmtiles` al hosting estático y apuntar
  `NEXT_PUBLIC_TILES_URL` a él (requiere el plugin de PMTiles en el front; ver nota abajo).
- **Opción B (raster):** copiar el árbol a `apps/web/public/tiles/` **o** a un bucket estático,
  y apuntar `NEXT_PUBLIC_TILES_URL=/tiles/{z}/{x}/{y}.png` (o la URL del bucket).

La caché del navegador ya está configurada como `immutable` para `/tiles/*` en
`apps/web/next.config.ts`: los tiles no cambian entre visitas y no se vuelven a descargar.

### 4. Verificar que quedó bien

1. `NEXT_PUBLIC_TILES_URL` apunta al lugar correcto (variable de entorno, no código).
2. Abrir cualquier pantalla con mapa (p. ej. adhesión de comercio) y confirmar que el mapa de
   San Juan se ve **sin pedir nada a `tile.openstreetmap.org`** (revisar la pestaña Network:
   no debe haber requests a ese dominio).
3. Zoom hasta nivel de calle en el centro de Rivadavia: las calles aparecen.
4. Peso total razonable (PMTiles: un archivo; raster: verificar que el árbol subió completo).

---

## Nota sobre PMTiles en el front

Si se elige la opción PMTiles (vectorial), hace falta un adaptador de Leaflet para PMTiles
(p. ej. `protomaps-leaflet`) y un estilo básico. El componente `MapaPicker` ya toma la URL de
`NEXT_PUBLIC_TILES_URL`; el cambio es de front (agregar el adaptador) y no toca el backend.
La opción raster no requiere nada extra: funciona con el `L.tileLayer` actual.

---

## Recordatorio

**Periodicidad sugerida: cada 6 meses** (2 veces al año). Está anotado como tarea recurrente en
`docs/VERSIONS.md` (sección PASO 07). Si esto no se hace, el mapa deja de incorporar calles
nuevas y nadie sabrá por qué: este documento es la razón por la que sí se va a poder.
