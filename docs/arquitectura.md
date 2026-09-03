# Arquitectura — suite-tarjeta (backend)

Monolito modular con DDD por módulos. Una sola base de datos PostgreSQL, un solo
despliegue. **No microservicios.** El objetivo es que los límites entre módulos sean
explícitos y verificados por herramienta, no por disciplina.

## Diagrama de capas

Dentro de cada módulo (y del shared kernel) las dependencias van en una sola dirección:

```
        ┌─────────────────────────────────────────┐
        │                   api                     │  routers FastAPI, schemas Pydantic
        └───────────────────┬───────────────────────┘
                            │ importa
                            ▼
        ┌─────────────────────────────────────────┐
        │               application                 │  casos de uso, DTOs, puertos
        └───────────────────┬───────────────────────┘
                            │ importa
                            ▼
        ┌─────────────────────────────────────────┐
        │                 domain                    │  entidades, VOs, eventos, PUERTOS
        └───────────────────▲───────────────────────┘
                            │ implementa los puertos
        ┌───────────────────┴───────────────────────┐
        │             infrastructure                 │  SQLAlchemy, adaptadores externos
        └─────────────────────────────────────────┘
```

## Reglas de dependencia (verificadas por import-linter)

1. `domain` no importa nada de `application`, `infrastructure` ni `api`. Tampoco
   SQLAlchemy, FastAPI, Pydantic ni httpx. Es Python puro + `shared.domain`.
2. `application` importa `domain`. Depende de los **puertos** definidos en `domain`,
   nunca de sus implementaciones. No importa `infrastructure` ni `api`.
3. `infrastructure` implementa los puertos de `domain`. Es la única capa que conoce
   SQLAlchemy.
4. `api` importa `application`. Nunca llama a un repositorio directo ni contiene reglas
   de negocio.
5. **Entre módulos:** un módulo nunca importa el `domain` ni la `infrastructure` de otro.
   La comunicación es por eventos de dominio o por interfaces publicadas en `application`.

Estas reglas se hacen cumplir automáticamente con tres contratos de `import-linter`
(ver `apps/api/pyproject.toml`):

- **forbidden** — el dominio no puede importar sqlalchemy/fastapi/pydantic/httpx.
- **layers** — orden `api > application > domain` en los 13 módulos.
- **independence** — los 13 módulos no se importan entre sí.

Si `lint-imports` falla, el build falla.

## Módulos

| Módulo | Agregados principales | Responsabilidad |
|---|---|---|
| `identidad` | Persona, Credencial, Consentimiento | Registro, autenticación, MFA, perfiles, sesiones y dispositivos |
| `padron` | EstadoPadron | Único punto de contacto con el endpoint municipal. Cachea el veredicto. |
| `ciudadania` | PerfilCiudadano, GrupoFamiliar, Tarjeta | Nivel Platino/Black, grupo familiar, tarjeta digital y física |
| `comercios` | Comercio, Sucursal, UsuarioComercio | Adhesión, sucursales, roles del comercio |
| `promociones` | Promocion | Ciclo de vida, segmentación, límites, moderación |
| `canje` | Transaccion | Tokens, validación, idempotencia, anulación, modo offline |
| `puntos` | Billetera, MovimientoBilletera, Lote | Libro mayor de PC y PM. Append-only. FIFO por lote. |
| `contenido` | Creatividad | Generación con IA, guardarraíles, cola de moderación |
| `difusion` | Publicacion | Redes sociales, cola editorial, métricas |
| `notificaciones` | Notificacion | Push, email, SMS, WhatsApp. Reglas de higiene. |
| `antifraude` | Alerta, Caso | Motor de reglas. Genera casos, no bloquea. |
| `captacion` | ProspectoComercio, Visita | CRM del embudo de comercios |
| `gobierno` | Parametro, RegistroAuditoria, SolicitudAprobacion, AgenteMunicipal | Roles y permisos municipales, parametría, auditoría inmutable, doble conformidad, tablero |

