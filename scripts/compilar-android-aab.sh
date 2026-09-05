#!/usr/bin/env bash
# Compila el AAB FIRMADO de publicación (§15.4). Genera el keystore si no existe y guarda su
# contraseña en config/produccion.env. Pensado para macOS con el Android SDK.
set -euo pipefail
umask 077  # los archivos que cree este script (config, keystore) quedan solo para el usuario

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOVIL="$RAIZ/apps/mobile"
CONFIG="$RAIZ/config/produccion.env"
KEYSTORE="$RAIZ/config/tarjeta-release.jks"
ALIAS="tarjeta"
SALIDA_DIR="$RAIZ/build"
SALIDA="$SALIDA_DIR/tarjeta-release.aab"

info() { printf '\033[1;34m[aab]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[aab] ERROR:\033[0m %s\n' "$*" >&2; }
aviso() { printf '\033[1;33m%s\033[0m\n' "$*"; }

command -v java >/dev/null 2>&1 || { error "Falta JDK 21+ (brew install --cask temurin@21)."; exit 1; }
command -v keytool >/dev/null 2>&1 || { error "Falta keytool (viene con el JDK)."; exit 1; }
command -v pnpm >/dev/null 2>&1 || { error "Falta pnpm."; exit 1; }
export ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}"
[ -d "$ANDROID_HOME" ] || { error "No se encontró el Android SDK en $ANDROID_HOME (ver docs/compilar-apk.md)."; exit 1; }

# --- contraseña del keystore: leerla o generarla y guardarla en la config -----
mkdir -p "$RAIZ/config"
STORE_PASS="$(grep -E '^ANDROID_KEYSTORE_PASSWORD=' "$CONFIG" 2>/dev/null | tail -1 | cut -d= -f2-)"
case "${STORE_PASS:-}" in ""|*CAMBIAR*) STORE_PASS="";; esac
if [ -z "${STORE_PASS:-}" ]; then
  STORE_PASS="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32)"
  touch "$CONFIG"
  grep -v -E '^ANDROID_KEYSTORE_PASSWORD=' "$CONFIG" > "$CONFIG.tmp" 2>/dev/null || true
  mv "$CONFIG.tmp" "$CONFIG" 2>/dev/null || true
  printf 'ANDROID_KEYSTORE_PASSWORD=%s\n' "$STORE_PASS" >> "$CONFIG"
  chmod 600 "$CONFIG"
  info "Se generó la contraseña del keystore y se guardó en $CONFIG (permisos 600)"
fi
# La contraseña se pasa por variable de entorno (no por línea de comandos, que es visible en `ps`).
export KEYSTORE_PW="$STORE_PASS"

# --- keystore: generarlo si no existe ----------------------------------------
if [ ! -f "$KEYSTORE" ]; then
  info "Generando el keystore de publicación…"
  # -storepass:env / -keypass:env leen la contraseña de la variable de entorno, no del `ps`.
  keytool -genkeypair -v -keystore "$KEYSTORE" -alias "$ALIAS" \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass:env KEYSTORE_PW -keypass:env KEYSTORE_PW \
    -dname "CN=Tarjeta de Beneficios, O=Municipio de Rivadavia, L=Rivadavia, ST=San Juan, C=AR"
  chmod 600 "$KEYSTORE"
  echo
  aviso "###############################################################################"
  aviso "# ATENCIÓN: RESGUARDÁ config/tarjeta-release.jks Y SU CONTRASEÑA.              #"
  aviso "# SI SE PIERDE ESTE ARCHIVO, NO SE PUEDE VOLVER A PUBLICAR LA APP NUNCA MÁS.  #"
  aviso "# NO SE COMMITEA (está en .gitignore). Hacé una copia segura fuera del equipo.#"
  aviso "###############################################################################"
  echo
fi

# --- build + firma -----------------------------------------------------------
info "Build de la app móvil…"; pnpm --filter @tarjeta/mobile build
cd "$MOVIL"
[ -d android ] || pnpm exec cap add android
pnpm exec cap sync android
info "Compilando AAB firmado (bundleRelease)…"
cd "$MOVIL/android"
# Las credenciales de firma van en un gradle.properties temporal (permisos 600) que Gradle lee
# solo, NO en la línea de comandos (que sería visible en `ps`). Se restaura al salir.
GP="gradle.properties"
GP_BACKUP=""
[ -f "$GP" ] && { GP_BACKUP="$(mktemp)"; cp "$GP" "$GP_BACKUP"; }
_restaurar_gp() { if [ -n "$GP_BACKUP" ]; then mv -f "$GP_BACKUP" "$GP"; else rm -f "$GP"; fi; }
trap _restaurar_gp EXIT
{
  echo "android.injected.signing.store.file=$KEYSTORE"
  echo "android.injected.signing.store.password=$STORE_PASS"
  echo "android.injected.signing.key.alias=$ALIAS"
  echo "android.injected.signing.key.password=$STORE_PASS"
} >> "$GP"
chmod 600 "$GP"
./gradlew bundleRelease

mkdir -p "$SALIDA_DIR"
cp "$MOVIL/android/app/build/outputs/bundle/release/app-release.aab" "$SALIDA"
info "AAB firmado listo: $SALIDA"
aviso "Recordá: el keystore ($KEYSTORE) es irreemplazable. Resguardalo."
