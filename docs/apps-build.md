# Cerrar las apps en Capacitor (§13.4)

Objetivo: binarios instalables (Android APK/AAB, iOS) y verificación en dispositivo real.

> **Qué NO se pudo hacer en este entorno y por qué.** El repo no tiene `cap`/`gradle`/`adb` en el
> PATH ni un dispositivo, y el build nativo necesita el SDK de Android (con firma) y, para iOS, una
> Mac con Xcode 27. Por eso acá quedan **la configuración y el procedimiento reproducible**; los
> binarios y la prueba en dispositivo los produce el responsable siguiendo estos pasos. Los ítems de
> verificación en dispositivo (almacén seguro, cámara, offline, mapa, QR) están en la checklist del
> final para registrar sus resultados.

## Requisitos

- Node 22 + pnpm (ya en el repo). `pnpm --filter @tarjeta/mobile build` genera `apps/mobile/out`.
- **Android:** JDK **Temurin 21** (no el JBR de JetBrains), Android SDK + Platform Tools, un teléfono
  con depuración USB.
- **iOS:** macOS con **Xcode 27** (Capacitor 8.5 lo exige por la adopción de UIScene; usa Swift
  Package Manager, no CocoaPods).

## Android

```bash
cd apps/mobile
pnpm build                      # export estático -> out/
pnpm exec cap add android       # crea apps/mobile/android (una sola vez)
pnpm exec cap sync android      # copia web + plugins (incl. secure-storage)
```

- **Ícono, splash, nombre y versión:** poné los assets con `@capacitor/assets`
  (`pnpm dlx @capacitor/assets generate --android`) a partir de un `assets/icon.png` (1024×1024) y
  `assets/splash.png`. Nombre visible = `appName` de `capacitor.config.ts`. Versión: `versionName`
  / `versionCode` en `android/app/build.gradle`.
- **Permisos** (declarar en `android/app/src/main/AndroidManifest.xml`):
  ```xml
  <uses-permission android:name="android.permission.CAMERA" />
  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
  <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
  <uses-permission android:name="android.permission.INTERNET" />
  ```
- **APK de depuración:**
  ```bash
  cd android && ./gradlew assembleDebug
  # -> android/app/build/outputs/apk/debug/app-debug.apk
  ```
- **AAB firmado de publicación:** crear un keystore (`keytool -genkey -v -keystore tarjeta.jks ...`),
  configurar `signingConfigs` en `android/app/build.gradle`, y:
  ```bash
  ./gradlew bundleRelease
  # -> android/app/build/outputs/bundle/release/app-release.aab
  ```
- **Instalar y probar el recorrido completo** en un teléfono real: `adb install -r app-debug.apk`,
  luego registro → tarjeta → mapa → caja → canje.

## iOS

```bash
cd apps/mobile
pnpm build
pnpm exec cap add ios
pnpm exec cap sync ios
pnpm exec cap open ios          # abre Xcode 27
```

- Ícono y splash con `@capacitor/assets generate --ios`.
- **Textos de permisos en `ios/App/App/Info.plist`** (Apple rechaza si faltan):
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>Se usa la cámara para escanear el QR de canje.</string>
  <key>NSLocationWhenInUseUsageDescription</key>
  <string>Se usa la ubicación para mostrar beneficios cercanos.</string>
  ```
- Compilar en Xcode 27. **Si no hay Mac con Xcode 27 disponible, queda documentado acá y se sigue
  con Android** (como permite el paso).

## Verificación en dispositivo real (registrar resultados)

| Ítem | Cómo | Resultado |
|---|---|---|
| Tokens en el **almacén seguro** del SO (Keychain/Keystore) | tras login, inspeccionar que access/refresh NO estén en almacenamiento común (ver `almacen-seguro.ts` + `AlmacenSeguroInit`) | _(pendiente en dispositivo)_ |
| La cámara escanea el QR | caja → escanear QR del ciudadano | _(pendiente)_ |
| Modo sin conexión encola y sincroniza | poner en avión, operar, volver la señal | _(pendiente)_ |
| El mapa carga | pantalla con mapa | _(pendiente)_ |
| El QR rotativo se lee sin problemas de reloj | escanear con el QR ya rotado | _(pendiente)_ |

> Completá esta tabla al probar en dispositivo. Es el cierre del ítem que quedó **parcial** en el
> PASO 12 (almacén seguro cableado pero sin verificar en hardware).