### Invariantes que quedan imposibles de violar por construcción

- `puntos`: `MovimientoBilletera` no expone métodos de actualización ni borrado.
- `gobierno`: `RegistroAuditoria` es append-only **a nivel motor**: la migración hace
  `REVOKE UPDATE, DELETE, TRUNCATE ON registro_auditoria FROM tarjeta_app`, y como el rol de
  runtime no es dueño de la tabla no puede volver a otorgárselo. Ni el superadministrador desde
  la app puede modificar ni borrar auditoría.
- `ciudadania`: el nivel no tiene setter público; cambia por el motor o por una excepción
  con vigencia y motivo.
- `padron`: nunca se persisten montos, cuentas, cuotas ni vencimientos.

## Shared kernel (`shared/`)

Núcleo transversal reutilizable por todos los módulos, con las mismas cuatro capas:

- `shared/domain`: `Entity`, `AggregateRoot`, `DomainEvent`, jerarquía `DomainError`,
  y value objects (`EntityId`, `Dni`, `Cuil` con dígito verificador, `Dinero`, `Porcentaje`).
- `shared/application`: `Command`/`Query`/handlers, `AbstractUnitOfWork`, `EventBus`.
- `shared/infrastructure`: `Base` declarativa, motor async, `SqlAlchemyUnitOfWork`,
  repositorio genérico, outbox, logging estructurado.
- `shared/api`: mapeo `DomainError → HTTP`, paginación, dependencias de FastAPI.

## Base de datos y roles

- **Rol `tarjeta_migrator`**: dueño del esquema, corre Alembic. Tiene DDL.
- **Rol `tarjeta_app`**: lo usa la API en runtime. **No puede crear ni alterar estructura**
  (verificado: `CREATE TABLE` como `tarjeta_app` da *permission denied*).
- Dos URLs de conexión separadas en configuración: `database_url` (app) y
  `database_migrator_url` (Alembic).
- Identificadores: UUIDv7 nativo de PostgreSQL 18 (`uuidv7()`), ordenables por tiempo,
  y `uuid.uuid7()` en Python 3.14 para generarlos del lado de la app.

## Configuración

Toda parametrización vive en `config.py` (pydantic-settings) o en variables de entorno
con prefijo `TARJETA_`. **Nada de valores fijos en el código.** Los datos del municipio
(nombre, provincia, zona horaria, logo) son configuración: no se escriben literalmente en
ningún otro módulo. Ver `.env.example`.

## Cómo agregar un módulo nuevo

1. Crear `src/tarjeta/modules/<nombre>/` con las cuatro capas:
   `domain/`, `application/`, `infrastructure/`, `api/` (cada una con `__init__.py`).
2. Modelar en `domain`: entidades, value objects, eventos y **puertos** (interfaces de
   repositorio como `Protocol`/ABC). Sin SQLAlchemy.
3. Escribir los casos de uso en `application`, dependiendo de los puertos del `domain`.
4. Implementar los puertos en `infrastructure` con SQLAlchemy (modelos, mappers,
   repositorios que heredan de `SQLAlchemyRepository`).
5. Exponer routers y schemas en `api`, delegando en los casos de uso.
6. Agregar el módulo a los contratos `layers` e `independence` en `pyproject.toml`.
7. La comunicación con otros módulos es por eventos de dominio; nunca importando su
   `domain`/`infrastructure`.
8. Correr `lint-imports`, `mypy`, `ruff` y `pytest` antes de commitear.

## Frontend (PASO 02)

Monorepo pnpm con dos apps Next.js 16 y paquetes compartidos:

- `apps/web` — Next.js con **SSR**. Sitio público (indexable, con Open Graph) + portal
  comercio + portal municipal. `promo/[id]` genera Open Graph en el servidor
  (`opengraph-image.tsx` con `next/og`): es la razón de que esta app no sea estática.
