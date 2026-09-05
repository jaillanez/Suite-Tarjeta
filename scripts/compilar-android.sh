#!/usr/bin/env bash
# Compila el APK de depuración de la app móvil en UN comando (§15.4).
# Pensado para macOS con el Android SDK en ~/Library/Android/sdk.
#
# Hace: verifica requisitos -> pnpm build (móvil) -> cap sync android -> assembleDebug ->
# deja el APK en una ruta fija y la muestra.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOVIL="$RAIZ/apps/mobile"
SALIDA_DIR="$RAIZ/build"
SALIDA="$SALIDA_DIR/tarjeta-debug.apk"

info() { printf '\033[1;34m[android]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[android] ERROR:\033[0m %s\n' "$*" >&2; }

# --- requisitos --------------------------------------------------------------
faltan=0

check_java() {
  if ! command -v java >/dev/null 2>&1; then
    error "Falta Java (JDK 21+). Instalalo:  brew install --cask temurin@21"
    faltan=1; return
  fi
  local major
  major="$(java -version 2>&1 | head -1 | sed -E 's/.*version "([0-9]+).*/\1/')"
  if [ "${major:-0}" -lt 21 ]; then
    error "Java ${major} detectado; se necesita 21+. Instalá Temurin 21:  brew install --cask temurin@21"
    faltan=1
  else
    info "Java ${major} OK."
  fi
}

check_sdk() {
  # Respeta ANDROID_HOME/ANDROID_SDK_ROOT; si no, prueba la ruta estándar de macOS.
  local sdk="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}"
  if [ ! -d "$sdk" ]; then
    error "No se encontró el Android SDK en '$sdk'. Instalá Android Studio o las command-line tools"
    error "y exportá ANDROID_HOME. Ver docs/compilar-apk.md."
    faltan=1; return
  fi
  export ANDROID_HOME="$sdk"
  export ANDROID_SDK_ROOT="$sdk"
  export PATH="$sdk/platform-tools:$PATH"
  info "Android SDK: $sdk"
}

command -v pnpm >/dev/null 2>&1 || { error "Falta pnpm."; faltan=1; }
check_java
check_sdk
[ "$faltan" -eq 0 ] || { error "Faltan requisitos (ver arriba). No se compila."; exit 1; }

# --- build -------------------------------------------------------------------
info "Build de la app móvil (export estático)…"
pnpm --filter @tarjeta/mobile build

cd "$MOVIL"
if [ ! -d android ]; then
  info "Creando el proyecto Android (cap add android)…"
  pnpm exec cap add android
fi
info "Sincronizando web + plugins (cap sync android)…"
pnpm exec cap sync android

info "Compilando APK de depuración (gradlew assembleDebug)…"
cd "$MOVIL/android"
./gradlew assembleDebug

mkdir -p "$SALIDA_DIR"
cp "$MOVIL/android/app/build/outputs/apk/debug/app-debug.apk" "$SALIDA"
info "APK listo: $SALIDA"
info "Instalar en un teléfono conectado:  adb install -r \"$SALIDA\""
