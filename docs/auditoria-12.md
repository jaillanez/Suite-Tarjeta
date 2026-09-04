# Auditoría PASO 12 — hallazgos priorizados

Recorrido completo del repositorio contra la regla de negocio autoritativa (§12.1 de la
especificación 2.3). Prioridad P0 (daño real) → P3 (deuda de calidad). Cada hallazgo indica
archivo:línea, comportamiento actual, esperado, riesgo y la prueba que falta.

Los arreglos van **después** de este informe, en tandas chicas y en orden de prioridad (un PR por
bloque). Nada se marca corregido sin una prueba que lo demuestre.

> Estado: **informe inicial**. La columna "Estado" se actualiza a `CORREGIDO (PR #n)` a medida que
> se cierra cada hallazgo.

---

## Regla de negocio autoritativa (§12.1) — verificación por caminos

La separación ciudadano-abierto / comercio-validado debe cumplirse en **todos** los caminos.

| # | Camino | Actual | Esperado | Estado |
|---|---|---|---|---|
| BR-1 | Registro ciudadano | Abierto; el padrón no bloquea (`registrar_persona.py`), y `consultar_y_actualizar` no degrada si el padrón cae (`padron/application/consultar.py:33`) | Correcto | **OK, falta test** |
| BR-2 | Mapa `cercanas` | `comercios/infrastructure/repositories.py:cercanas` filtra `SucursalModel.estado == ACTIVA` pero **no** valida el estado del comercio padre | Solo sucursales de comercios `APROBADA`/`ACTIVA` | **GAP → P1-F** |
| BR-3 | Búsqueda/feed/motor de promos | `promociones/infrastructure/repositories.py` (`candidatas`, `buscar`, `nuevas_desde`, `exclusivas_black`) filtra por estado de la **promoción**, no del **comercio** | Excluir promos de comercios no aprobados/suspendidos | **GAP → P1-F** |
| BR-4 | Operar canje / emitir puntos | `requiere_comercio` (`comercios/api/deps.py`) valida rol y permiso, **no** el estado del comercio | Solo un comercio `APROBADA`/`ACTIVA` opera canjes | **GAP → P1-F** |
| BR-5 | Publicar promoción | Verificar que `publicacion` exija comercio aprobado | Solo inscripto y aprobado publica | **A verificar → P1-F** |

Los cinco necesitan test por cada camino (criterio de aceptación explícito).

---

## P0 — van primero, cada uno puede causar daño real

### P0-A · El cliente de API reintenta mutaciones
- **Archivo:** `packages/api-client/src/index.ts:59-90` (`request` reintenta en 5xx y en error de
  red para **cualquier** método, incluidos POST/PUT/DELETE).
- **Actual:** un POST de canje cuya respuesta se pierde se reintenta hasta `maxRetries=3` →
  aplica el descuento y acredita puntos **dos veces**. Es plata del comercio.
- **Esperado:** sin reintentos automáticos de mutaciones no idempotentes. GET reintentables;
  POST/PUT/DELETE no, salvo que lleven clave de idempotencia y el backend la respete.
- **Riesgo:** doble descuento / doble acreditación / adhesiones y aprobaciones duplicadas.
- **Falta test:** una respuesta perdida en `iniciar`/`confirmar` no duplica la transacción.

### P0-B · Verificar que el QR se renderice como QR
- **Archivo:** `apps/mobile/src/app/(ciudadano)/tarjeta/page.tsx:131-132` (muestra el token como
  `<p class="font-mono">`, con el comentario "en la app real esto se renderiza como QR").
- **Actual:** el token va en **texto plano**, no como código escaneable. El cajero no puede
  escanear → el canje directo no funciona.
- **Esperado:** render como QR real (SVG/canvas) desde el token vigente.
- **Riesgo:** el flujo principal de canje es inoperable.
- **Falta test:** el componente renderiza un `<svg>`/`<canvas>` de QR, no texto.

### P0-C · Trazabilidad falsa de identidad (RENAPER)
- **Archivo:** `modules/identidad/application/registrar_persona.py:76`
  (`persona.verificar_identidad(MetodoVerificacion.RENAPER)`), enum en
  `modules/identidad/domain/persona.py:32-35`, stub en `infrastructure/renaper_stub.py`.
- **Actual:** el registro etiqueta `metodo_verificacion = RENAPER` sin haber consultado RENAPER.
- **Esperado:** `AUTODECLARADA` para el alta por la app; `PRESENCIAL` en mostrador; `DOCUMENTAL`
  si hubo proceso documental. RENAPER fuera del flujo y del código.
- **Riesgo:** afirmar una verificación que no ocurrió, en un sistema público.
- **Migración:** corregir los registros existentes mal etiquetados (`RENAPER` → `AUTODECLARADA`).
- **Revisar:** `ff_exigir_identidad_verificada` (`config.py:138`, usada en `identidad/api/deps.py:51`):
  conservar apagada y sin afectar canjes, o eliminar.