- `apps/mobile` — Next.js con `output: 'export'` (estático), envuelto en Capacitor 8.5.1.
  Sin middleware, sin route handlers, sin server actions: todo el fetching es del lado del
  cliente contra la API.
- `packages/ui` — shadcn/ui + componentes de dominio (`NivelBadge`, `TarjetaCredencial`).
  El tema vive **solo** en `packages/ui/src/styles/theme.css` (Tailwind 4, directiva
  `@theme`). **No existe `tailwind.config.js`.**
- `packages/api-client` — cliente TS generado desde el OpenAPI 3.1 de FastAPI
  (`openapi-typescript`), con wrapper de fetch (base URL, auth, reintentos, errores).
- `packages/config` — tsconfig base estricto, ESLint (jsx-a11y en error) y Prettier.

### Piso de navegador soportado

Tailwind CSS 4 usa características modernas de CSS y apunta a navegadores recientes. El piso
soportado del programa es:

| Navegador | Versión mínima |
|---|---|
| Safari / iOS Safari | 16.4+ |
| Chrome / Android WebView | 111+ |
| Firefox | 128+ |
| Edge | 111+ |

Consecuencia operativa: la **pantalla de caja** debe funcionar en el celular viejo del
mostrador y en la PC vieja del comercio. Antes de cerrar el PASO 06 hay que **probar la caja
en un dispositivo de gama baja real**. Si el piso no alcanza, el **código de 6 dígitos**
(que no requiere cámara ni JS moderno de escaneo) es el camino de respaldo que nunca debe
depender de estas versiones.

### Limitación conocida: modo caja bloqueado en iOS (no simétrico)

La especificación (§4.6) pide que, con el turno abierto, la app quede fijada en la pantalla
de caja y que salir exija el PIN del encargado.

- **Android:** hay fijado de pantalla a nivel de sistema operativo → se logra el
  comportamiento pedido.
- **iOS:** el equivalente es **Acceso Guiado**, que **no se puede activar por programa**; lo
  activa el usuario a mano desde los ajustes del dispositivo.

En iPhone, entonces, el bloqueo real a nivel de sistema no es posible. Queda solo el bloqueo
dentro de la app (el cambio de perfil pide PIN), que protege del empleado curioso pero no de
quien sale de la app y la vuelve a abrir. **Es una decisión de producto pendiente:** instruir
a los comercios con iPhone a activar Acceso Guiado a mano, o aceptar el bloqueo más débil.

### Modo caja bloqueado y permisos

- Permisos nativos (cámara, ubicación, notificaciones): se piden **en el momento de uso**, no
  al instalar (§11.2).
- Escáner QR elegido: **@capacitor-mlkit/barcode-scanning** (MLKit; peer `@capacitor/core >=8`).

## Módulo `identidad` (PASO 03)

Primer módulo con lógica de negocio: registro, verificación de celular, login, MFA,
perfiles y dispositivos.

### Cifrado de datos personales (§8.3)

Patrón de **dos columnas por dato sensible** (DNI y CUIL):

| Columna | Contenido | Uso |
|---|---|---|
| `dni_hash` / `cuil_hash` | HMAC-SHA256 del valor **normalizado** (solo dígitos), con un *pepper* de aplicación | Índice **único** y búsqueda por igualdad |
| `dni_cifrado` / `cuil_cifrado` | Valor cifrado con AES-256-GCM, con prefijo de versión de clave | Recuperar el valor cuando hay que mostrarlo |

- El **pepper** (HMAC) y la **clave de cifrado** viven en configuración
  (`TARJETA_FIELD_PEPPER`, `TARJETA_FIELD_ENCRYPTION_KEY`), **nunca en la base**.
- Normalización antes de hashear: el mismo DNI con o sin puntos produce el mismo hash
  (garantiza unicidad). Verificado por test.
