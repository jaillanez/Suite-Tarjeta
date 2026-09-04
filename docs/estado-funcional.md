# Estado funcional de la plataforma

Qué es **real** y qué está **fingido**, sin ambigüedad. Se actualiza en cada paso.

Clasificación: **Implementada** (funciona de punta a punta con integración real) · **Parcial**
(funciona pero le falta una pieza) · **Simulada** (adaptador de simulación detrás de un puerto;
no llama a un servicio real) · **Pendiente** (no construida).

> Regla de negocio (§12.1): **el registro ciudadano es abierto** y el padrón solo asigna el nivel;
> **el comercio se valida** (solo inscripto y aprobado publica u opera).

---

## Módulos

| Módulo | Estado | Detalle / de qué depende para completarse |
|---|---|---|
| identidad | **Parcial** | Registro abierto, login, MFA (TOTP), dispositivos, perfiles: reales. **Verificación de identidad: autodeclarada** (no hay RENAPER; fuera de alcance, §12.2-C). Recuperación de cuenta: **pendiente** (necesita canal, ver Notificaciones). |
| padron | **Simulada** | Puerto `ClientePadron` con cliente real y simulación. En dev/tests el simulador decide por paridad de DNI/CUIT; **en prod ese atajo está prohibido** y el arranque se bloquea con `padron_modo=simulacion`. Depende de: endpoint municipal real + credenciales. |
| ciudadania | **Implementada** | Perfil, nivel (Platino/Black), tarjeta digital, historial de nivel. Tarjeta **física**: parcial (número emitido; no hay impresión/logística). |
| comercios | **Implementada** | Adhesión (máquina de estados), sucursales con PostGIS, usuarios y roles, PIN de cajero atado a dispositivo, turnos, QR de comprobante en PDF. |
| promociones | **Implementada** | Mecánicas, vigencia, topes atómicos, moderación por confianza, descubrimiento (pg_trgm + unaccent). |
| canje | **Parcial** | Transacción, idempotencia, anulación, modo offline: reales. **Render del QR del ciudadano: pendiente** (hoy muestra el token en texto; §12.2-B). Confirmación **por consulta** (no hay push, ver Notificaciones). |
| puntos | **Implementada** | Libro append-only PC/PM, FIFO por lote, inventario municipal, reserva atómica. **Generación de PM: apagada por flag** (`ff_generacion_pm`) hasta que haya inventario real. |
| grupo | **Implementada** | Grupo familiar, herencia de nivel por evento, billetera común (pozo), sucesión, antifraude que solo observa. |
| contenido | **Parcial** | Cuota atómica, editor, superposición de texto, moderación, almacén de objetos: reales. **Generación de imágenes: simulada** (`GeneradorSimulacion`); el adaptador real exige API key y aún no hay proveedor elegido. Almacén: **local** (dev); falta bucket de prod. |
| gobierno | **Implementada** | Auditoría inmutable a nivel DB, parametría, doble conformidad, agentes municipales, recaudación por vistas. |
| difusion (redes) | **Pendiente** | Publicación en redes sociales; fuera de alcance hasta su paso. |
| captacion | **Pendiente** | Módulo de captación; no construido. |

---

## Integraciones y adaptadores por proveedor

| Integración | Estado | Hoy hace | Depende de |
|---|---|---|---|
| Padrón municipal | **Simulada** | Veredicto por paridad de DNI/CUIT (solo dev/tests) | Endpoint real + credenciales |
| Verificación de identidad (RENAPER) | **Fuera de alcance** | Autodeclaración en el alta | Decisión de negocio; no pedido |
| OTP de celular | **Simulada** | Código por consola/log | Proveedor SMS |
| Recuperación de cuenta | **Pendiente** | Sin flujo funcional | Canal (email/SMS) |
| Generación de imágenes IA | **Simulada** | Fondos de color deterministas, sin red | Proveedor elegido + API key (ver `docs/costo-ia.md`) |
| Almacén de objetos | **Parcial** | Disco local detrás de puerto | Bucket de producción |
| Tiles del mapa | **BLOQUEANTE** | Aviso "mapa no disponible" | **Generar tiles; sin responsable** (`docs/tiles-mapa.md`) |

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
| Recuperación de cuenta | — | **Pendiente** |
| Aviso al comercio por moderación | — | **Pendiente** |
| Aviso por reuso de refresh token | — | **Pendiente** |

Decisión humana requerida: elegir proveedor(es) de notificación define qué se puede prometer al lanzar.

---

## Bloqueantes de lanzamiento

- **Tiles del mapa** (§12.6-B): sin generar, **sin responsable asignado**. Arrastrado desde el PASO 07.
- **Proveedores de prod sin elegir**: padrón, OTP/recuperación, imágenes IA. Las guardas de arranque
  (§12.2-D) impiden salir a producción con cualquiera en simulación.
