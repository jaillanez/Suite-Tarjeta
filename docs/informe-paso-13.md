# PASO 13 — Informe de cierre (cerrar apps y cargar datos reales)

Deja el sistema listo para probarlo entero en local: padrón por YAML, textos legales cargados,
comercios y promociones poblando el sistema, modo demostración, y el mapa andando. Lo que depende
de hardware que este entorno no tiene (build nativo, dispositivo real, Mac con Xcode 27) queda como
**procedimiento reproducible documentado**.

**Estado:** completado en todo lo que es código y datos. Los ítems de dispositivo/binarios quedan
pendientes de ejecutarse en la máquina del responsable (ver "Lo que informa el paso").

## PRs

| PR | Bloque |
|---|---|
| #37 | 13.1 padrón simulado por YAML (sin paridad, recarga en caliente) |
| #38 | 13.2 textos legales v1 (borradores para revisión legal) |
| #39 | 13.3 carga idempotente de comercios de precarga |
| #40 | 13.0 mapa con tiles públicos de OSM (por ahora) |
| #41 | 13.5 modo demostración + 13.4 doc de build de apps |

## Criterios de aceptación

- [x] Padrón simulado lee de YAML, con recarga en caliente y **sin paridad de DNI** (incl. tests).
- [x] Adaptador real intacto; pasar a modo real es solo configuración.
- [x] La guarda de producción sigue bloqueando el arranque con padrón simulado.
- [x] Tres textos legales cargados, versionados, con la nota de revisión legal **visible**.
- [x] 36 comercios (14 rubros) cargados con promociones activas.
- [x] Carga idempotente por comando, con **origen** del dato y **bandera de precarga**.
- [x] Los precargados se pueden dar de baja en bloque (`baja_precarga`).
- [ ] **APK de depuración y AAB de publicación generados** — requiere Android SDK + firma (no en este entorno). Procedimiento en `docs/apps-build.md`.
- [ ] **Recorrido completo probado en un teléfono Android real** — requiere dispositivo (no en este entorno).
- [ ] **Confirmado en dispositivo que los tokens están en el almacén seguro del SO** — requiere dispositivo (plugin cableado en PASO 12 #33).
- [ ] **iOS compilado** — requiere Mac con Xcode 27 (no en este entorno); documentado por qué no.
- [x] Modo demostración cargable con un comando (idempotente).
- [x] Documentos de estado actualizados (matriz + esta lista + gate `docs_al_dia`).
- [x] Pipeline en verde.

## Lo que informa el paso

- **Comercios cargados y de dónde:** **36** comercios de precarga en **14 rubros**
  (`datos/comercios_rivadavia.yaml`) + 1 comercio de demo. **Son datos sintéticos** (nombres y
  teléfonos inventados; no son negocios reales) con **geografía real de Rivadavia** (zonas y
  coordenadas) para poblar el mapa — decisión tomada por integridad, para no afirmar promociones
  falsas sobre negocios reales identificables. Cada uno guarda su `origen`; se reemplazan por un
  relevamiento real con el mismo comando idempotente.
- **Prueba en dispositivo real:** **no realizada** en este entorno (no hay `cap`/`gradle`/`adb` ni
  teléfono). El procedimiento reproducible y la checklist para registrar resultados están en
  `docs/apps-build.md`.
- **¿Almacén seguro verificado?** **No en dispositivo.** El plugin nativo quedó cableado en el
  PASO 12 (#33) detrás del seam; falta correrlo en un teléfono (`cap sync` + build nativo) y
  confirmar que access/refresh van a Keychain/Keystore. Es el ítem que quedó **parcial**.
- **Estado de iOS:** **no compilado.** Capacitor 8.5 exige Xcode 27 y no hay Mac con esa versión
  disponible en este entorno; el paso permite documentarlo y seguir con Android. Pasos en
  `docs/apps-build.md`.

## Decisiones aplicadas (§13.0)

Tiles = OSM público por ahora; alojamiento local; clave de cifrado la custodia el responsable;
padrón real cableado con datos desde YAML mientras no haya endpoint; comercios reales (aquí
sintéticos por integridad, ver arriba); binarios los produce el responsable.

## Nota de seguridad (revisión automática del commit de tiles)

La revisión de seguridad marcó el cambio de tiles como *fail-open/privacy*: el default pasó de
tiles propios (fail-closed → "mapa no disponible") a **OSM público** (carga siempre, pero manda IP y
zona vista del usuario a un tercero y su política no permite producción). Es el comportamiento
**autorizado por §13.0 para pruebas/local**, `NEXT_PUBLIC_TILES_URL` lo overridea, y **pasar a
tiles propios antes de abrir al público ya es un bloqueante en la lista de lanzamiento** (1.7). No
hay guarda que impida usarlo en prod por descuido: si querés, agrego una que en producción falle
cerrado (mapa no disponible) salvo que se configure la URL propia.

## Pendientes que requieren hardware o decisión humana

1. **Build y prueba en dispositivo (Android):** APK/AAB firmados + recorrido completo + verificación
   del almacén seguro. `docs/apps-build.md`.
2. **iOS:** compilar en una Mac con Xcode 27.
3. **Revisión legal:** los tres textos son borradores; los fija Asesoría Letrada (nueva versión ⇒
   nueva migración v2).
4. **Relevamiento real de comercios:** reemplazar el dataset sintético por comercios reales con el
   mismo comando.
5. **Tiles propios para producción** (§1.7) y demás ítems de `docs/lista-para-lanzar.md`.