- Rotación de clave: el texto cifrado lleva `vN:` como prefijo (`field_encryption_key_version`).
- El valor en claro **no existe en ninguna columna**.
- **Redacción en logs**: el logging estructurado del shared kernel redacta por patrón los
  DNI (7-8 dígitos) y CUIL (11 dígitos). El domicilio no se loguea nunca (disciplina).
  Verificado por test.

### Contraseñas

argon2id (`argon2-cffi`), parámetros en configuración (`argon2_*`); rehash automático al
iniciar sesión si cambian los parámetros; comparación en tiempo constante; login que **no
revela si el usuario existe** (mismo error y se hashea igual cuando el usuario no existe).

### Sesiones y tokens

- **Access token**: JWT HS256 corto (`jwt_access_ttl_seconds`, 900 s) con `sub`, `perfil` y
  `permisos`. Sin datos personales.
- **Refresh token**: opaco, guardado con hash (SHA-256) en `refresh_token`, **rotado en cada
  uso**. Familia por sesión (`family_id`).
- **Detección de reuso**: si llega un refresh ya usado, se **revoca toda la familia** y el
  intento falla (401). Convierte un token robado en un incidente detectado.
- **Timeouts por perfil activo** (§11.3): ciudadano generoso, comercio 30 min, municipal 10 min.
- **MFA (TOTP)** para perfiles municipales y Admin de Comercio, con códigos de recuperación
  de un solo uso (guardados con hash). El perfil municipal exige además un **dispositivo
  registrado y autorizado**.

### Puertos y adaptadores

Puertos en `domain/ports.py` (repositorios, `HashDeContrasena`, `EnvioOtp`, `AlmacenOtp`,
`RateLimiter`, `VerificadorIdentidad`, `GeneradorTotp`, `GeneradorTokenAcceso`,
`AlmacenRefresh`, `AlmacenMfa`, `TextosLegales`, `Outbox`). Adaptadores en `infrastructure/`:
argon2, pyotp (TOTP), PyJWT, RENAPER **stub** (resultado configurable), OTP por **consola**
(deshabilitado fuera de `dev`), Redis (OTP + rate limiting), refresh sobre SQLAlchemy.

### Eventos (outbox)

Los casos de uso escriben eventos (`PersonaRegistrada`, `SesionIniciada`,
`IntentoDeLoginFallido`, `PerfilCambiado`, `DispositivoRevocado`, `ConsentimientoOtorgado`,
`ConsentimientoRevocado`) en la tabla `outbox`, en la **misma transacción** que el cambio de
estado. El **consumidor de auditoría inmutable** (`gobierno`) está suscripto a *todos* los
eventos (`subscribe_all`) y los persiste en `registro_auditoria`, redactando DNI/CUIL antes de
guardar (§8.3) y de forma idempotente por `id_evento_origen`. Ver el worker de outbox más abajo.

### Frontend

- `apps/web`: registro (con consentimientos separados), login con MFA, selector de perfil,
  perfil con dispositivos y cierre remoto. **Middleware real** que protege las rutas de
  comercio y municipio (cookie de presencia de sesión; la validez la valida la API).
- `apps/mobile`: login y selector de perfil; el perfil activo y los tokens se persisten con
  el plugin **Preferences** de Capacitor. Sin middleware (protección del lado del cliente +
  validación en la API).

## Módulos `padron` y `ciudadania` (PASO 04)

Convierten el programa en política fiscal: el nivel se calcula a partir del veredicto
municipal y se comunica al vecino.

### Comunicación por eventos (sin importar módulos)

Los módulos no se importan entre sí (verificado por import-linter). Se comunican por el
**outbox compartido** (`shared/infrastructure/outbox.py`) y un **EventDispatcher** cableado
en el composition root `tarjeta/orquestacion.py`. Un middleware de la app drena el outbox
después de cada request y entrega los eventos a los handlers (procesa cadenas).

