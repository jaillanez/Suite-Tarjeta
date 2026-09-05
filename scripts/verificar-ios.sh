#!/usr/bin/env bash
# Verifica si esta Mac puede compilar iOS para Capacitor 8.5 (§15.5), que exige Xcode 27.
# Informa Xcode, command-line tools y espacio, y termina con un veredicto claro.
set -uo pipefail

XCODE_MIN=27

info() { printf '\033[1;34m[ios]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
bad()  { printf '\033[1;31m✗\033[0m %s\n' "$*"; }

falta=0

# --- Sistema operativo -------------------------------------------------------
if [ "$(uname)" != "Darwin" ]; then
  bad "iOS solo se compila en macOS. Este sistema es $(uname)."
  echo
  printf '\033[1;31mVEREDICTO: NO se puede compilar iOS (se necesita una Mac).\033[0m\n'
  exit 1
fi
info "macOS $(sw_vers -productVersion 2>/dev/null || echo '?')"

# --- Xcode -------------------------------------------------------------------
xcode_major=0
if command -v xcodebuild >/dev/null 2>&1 && xcodebuild -version >/dev/null 2>&1; then
  ver="$(xcodebuild -version | head -1 | awk '{print $2}')"
  xcode_major="${ver%%.*}"
  if [ "${xcode_major:-0}" -ge "$XCODE_MIN" ]; then
    ok "Xcode $ver (>= $XCODE_MIN)."
  else
    bad "Xcode $ver: Capacitor 8.5 necesita Xcode $XCODE_MIN o superior."
    falta=1
  fi
else
  bad "Xcode no está instalado (o 'xcode-select' apunta solo a las Command Line Tools)."
  falta=1
fi

# --- Command Line Tools ------------------------------------------------------
if xcode-select -p >/dev/null 2>&1; then
  ok "Herramientas de línea de comandos: $(xcode-select -p)"
else
  bad "Faltan las Command Line Tools. Instalá con:  xcode-select --install"
  falta=1
fi

# --- Espacio libre -----------------------------------------------------------
libre="$(df -g / 2>/dev/null | awk 'NR==2{print $4}')"
[ -n "${libre:-}" ] && info "Espacio libre en /: ${libre} GB (Xcode ocupa ~40 GB instalado)."

# --- Veredicto ---------------------------------------------------------------
echo
if [ "$falta" -eq 0 ]; then
  printf '\033[1;32mVEREDICTO: SE PUEDE COMPILAR iOS.\033[0m\n'
  echo "Seguí docs/apps-build.md (cap add ios; cap sync ios; abrir en Xcode)."
  exit 0
fi
printf '\033[1;31mVEREDICTO: FALTA para compilar iOS:\033[0m\n'
echo "  - Instalar/actualizar a Xcode $XCODE_MIN+ desde la Mac App Store o developer.apple.com/download"
echo "    (descarga ~12-15 GB; ocupa ~40 GB instalado; necesitás al menos ~50 GB libres)."
echo "  - Xcode $XCODE_MIN puede requerir una versión de macOS más nueva que la actual"
echo "    ($(sw_vers -productVersion 2>/dev/null)); la ficha de la App Store indica el mínimo."
echo "  - Después: sudo xcodebuild -license accept  y  xcode-select --install (si faltan las CLT)."
exit 1
