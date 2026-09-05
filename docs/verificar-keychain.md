# Verificar el almacén seguro en un Android real (§15.6)

Comprobar, en ~10 minutos, que los tokens de sesión quedan en el **almacén protegido** del sistema
(Keystore, vía `capacitor-secure-storage-plugin`) y **no** en el almacenamiento común
(`SharedPreferences` en texto). Es el ítem que quedó **parcial** desde el PASO 12.

## Preparación

- Teléfono Android con **depuración USB** activada, conectado por USB.
- APK de **depuración** instalado (`scripts/compilar-android.sh` + `adb install`). `run-as` solo
  funciona con builds debuggables.
- Paquete de la app: **`ar.gob.tarjeta.app`** (de `apps/mobile/capacitor.config.ts`).

Iniciar sesión en la app (un vecino cualquiera) **antes** de mirar los archivos, para que existan
los tokens.

## Pasos

```bash
PKG=ar.gob.tarjeta.app

# 1) Listar los archivos de preferencias de la app.
adb shell run-as "$PKG" ls -l shared_prefs/

# 2) Mirar el almacenamiento COMÚN (Preferences de Capacitor). NO debe tener los tokens en claro.
adb shell run-as "$PKG" cat shared_prefs/CapacitorStorage.xml
```

## Qué tiene que verse (está bien) ✅

- En `CapacitorStorage.xml` (almacenamiento común) **no** aparecen `tarjeta_access` ni
  `tarjeta_refresh` con un valor legible. A lo sumo aparecen datos NO sensibles (perfil activo,
  huella del dispositivo).
- Los tokens viven en el archivo del **secure storage** (otro `.xml` en `shared_prefs/`, típicamente
  con nombre del plugin de secure storage) y **con el valor cifrado** (texto ilegible tipo base64),
  no el JWT original.

## Qué indica que está MAL ❌

- Ver `tarjeta_access` o `tarjeta_refresh` con un **JWT legible** (empieza con `eyJ...`) en
  `CapacitorStorage.xml` o en cualquier archivo en texto plano.
- Que el token aparezca sin cifrar en cualquier lado accesible por `run-as`.

## Registrar el resultado

Anotá el resultado en `docs/apps-build.md` (tabla de verificación en dispositivo). Recién cuando esto
dé ✅ en un teléfono real, el almacén seguro pasa de **parcial** a **implementada** en la matriz
(`docs/estado-funcional.md`). Hasta entonces, queda como **parcial**.