| Evento | Emite | Consume | Efecto |
|---|---|---|---|
| `IdentidadVerificada` | identidad | padron + ciudadania | padron consulta el veredicto; ciudadania crea `PerfilCiudadano` (Platino) y emite la tarjeta |
| `EstadoPadronActualizado` | padron | ciudadania | recalcula el nivel |
| `SolicitudActualizarEstado` | ciudadania | padron | reconsulta (botón "Actualizar mi estado") |
| `NivelCambiado` | ciudadania | (futuro notificaciones) | avisar a la persona |

### `padron` — único contacto con el municipio

- Contrato mínimo (§7.1): `?dni → {al_dia}`, `?cuit → {es_comerciante}`. **Un booleano por
  consulta.** Puerto `ClientePadron` con adaptador **real** (httpx) y **simulación**
  (respuestas configurables por archivo + regla determinística), elegidos por configuración
  (`padron_modo`). Test de contrato con `httpx.MockTransport`.
- `EstadoPadron` cachea solo `al_dia`, `es_comerciante`, `fecha_ultima_consulta` (dato
  propio) + histórico append-only. **No existe ninguna columna de monto/cuenta/cuota/
  vencimiento** (test lo verifica). El DNI se guarda cifrado (AES-GCM).
- **Degradación (§7.3):** si el endpoint no responde, se conserva el último estado y **nadie
  baja de nivel**. Batch nocturno: `uv run python -m tarjeta.scripts.sync_padron` (concurrencia
  acotada, tolerante a fallas individuales).

### `ciudadania` — motor de nivel y tarjeta

- Niveles **Platino/Black**: `BLACK` si `al_dia` (o excepción vigente), `PLATINO` en otro caso.
- `PerfilCiudadano`: el nivel **no tiene setter público** (cambia por `recalcular` o excepción).
  `HistorialNivel` es append-only y guarda un **snapshot textual de la regla**.
- **Excepciones de nivel** con vigencia y motivo, que **expiran solas** (el motor las consulta;
  no editan el nivel).
- **Tarjeta**: número de 16 dígitos con dígito verificador (Luhn), estados
  ACTIVA/BLOQUEADA/SUSPENDIDA/BAJA, bloqueo por robo/pérdida. Se emite al verificarse la
  identidad.

### Pantalla "Mi estado" (§3.2)

`al_dia=true` → **Black** ("estás al día…"). `al_dia=false` → **Platino** con texto
**condicional que nunca afirma deuda** (el inquilino que no figura también cae en Platino).
Muestra "actualizado hace N horas" (con `fecha_ultima_consulta`) y el botón "Actualizar mi
estado" (máx. 3/día, contador en Redis). En web y móvil.

### Ajustes del PASO 03 saldados

- **Huella de dispositivo**: el cliente la envía en `X-Device-Huella`; entra en el access
  token y se valida en cada request. Activar el perfil municipal exige que la huella de la
  petición corresponda a un dispositivo autorizado (no basta con tener uno).
- **Registro sin OTP** (§04.0.B): DNI + fecha de nacimiento + contraseña + consentimientos.
  El nivel se determina consultando el padrón por DNI. Recuperación por email. Rate limiting
  reforzado. En esta etapa la identidad se auto-verifica por DNI (el `EnvioOtp` y su adaptador
  de consola quedan para cuando haya proveedor); el reclamo de cuenta por alta presencial
  (PASO 05) es el remedio ante suplantación.

## Módulo `gobierno` y portal municipal (PASO 05)

Convierte al municipio en operador del programa: quién puede hacer qué, con qué controles y
con qué trazabilidad.

### Roles y matriz de permisos (§2.2)

- Cinco roles: `SUPER_ADMIN`, `ADMINISTRADOR`, `ENCARGADO`, `PERSONAL`, `AUDITOR`, con un
  **rango** ordenado. `AUDITOR` es estrictamente de solo lectura.