- **Falta test:** un registro nuevo queda `AUTODECLARADA`; la migración reetiqueta los viejos.

### P0-D · Guardas de arranque en producción
- **Archivo:** `main.py:create_app` (no valida `environment`); `config.py` (`padron_modo` sim,
  `renaper_stub_resultado`, OTP/recuperación por consola, `contenido_proveedor` sim).
- **Actual:** nada impide arrancar en `prod` con padrón simulado, JWT débil, clave de cifrado
  inválida, CORS permisivo, adaptadores de consola o integraciones críticas en simulación. Además
  el padrón simulado usa **paridad de DNI/CUIT**, que en prod habilitaría comercios por tener CUIT par.
- **Esperado:** la app se **niega a iniciar** en `prod` ante cualquiera de esas condiciones; la
  paridad de DNI/CUIT solo vale en dev/tests.
- **Riesgo:** despliegue inseguro silencioso.
- **Falta test:** con `environment=prod` + simulación crítica, `create_app` levanta error.

---

## P1 — sesión, accesos y correctitud

### P1-A · Refresh token en `localStorage` (web)
- **Archivo:** `apps/web/src/lib/session.ts:8-11,19-21` (guarda access+refresh en `localStorage`
  y usa `document.cookie tarjeta_sesion=1` como indicador manipulable).
- **Esperado:** refresh en cookie `HttpOnly`/`Secure`/`SameSite`; sin cookie manipulable como
  prueba de sesión; revisar CSRF; mantener rotación; migrar/limpiar lo guardado.
- **Riesgo:** robo de refresh por XSS.
- **Falta test:** login no deja el refresh accesible a JS; middleware no confía en cookie falsificable.

### P1-B · Tokens móviles en `Preferences`
- **Archivo:** `apps/mobile/src/lib/session.ts:10-11` (access+refresh en `@capacitor/preferences`).
- **Esperado:** credenciales en almacenamiento protegido del SO (Keychain/Keystore);
  `Preferences` solo para no sensibles (perfil activo). Migrar lo ya guardado.
- **Riesgo:** credenciales legibles en el dispositivo.
- **Falta test:** el helper de sesión usa el almacén seguro.

### P1-C · Middleware de rutas incompleto (web)
- **Archivo:** `apps/web/middleware.ts` (matcher sin `/agentes`, `/aprobaciones`, `/auditoria`,
  `/puntos`, `/piezas`, `/mi-comercio`, `/contenido`).
- **Esperado:** política centralizada por espacio de nombres (grupos de rutas), no enumeración.
  La API sigue validando siempre (el middleware es comodidad, no seguridad).
- **Riesgo:** rutas privadas accesibles sin sesión (UX; la API igual corta).
- **Falta test:** navegar sin sesión a cada ruta privada redirige a login.

### P1-D · Health check expone la versión de PostgreSQL
- **Archivo:** `main.py:106-112` (`/health/db` devuelve `version()` completo).
- **Esperado:** separar liveness (`/health`), readiness (`/health/ready`) y diagnóstico interno
  protegido. La versión exacta del motor no va en un endpoint público.
- **Riesgo:** fingerprinting para explotación dirigida.
- **Falta test:** `/health/db` (o su reemplazo público) no expone la versión.

### P1-E · Auditoría de concurrencia y autorización
- **Alcance:** doble confirmación de canje, doble consumo/acreditación de puntos, reuso de
  códigos/tokens, confirmaciones vencidas, pertenencia del recurso al comercio autenticado (IDOR),
  escalamiento de permisos, reuso de refresh, idempotencia de consumidores del outbox, y jobs
  ejecutados por varias réplicas.
- **Actual:** buena base (reservas atómicas, nonce de QR, ventana de confirmación, dedup en el
  libro). A revisar y cubrir con test donde falte evidencia; documentar en el informe cada punto.
- **Falta test:** casos de IDOR (recurso de otro comercio) y de reuso donde no haya cobertura.

### P1-F · Gating de comercio no aprobado (regla BR-2..BR-5)
- Ver la tabla de arriba. Agregar el filtro por estado del comercio en mapa, búsqueda/feed/motor y
  operación de canje, con **un test por camino**.

---

## P2 — honestidad del producto

### P2-A · Matriz de funcionalidad (`docs/estado-funcional.md`)
- **Actual:** no existe. Nadie tiene la lista completa de qué es real y qué está simulado.
- **Esperado:** cada funcionalidad como **implementada / parcial / simulada / pendiente**, con su
  dependencia para completarse. Incluye la brecha de notificaciones (§12.6-A) y el bloqueante de
  tiles (§12.6-B). Se actualiza en cada paso.

