# Estado funcional de la plataforma

Qué es **real** y qué está **fingido**, sin ambigüedad. Se actualiza en cada paso.
*Última actualización: cierre del PASO 12 (PRs #17–#31).*

Clasificación: **Implementada** (funciona de punta a punta con integración real) · **Parcial**
(funciona pero le falta una pieza) · **Simulada** (adaptador de simulación detrás de un puerto;
no llama a un servicio real) · **Pendiente** (no construida).

> Regla de negocio (§12.1): **el registro ciudadano es abierto** y el padrón solo asigna el nivel;
> **el comercio se valida** (solo inscripto y aprobado publica u opera).

---

## Módulos

| Módulo | Estado | Detalle / de qué depende para completarse |
|---|---|---|
| identidad | **Parcial** | Registro abierto, login, MFA (TOTP), dispositivos, perfiles: reales. Sesión web: refresh en **cookie HttpOnly** + access en memoria (§12 P1-A). **Verificación de identidad: autodeclarada** (no hay RENAPER; fuera de alcance, §12.2-C). Recuperación de cuenta por email: **flujo completo** (token de un solo uso, cierra sesiones); el **envío real espera proveedor** (`EMAIL_PROVEEDOR`, en dev por consola). |
| padron | **Simulada** | Puerto `ClientePadron` con cliente real y simulación. En dev/tests el simulador lee un **YAML** (`datos/padron.yaml`) con **recarga en caliente**; lo no listado devuelve `false` (sin paridad, §13.1). **En prod ese atajo está prohibido** y el arranque se bloquea con `padron_modo=simulacion`. Depende de: endpoint municipal real + credenciales. |
| ciudadania | **Implementada** | Perfil, nivel (Platino/Black), tarjeta digital, historial de nivel. Tarjeta **física**: parcial (número emitido; no hay impresión/logística). |
| textos legales | **Parcial** | Términos del ciudadano, política de privacidad y convenio del comercio **cargados** como versión `v1` (§13.2, `docs/legal/*.md`), con la nota "no utilizar sin revisión legal" visible. **Borradores**: falta revisión de Asesoría Letrada. |
| comercios | **Implementada** | Adhesión (máquina de estados), sucursales con PostGIS, usuarios y roles, PIN de cajero atado a dispositivo, turnos, QR de comprobante en PDF. **Precarga (§13.3/§14.2/§15.3):** comando idempotente `cargar_comercios` siembra 38 comercios **reales de Rivadavia** (relevados de OpenStreetMap: nombre/rubro/coordenadas reales) en estado ACTIVA; **2 con promoción real confirmada** (Farmacia Cuyo y Cabral Mayorista: 20% tope $15.000), el resto con promo estimada marcada; bandera `precarga` + `baja_precarga` para baja en bloque (`docs/precarga-comercios.md`). |
| promociones | **Implementada** | Mecánicas, vigencia, topes atómicos, moderación por confianza, descubrimiento (pg_trgm + unaccent). |
| canje | **Parcial** | Transacción, idempotencia, anulación, modo offline: reales. Render del QR del ciudadano: **real** (QR escaneable, rota cada 45 s; §12.2-B). Confirmación **por consulta** (no hay push, ver Notificaciones). |
| puntos | **Implementada** | Libro append-only PC/PM, FIFO por lote, inventario municipal, reserva atómica. **Generación de PM: apagada por flag** (`ff_generacion_pm`) hasta que haya inventario real. |
| grupo | **Implementada** | Grupo familiar, herencia de nivel por evento, billetera común (pozo), sucesión, antifraude que solo observa. |
| contenido | **Parcial** | Cuota atómica, editor, superposición de texto, moderación, almacén de objetos: reales. **Generación de imágenes: simulada** (`GeneradorSimulacion`); el adaptador real exige API key y aún no hay proveedor elegido. Almacén: **local** (dev); falta bucket de prod. |
| gobierno | **Implementada** | Auditoría inmutable a nivel DB, parametría, doble conformidad, agentes municipales, recaudación por vistas. |
| modo demostración | **Implementada** | §13.5: `scripts/demo.py` deja con un comando 2 vecinos (Black/Platino), grupo familiar, comercio con cajero y turno abierto, promos de distintas mecánicas y puntos con movimientos. Idempotente (`docs/modo-demo.md`). |
| difusion (redes) | **Pendiente** | Publicación en redes sociales; fuera de alcance hasta su paso. |
| captacion | **Pendiente** | Módulo de captación; no construido. |

---

## Integraciones y adaptadores por proveedor

| Integración | Estado | Hoy hace | Depende de |
|---|---|---|---|
| Padrón municipal | **Simulada** | Veredicto desde `datos/padron.yaml` con recarga en caliente (dev/tests); lo no listado es `false` | Endpoint real + credenciales (`docs/padron-simulado.md`) |
| Verificación de identidad (RENAPER) | **Fuera de alcance** | Autodeclaración en el alta | Decisión de negocio; no pedido |
| OTP de celular | **Simulada** | Código por consola/log | Proveedor SMS |
| Correo / recuperación de cuenta | **Parcial** | Flujo completo + **adaptador SMTP real cableado** (§15.2, `EmailReal`); en dev por consola. Comando `probar_email` para probar el envío | Cargar los datos SMTP en `config/produccion.env` y `EMAIL_PROVEEDOR=real`; la guarda de arranque bloquea prod en simulación |
| Generación de imágenes IA | **Simulada** | Fondos de color deterministas, sin red | Proveedor elegido + API key (ver `docs/costo-ia.md`) |
| Almacén de objetos | **Parcial** | Disco local detrás de puerto | Bucket de producción |
| Almacén seguro móvil (Keychain/Keystore) | **Parcial** | Seam + migración + **plugin nativo cableado** (`capacitor-secure-storage-plugin` vía `AlmacenSeguroInit`, solo en dispositivo); en web dev, fallback a Preferences | Verificación en dispositivo (`cap:sync` + build nativo): CI no compila el proyecto nativo. |
| Tiles del mapa | **Parcial** | §13.0/§14.1: en dev/local usa el **OSM público** (por defecto). En **producción falla cerrado**: sin `NEXT_PUBLIC_TILES_URL` propia, el mapa muestra "no disponible" y **no** cae al server público. Falta generar/hostear los tiles propios: `scripts/generar-tiles.sh` (Java 21+) (`docs/tiles-mapa.md`) |

---

## Notificaciones — la mayor brecha (§12.6-A)

**No existe ningún canal real** (ni push, ni SMS, ni email). Todo lo que dependería de uno hoy se
resuelve por otro medio o queda pendiente:

| Necesidad | Hoy | Estado |
|---|---|---|
| Confirmación de canje | El ciudadano consulta desde la app (polling de pendientes) | **Parcial** (funciona sin canal) |
| Invitación al grupo familiar | El titular comparte el código a mano | **Parcial** |
| Aviso de cambio de nivel | Visible al entrar a la app | **Parcial** |
| Aviso de puntos por vencer | Visible en la billetera | **Parcial** |
| Aviso de sucesión de titular | Aviso visible en la app (`aviso_grupo`) | **Parcial** |
| Recuperación de cuenta | Token de un solo uso por email (consola en dev) | **Parcial** (falta proveedor real) |
| Aviso al comercio por moderación | — | **Pendiente** |
| Aviso por reuso de refresh token | — | **Pendiente** |

Decisión humana requerida: elegir proveedor(es) de notificación define qué se puede prometer al lanzar.

---

## Bloqueantes de lanzamiento

- **Tiles del mapa** (§12.6-B): en dev/local ya se ve con el **OSM público** (§13.0); en
  **producción falla cerrado** (§14.1): sin `NEXT_PUBLIC_TILES_URL` propia el mapa no carga (avisa)
  y no usa el server público. Falta generar/hostear los tiles propios
  (`scripts/generar-tiles.sh`, Java 21+) y apuntar `NEXT_PUBLIC_TILES_URL`. Sin responsable
  asignado. Arrastrado desde el PASO 07.
- **Proveedores de prod sin elegir**: padrón, OTP, email (recuperación), imágenes IA. Las guardas de
  arranque (§12.2-D) impiden salir a producción con cualquiera en simulación.
- **Recuperación de cuenta**: el flujo está completo; falta el **proveedor de email real**
  (`EMAIL_PROVEEDOR=real`) — la guarda de arranque bloquea prod hasta configurarlo.
- **Resguardo de la clave de cifrado de campos**: sin ella, el backup no alcanza — el DNI/CUIL queda
  irrecuperable (`docs/restauracion-backup.md`).

## Casi bloqueantes

- **Almacén seguro móvil**: el plugin nativo (`capacitor-secure-storage-plugin`) ya está cableado en
  el bootstrap; **falta verificarlo en un dispositivo real** (`cap:sync` + build nativo), porque CI
  no compila el proyecto nativo.