- La **matriz** rol→permisos vive como **datos** (`domain/roles.py::MATRIZ`), no como `if`
  dispersos. La dependencia FastAPI `requiere(permiso)` exige perfil municipal activo, resuelve
  el rol del agente desde la tabla propia de `gobierno` (`agente_municipal`, sin importar
  `identidad`) y aplica la matriz. Un test verifica **celda por celda**.

### Doble conformidad (§05.5)

- Acciones sensibles (`reglas_nivel:editar`, `ciudadano:reclamo`, `datos:exportar_masivo`) no
  se ejecutan solas: crean una `SolicitudAprobacion` que **otro** agente debe aprobar.
- Reglas del agregado: **no autoaprobación**, **rango del aprobador ≥ del solicitante**,
  **expiración a las 72 h**. Si el ejecutor de la acción falla, la solicitud queda en `ERROR`
  (no se pierde). Al aprobar `reglas_nivel:editar` se aplica el cambio de parámetro; al aprobar
  un reclamo (portal) se revoca la sesión anterior y se resetean credenciales.

### Auditoría inmutable (§05.4)

- `RegistroAuditoria` es append-only **a nivel motor** (ver invariantes): `REVOKE UPDATE,
  DELETE, TRUNCATE … FROM tarjeta_app` en la migración; `tarjeta_app` queda con `ar`
  (INSERT + SELECT) y, al no ser dueño, no puede re-otorgarse la escritura. Verificado en test
  de integración (UPDATE/DELETE como rol de runtime → *permission denied*).
- El consumidor está suscripto a **todos** los eventos, **redacta DNI/CUIL** antes de guardar y
  es **idempotente** por `id_evento_origen` (índice único).

### Worker de outbox con reintentos (§05.1)

- La tabla `outbox` sumó `intentos`, `proximo_intento`, `muerto`, `error`. El `EventDispatcher`
  procesa **un evento por transacción**; ante falla hace rollback, incrementa `intentos` con
  **retroceso exponencial** (`min(300, 2**intentos)` s) y a los `MAX_INTENTOS=5` lo manda a la
  **cola de muertos** (`muerto=true`). Toma trabajo con `SELECT … FOR UPDATE SKIP LOCKED`
  (seguro con múltiples workers).
- Corre como **proceso aparte** del tráfico HTTP: `uv run python -m tarjeta.scripts.outbox_worker`
  (además del drenado oportunista en el middleware y del worker del `lifespan`). Un test drena
  el outbox **sin ninguna request** y comprueba que la auditoría no guarda PII.

### Parametría (§5.5)

- Catálogo de parámetros enteros con rango válido (`domain/parametro.py`); editarlos audita el
  valor anterior y el nuevo. Un valor fuera de rango se rechaza (422). Nada de reglas fijas en
  el código.

### MFA obligatorio y puerta de canje

- **MFA enrolado obligatorio** para activar el perfil municipal (además de dispositivo
  autorizado): sin `MfaEstado` activo → 403 (`MfaNoEnrolado`).
- La **puerta de canje** depende de un parámetro explícito (`ff_exigir_identidad_verificada`),
  no del stub de verificación: `GET /api/v1/canje/puerta` sólo deja canjear si corresponde.

### Portal municipal (frontend)

Grupo de rutas `apps/web/(municipal)` con layout propio y **cierre de sesión por inactividad a
los 10 min** (avisa 1 min antes; los formularios guardan **borrador** en `sessionStorage`, así
no se pierde lo tipeado). Páginas: **Tablero** (recaudación + distribución por nivel),
**Ciudadanos** (ficha 360 con reautenticación, alta presencial, reclamo de cuenta),
**Parametría**, **Aprobaciones** (bandeja de doble conformidad), **Auditoría** (tabla con
filtros) y **Agentes** (asignación de rol). Endpoints cross-módulo en el composition root
`tarjeta/portal_municipal.py` (no es un módulo; por eso puede importar varios).

## Módulo `comercios` y portal del comercio (PASO 06)