### P2-B · Datos de mentira en pantallas reales
- **Archivos:** `apps/web/src/app/(publico)/page.tsx:11,17` ("Vecino de ejemplo", "Pantalla de
  ejemplo"), `apps/mobile/src/app/page.tsx:15` ("Vecino de ejemplo"),
  `apps/mobile/src/app/(ciudadano)/tarjeta/page.tsx:91` (`nombre="Titular"` fijo), y varias
  "En construcción (PASO 02)" (`(ciudadano)/inicio`, `/mapa`, `(municipal)/operacion`,
  `(publico)/comercio/[slug]`, `campania/[slug]`, `(municipal)/campanias`).
- **Esperado:** completar o marcar con claridad como no disponible. No aparentar terminado.
- **Riesgo:** una pantalla que finge datos reales es peor que una vacía.

### P2-C · Manejo de errores del frontend
- **Archivos:** `catch { push('/login') }` en `(publico)/{registro,perfil,mi-estado,seleccionar-perfil}`
  y en mobile `(ciudadano)/{tarjeta,mi-estado}`, `seleccionar-perfil`.
- **Actual:** cualquier excepción redirige al login.
- **Esperado:** distinguir 401 (sesión vencida) / 403 / 404 / 409-422 (negocio) / 500 / red. Los
  errores durante la confirmación de canje **no se pueden ignorar en silencio**.
- **Falta test:** cada código produce el estado de UI correcto.

---

## P3 — tests de frontend

- **Actual:** no hay ninguno.
- **Esperado:** cubrir la lista de §12.5 (login/salida, refresh, protección de rutas, selección de
  perfil, registro abierto, ciudadano fuera del padrón, `al_dia=false`, padrón caído, comercio no
  habilitado / pendiente / activo, promos no publicables desde comercio inactivo, reintentos e
  idempotencia, errores sin conexión, QR con confirmación). Al menos un flujo E2E si la infra lo
  permite.

---

## §12.6 — lo que la revisión no cubrió

### 12.6-A · No existe canal de notificaciones
- Ni push, ni SMS, ni email real. Dependen de un canal inexistente: confirmación de canje
  (hoy por consulta), invitaciones al grupo (a mano), aviso de nivel, puntos por vencer,
  recuperación de cuenta, aviso de moderación al comercio, aviso de reuso de refresh.
- **Acción:** listarlo explícito en `docs/estado-funcional.md` con lo que hace hoy cada uno. Es la
  mayor brecha del sistema.

### 12.6-B · Tiles del mapa sin generar
- **Bloqueante de lanzamiento** sin responsable, arrastrado desde el PASO 07 (`docs/tiles-mapa.md`).
  Debe figurar en la matriz con la palabra **bloqueante**.

### 12.6-C · Nunca se probó restaurar un backup
- **Actual:** hay `docker-compose.yml` y volúmenes, pero ningún procedimiento probado de
  restauración. Un backup no probado no es un backup.
- **Acción:** hacer la prueba de restauración completa y dejar `docs/restauracion-backup.md`.

---

## §12.7 — documentación desalineada

- `README.md`, `docs/arquitectura.md`, `docs/VERSIONS.md` deben decir sin ambigüedad: adhesión
  ciudadana abierta, padrón solo para el nivel, RENAPER fuera de alcance, verificación obligatoria
  solo para comercios, diferencia entre solicitar/aprobar/publicar, estado real de cada módulo e
  integraciones pendientes. Alinear con la especificación 2.3.

---

## Orden de corrección propuesto (un PR por bloque)

1. **PR-audit:** este informe + `docs/estado-funcional.md` + docs alineadas a 2.3 (P2-A, §12.7, 12.6-A/B).
2. **PR-P0:** A (reintentos), B (QR), C (RENAPER + migración), D (guardas de prod). ← daño real.
3. **PR-BR:** gating de comercio no aprobado en todos los caminos + tests de la regla de negocio (BR-1..BR-5).
4. **PR-P1-sesión:** A (cookies web + CSRF), B (móvil seguro), C (middleware), D (health).
5. **PR-P1-E:** hallazgos de concurrencia/autorización con test donde falte.
6. **PR-P2/P3:** datos de mentira, manejo de errores, tests de frontend.
7. **PR-backup:** restauración probada + procedimiento (12.6-C).

## Riesgos que requieren decisión humana

- **Proveedores reales** (padrón, notificaciones, imágenes IA): sin elegir. Las guardas de prod
  bloquean el arranque hasta que se configuren; alguien debe decidir y contratarlos.
- **Tiles del mapa:** bloqueante de lanzamiento sin responsable.
- **Canal de notificaciones:** brecha estructural; define qué se puede prometer al lanzar.
- **Backup/restore:** hay que validar la infraestructura real de producción, no solo el compose local.
