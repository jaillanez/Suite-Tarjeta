# Compilar la app Android (§15.4)

En la máquina del responsable (macOS con el Android SDK en `~/Library/Android/sdk`).

## Requisitos (instalar lo que falte)

```bash
# JDK 21 (Temurin) — NO el JBR de JetBrains
brew install --cask temurin@21

# Android SDK: la forma simple es instalar Android Studio (trae el SDK en ~/Library/Android/sdk).
brew install --cask android-studio
# Abrir Android Studio una vez para que baje el SDK, o usar las command-line tools.

# Variables de entorno (agregar a ~/.zshrc)
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"

# Aceptar licencias del SDK (una vez)
yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses
```

Los scripts **verifican estos requisitos** y, si falta algo, dicen exactamente qué instalar.

## APK de depuración (un comando)

```bash
scripts/compilar-android.sh
```

Hace: verifica requisitos → `pnpm build` (móvil) → `cap add android` (la primera vez) →
`cap sync android` → `gradlew assembleDebug`. Deja el APK en **`build/tarjeta-debug.apk`** y muestra
la ruta.

## Pasar el APK al teléfono

```bash
# Con el teléfono conectado por USB y la depuración USB activada:
adb install -r build/tarjeta-debug.apk
# o copiarlo y abrirlo desde el teléfono (permitir "instalar apps de orígenes desconocidos").
```

Probar el recorrido completo: registro → tarjeta → mapa → caja → canje.

## AAB firmado de publicación

```bash
scripts/compilar-android-aab.sh
```

- Genera el **keystore** (`config/tarjeta-release.jks`) la primera vez y guarda su contraseña en
  `config/produccion.env` (`ANDROID_KEYSTORE_PASSWORD`).
- **⚠ RESGUARDÁ `config/tarjeta-release.jks` Y SU CONTRASEÑA.** Si se pierde, **no se puede volver a
  publicar la app nunca más**. No se commitea (`.gitignore`); hacé una copia segura fuera del equipo.
- Deja el AAB en **`build/tarjeta-release.aab`** para subir a Google Play.

## Íconos, splash, permisos y versión

- Íconos/splash: `pnpm dlx @capacitor/assets generate --android` a partir de `assets/icon.png`
  (1024×1024) y `assets/splash.png`.
- Nombre visible: `appName` en `apps/mobile/capacitor.config.ts`.
- Versión: `versionName` / `versionCode` en `apps/mobile/android/app/build.gradle`.
- Permisos (cámara, ubicación, red): declarados en `android/app/src/main/AndroidManifest.xml`
  (ver `docs/apps-build.md`).