Habilita el otro lado del programa: un comercio se adhiere, carga sus sucursales en el mapa y
da de alta a sus encargados y cajeros; el municipio lo aprueba, suspende o da de baja.

### Adhesión y máquina de estados (§06.2)

- `SOLICITADA → EN_REVISION → APROBADA → ACTIVA`, con ramas `DOCUMENTACION_PENDIENTE` y
  `RECHAZADA`, `ACTIVA ⇄ SUSPENDIDA` y `→ BAJA`. Transiciones inválidas lanzan error; cada
  cambio lleva motivo y evento (auditado por el consumidor de gobierno).
- **Verificación por CUIT** contra el padrón: `comercios` no contacta el endpoint (lo hace solo
  `padron`). El `VerificadorComerciante` es un puerto que el composition root
  `tarjeta/portal_comercio.py` implementa delegando en el cliente de `padron`.
- **Convenio de adhesión** versionado, con evidencia (versión, fecha, IP). Sin convenio no hay
  alta. La **baja definitiva** usa la doble conformidad del PASO 05 (no se reimplementó).

### Sucursales con PostGIS (§06.3)

- Columna `geography(Point, 4326)` con **índice GiST**; consulta de cercanía con `ST_DWithin`
  + orden por `ST_Distance` (metros). El **pin en el mapa es obligatorio**.
- Horarios con **doble turno** por día y consulta "¿abierto ahora?" que respeta la zona horaria
  de configuración. **QR de establecimiento**: token firmado (HMAC) permanente por sucursal, con
  PDF imprimible (reportlab).

### Usuarios, cajero y turnos (§06.4-06.5)

- Cuatro roles (`ADMIN_COMERCIO`, `ADMIN_SUCURSALES`, `ENCARGADO`, `CAJERO`) con **matriz
  declarativa** (mismo mecanismo que gobierno) y alcance por sucursal. `ADMIN_COMERCIO` exige
  MFA (se aplica en `cambiar_perfil` por el rol del perfil de comercio). Invitación con
  vencimiento a 72 h.
- **Cajero por PIN** atado a un dispositivo registrado (reusa la huella del PASO 04), con límite
  de intentos y bloqueo temporal. Dar de baja a un cajero **revoca sus sesiones al instante**.
- **Ningún rol de comercio ve datos de contacto, domicilio ni estado fiscal del ciudadano**
  (test que recorre los endpoints del módulo).

### Deuda del PASO 05 saldada (§06.0)

- **A — Cliente de API generado:** `schema.generated.ts` se genera desde el OpenAPI del backend
  (`uv run python -m tarjeta.scripts.dump_openapi` → `pnpm generate:api`). El CI regenera ambos
  y **falla si quedaron desactualizados**, para que backend y frontend no diverjan en silencio.
- **B — `agente_municipal` sincronizado por evento:** `identidad` es dueña del hecho "tiene
  perfil municipal"; `gobierno` del rol. Al revocarse el perfil (evento
  `PerfilMunicipalRevocado`), `gobierno` **desactiva** al agente (`activo=false`), que pierde el
  acceso sin intervención manual (test).
- **C — Excepción del SQL de reportes:** la métrica de recaudación de `gobierno` lee tablas de
  otros módulos. Se acepta **solo para lectura/reportes** y se encapsula en **vistas de base**
  (`vista_recaudacion_*`, creadas por migración): si otro módulo cambia su esquema, la vista
  rompe de forma ruidosa. **Ninguna escritura cruza módulos por SQL.**

## Walking skeleton (estado actual, PASO 01)

La línea fina que atraviesa todas las capas está implementada y verificada:

- `GET /health` → `{"status": "ok"}`
- `GET /health/db` → ejecuta `uuidv7()` y devuelve el UUID + la versión del servidor
  (PostgreSQL 18.6), pasando por api → sesión async → base.
- Alembic con la migración `0001_extensions`.
- Sin lógica de negocio: el primer módulo real (`identidad`) es el PASO 03.
