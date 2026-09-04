#!/usr/bin/env bash
# Genera los tiles del mapa (§07.0.A / §12.6-B) de forma reproducible, en UN comando.
# Implementa el procedimiento de docs/tiles-mapa.md (opción A: PMTiles vectorial con planetiler).
#
# Uso:
#   scripts/generar-tiles.sh            # descarga deps, extracto y genera el PMTiles
#   BBOX=... OSM_URL=... scripts/generar-tiles.sh   # ajustar cobertura/fuente
#
# Requisitos: Java 21+ (planetiler), curl. `osmium` es opcional (recorta el extracto al bbox;
# si no está, se usa Argentina completa y planetiler igual lo procesa, sólo tarda más).
#
# Los artefactos de build (jar, .osm.pbf) y el .pmtiles resultante NO se commitean: el tile es
# un archivo que se sube al hosting estático. Ver "Subir como archivo estático" en el doc.
set -euo pipefail

# --- configuración (override por variables de entorno) -----------------------
PLANETILER_VERSION="${PLANETILER_VERSION:-0.9.0}"
# bbox San Juan (oeste,sur,este,norte) — cubre Gran San Juan y Rivadavia con margen.
BBOX="${BBOX:--69.6,-32.6,-67.2,-30.0}"
OSM_URL="${OSM_URL:-https://download.geofabrik.de/south-america/argentina-latest.osm.pbf}"
XMX="${XMX:-4g}"

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$RAIZ/scripts/.tiles-build}"
SALIDA="${SALIDA:-$RAIZ/apps/web/public/tiles/san-juan.pmtiles}"

JAR="$BUILD_DIR/planetiler-$PLANETILER_VERSION.jar"
ARG_PBF="$BUILD_DIR/argentina-latest.osm.pbf"
SJ_PBF="$BUILD_DIR/san-juan.osm.pbf"

info() { printf '\033[1;34m[tiles]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[tiles] ERROR:\033[0m %s\n' "$*" >&2; }

# --- comprobación de dependencias --------------------------------------------
require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { error "falta '$1' en el PATH. $2"; exit 1; }
}

check_java() {
  if ! command -v java >/dev/null 2>&1; then
    error "falta Java 21+ (planetiler lo necesita). Instalá un JDK 21 y reintentá."
    exit 1
  fi
  # "openjdk version \"21.0.1\"" / "\"17.0.14\"" -> major
  local ver major
  ver="$(java -version 2>&1 | head -1 | sed -E 's/.*version "([0-9]+).*/\1/')"
  major="${ver:-0}"
  if [ "$major" -lt 21 ]; then
    error "Java $major detectado; planetiler necesita 21+. Actualizá el JDK (p. ej. Temurin 21)."
    exit 1
  fi
  info "Java $major OK."
}

# --- pasos -------------------------------------------------------------------
check_java
require_cmd curl "Instalalo con tu gestor de paquetes."
mkdir -p "$BUILD_DIR" "$(dirname "$SALIDA")"

if [ ! -f "$JAR" ]; then
  info "Descargando planetiler $PLANETILER_VERSION…"
  curl -L --fail -o "$JAR" \
    "https://github.com/onthegomap/planetiler/releases/download/v$PLANETILER_VERSION/planetiler.jar"
fi

if [ ! -f "$ARG_PBF" ]; then
  info "Descargando extracto de Argentina (Geofabrik)… (puede tardar)"
  curl -L --fail -o "$ARG_PBF" "$OSM_URL"
fi

ENTRADA="$ARG_PBF"
if command -v osmium >/dev/null 2>&1; then
  info "Recortando a San Juan (bbox $BBOX) con osmium…"
  osmium extract -b "$BBOX" "$ARG_PBF" -o "$SJ_PBF" --overwrite
  ENTRADA="$SJ_PBF"
else
  info "osmium no está: se procesa Argentina completa (más lento, resultado más grande)."
  info "Para acotar a San Juan, instalá osmium-tool y reintentá."
fi

info "Generando PMTiles con planetiler…"
java "-Xmx$XMX" -jar "$JAR" --osm-path="$ENTRADA" --output="$SALIDA" --force

info "Listo: $SALIDA ($(du -h "$SALIDA" | cut -f1))"
cat <<'SIGUIENTE'

Siguientes pasos (ver docs/tiles-mapa.md):
  1. Subir el .pmtiles al hosting estático (o dejarlo en apps/web/public/tiles/).
  2. Apuntar NEXT_PUBLIC_TILES_URL al archivo.
  3. PMTiles es vectorial: el front necesita el adaptador (protomaps-leaflet). Si preferís no
     tocar el front ahora, generá una pirámide raster {z}/{x}/{y}.png (opción B del doc), que
     funciona con el L.tileLayer actual sin cambios.
SIGUIENTE
