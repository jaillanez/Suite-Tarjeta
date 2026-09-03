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
| `gobierno` | Parametro, RegistroAuditoria | Parametría, auditoría inmutable, tablero |

### Invariantes que quedan imposibles de violar por construcción

- `puntos`: `MovimientoBilletera` no expone métodos de actualización ni borrado.
- `gobierno`: `RegistroAuditoria` es append-only, incluso para el superadministrador.
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
estado. Un consumidor mínimo los escribe al log estructurado; el consumidor de auditoría
inmutable llega con el módulo `gobierno`.

### Frontend

- `apps/web`: registro (con consentimientos separados), login con MFA, selector de perfil,
  perfil con dispositivos y cierre remoto. **Middleware real** que protege las rutas de
  comercio y municipio (cookie de presencia de sesión; la validez la valida la API).
- `apps/mobile`: login y selector de perfil; el perfil activo y los tokens se persisten con
  el plugin **Preferences** de Capacitor. Sin middleware (protección del lado del cliente +
  validación en la API).

## Walking skeleton (estado actual, PASO 01)

La línea fina que atraviesa todas las capas está implementada y verificada:

- `GET /health` → `{"status": "ok"}`
- `GET /health/db` → ejecuta `uuidv7()` y devuelve el UUID + la versión del servidor
  (PostgreSQL 18.6), pasando por api → sesión async → base.
- Alembic con la migración `0001_extensions`.
- Sin lógica de negocio: el primer módulo real (`identidad`) es el PASO 03.
