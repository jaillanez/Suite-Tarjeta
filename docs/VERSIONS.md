# Versiones fijadas — suite-tarjeta

Última verificación: **2026-09-02**

> **Estado del PASO 00: COMPLETO.** Todos los criterios de aceptación cumplidos.
> Python 3.14.7 gestionado por uv; PostgreSQL 18.6 con `uuidv7()` nativo y las cinco
> extensiones disponibles; librerías backend instaladas desde ruedas binarias en 3.14.7
> con conexión real verificada. Pendientes solo del toolchain móvil (no bloquean 01–03).

## Entorno base
| Componente | Versión | Comando de verificación | Notas |
|---|---|---|---|
| Sistema operativo | macOS 15.3 (24D60), arm64 | `sw_vers` / `uname -a` | Apple Silicon (T6000) |
| Git | 2.39.5 (Apple Git-154) | `git --version` | OK |

## Base de datos
| Componente | Versión | Notas |
|---|---|---|
| PostgreSQL servidor | **18.6** (Homebrew) | `SHOW server_version;` → 18.6. |
| PostgreSQL cliente (`psql`) | **18.6** | Alineado con el servidor tras el upgrade. |
| `uuidv7()` nativo | ✅ | Devuelve UUID en 18.6. No usar extensión de terceros. |
| PostGIS | ✅ **3.6.4** | `pg_available_extensions`. Homebrew la trae compilada contra PG18. |
| pgcrypto | ✅ 1.4 | disponible |
| pg_trgm | ✅ 1.6 | disponible |
| btree_gist | ✅ 1.8 | disponible |
| unaccent | ✅ 1.1 | disponible |

## Backend
| Componente | Versión | ¿Rueda binaria? | Notas |
|---|---|---|---|
| Python | **3.14.7** | — | Gestionado por uv (`~/.local/share/uv/python/cpython-3.14.7`). |
| uv | 0.12.9 | — | Actualizado desde 0.11.7 para poder resolver 3.14.7. |
| SQLAlchemy | 2.0.52 | ✅ sí | Importa OK en 3.14.7. |
| psycopg | 3.3.5 (+ `psycopg-binary` 3.3.5, `psycopg-pool` 3.3.1) | ✅ sí | Conexión real a PG 18.6 verificada. |
| Pydantic | 2.13.5 (`pydantic-core` 2.46.5) | ✅ sí | Sin DeprecationWarning de anotaciones (PEP 649). |
| Alembic | 1.19.1 | ✅ sí | Importa OK. |
| FastAPI | **0.141.1** | ✅ sí | Fijada en PASO 01. Starlette 1.6.0. |
| uvicorn[standard] | **0.52.4** | ✅ sí | uvloop 0.22.1, watchfiles 1.2.0, websockets 17.1. |
| pydantic-settings | **2.15.0** | ✅ sí | — |
| redis | **8.1.0** | ✅ sí | Cliente Python. |
| httpx | **0.28.1** | ✅ sí | Cliente HTTP (padrón, tests). |
| greenlet | 3.5.5 | ✅ sí | Requerido por SQLAlchemy async (extra `[asyncio]`). |

> Prueba 00.6: `uv pip install` resolvió e instaló 14 paquetes en 44 ms **sin compilar
> desde fuente** (todas ruedas para cp314). Sin advertencias relacionadas con anotaciones.
>
> PASO 01: todas las dependencias del backend (prod y dev) resolvieron como **ruedas
> binarias** para cp314 — ninguna compila desde fuente. Dev: ruff 0.16.5, mypy 2.3.1,
> pytest 9.1.1, pytest-asyncio 1.4.0, testcontainers 4.15.0, import-linter 2.14.

## Integración continua (PASO 01-bis)
| Tema | Definición |
|---|---|
| Runner | `ubuntu-latest` (GitHub Actions) |
| Imagen del service container | **`postgis/postgis:18-3.6`** (verificada en Docker Hub, actualizada 2026-08-31). PostgreSQL 18 + PostGIS 3.6. |
| Workflow backend | `.github/workflows/api.yml`: ruff, ruff format, mypy `src`, import-linter, alembic, pytest + cobertura. El job **falla si el test de integración se saltea**. |
| Workflow web | `.github/workflows/web.yml`: placeholder (se completa en PASO 02). |
| Dependabot | `uv`, `npm`, `github-actions`, semanal. |
| Rama `main` | Protegida: requiere el check `api`, exige PR, sin force push. |
| Cobertura backend | ~60% (walking skeleton). |

> Nota: `actions/checkout@v4` y `astral-sh/setup-uv@v6` emiten un warning de Node 20
> deprecado (corren forzados en Node 24). Dependabot los actualizará.

## Base de datos de desarrollo (PASO 01)
| Tema | Definición |
|---|---|
| Camino elegido | **A — PostgreSQL nativo de Homebrew** (ya verificado en PASO 00). Redis nativo de Homebrew. |
| Rol runtime | `tarjeta_app` (LOGIN, sin DDL). `CREATE TABLE` como este rol da *permission denied* (verificado). |
| Rol migraciones | `tarjeta_migrator` (dueño del esquema, corre Alembic). |
| Base | `tarjeta`, OWNER `tarjeta_migrator`, con las 5 extensiones (PostGIS 3.6.4). |
| Redis | Homebrew, `redis-cli ping` → PONG. |
| Docker | OrbStack (runtime del `docker` CLI). Usado por `testcontainers` en el test de integración. |

## Frontend (PASO 02)
| Componente | Versión | Notas |
|---|---|---|
| Node.js | 22.18.0 | Línea 22 LTS (aceptada por Next 16, que exige ≥20). |
| pnpm | 10.28.2 | vía corepack; `packageManager` en package.json |
| Next.js | **16.3.4** | LTS activa (≥16.3.3, incluye fix de seguridad 25/08/2026). |
| React / React DOM | **19.2.8** | Requerido por Next 16. |
| TypeScript | **5.9.3** | TS 7.0.2 es latest y Next 16 lo aceptaría, pero `typescript-eslint` exige `<6.1.0`; se fija 5.9.3 (compatible con todo el tooling). |
| Tailwind CSS | **4.3.3** | Config en CSS (`@theme`), sin `tailwind.config.js`. + `@tailwindcss/postcss` 4.3.3, `tw-animate-css` 1.4.0. |
| shadcn/ui | CLI `new-york`, base neutral | 16 componentes en `packages/ui`. |
| ESLint / eslint-config-next / typescript-eslint | 9.39.5 / 16.3.4 / 8.69.0 | jsx-a11y 6.10.2 (modo error). Prettier 3.9.6. |
| openapi-typescript | **7.13.0** | Genera el cliente desde OpenAPI **3.1** de FastAPI. |
| Capacitor (core/cli/android/ios) | **8.5.1** | Plugins (peer core ≥8): geolocation 8.2.2, push-notifications 8.1.2, preferences 8.0.1, network 8.0.1, app 8.1.1, @capacitor-mlkit/barcode-scanning 8.1.1. |
| Otros UI | cva 0.7.1, clsx 2.1.1, tailwind-merge 3.6.0, lucide-react 1.40.0, radix-ui 1.6.7, next-themes 0.4.6, sonner 2.0.8, react-hook-form 7.87.0, zod 4.5.4 | Fijadas exactas. |

> Piso de navegador (Tailwind 4): Safari/iOS 16.4+, Chrome/WebView 111+, Firefox 128+, Edge 111+.
> Ver `docs/arquitectura.md`. La caja debe probarse en gama baja antes del PASO 06.

## CI (actualizado en PASO 02)
| Tema | Definición |
|---|---|
| Workflow único | `.github/workflows/ci.yml` con jobs `changes` → `api`/`web` → `ci-ok`. Sin filtro de paths en el trigger; `changes` (dorny/paths-filter) decide qué corre. |
| Check obligatorio de `main` | **`ci-ok`** (reemplaza a `api`). Un PR de solo docs pasa sin override de admin. |
| Job web | pnpm install (frozen), lint, build web + mobile, typecheck. |

## Móvil
| Componente | Versión | Notas |
|---|---|---|
| @capacitor/core | **8.5.1** | Última estable de la serie 8.5.x (8.5.2 solo nightly). No subir a 9.x (alpha). Fijar en PASO 04. |
| @capacitor/cli | 8.5.1 | — |
| @capacitor/android | 8.5.1 | — |
| @capacitor/ios | 8.5.1 | SPM por defecto desde Capacitor 8. |
| JDK | 17.0.14 (JBR) | Runtime de JetBrains. Para build Android usar un JDK estándar (17/21). |
| Android SDK | ⏸️ `ANDROID_HOME` vacío | Pendiente. No bloquea pasos 01–03. |
| Xcode | ⏸️ no disponible | `xcodebuild` no responde. Capacitor 8.5 requiere UIScene con Xcode 27. Pendiente. No bloquea 01–03. |

## Criterios de aceptación del PASO 00
- [x] Python 3.14.7 disponible (vía uv) e imprime exactamente `Python 3.14.7`
- [x] Servidor PostgreSQL 18.6
- [x] `SELECT uuidv7()` devuelve un UUID
- [x] Las cinco extensiones (postgis, pgcrypto, pg_trgm, btree_gist, unaccent) disponibles
- [x] Node y pnpm registrados
- [x] Versión exacta de Capacitor 8.5.x identificada (8.5.1)
- [x] SQLAlchemy, psycopg, Pydantic y Alembic instalan e importan en 3.14.7
- [x] Conexión psycopg contra PostgreSQL 18.6 funciona
- [x] Repositorio git inicializado (este repo)
- [x] `docs/VERSIONS.md` completo
- [x] `docs/especificacion.md` con el documento funcional v2.0

## Pendientes (no bloquean PASO 01–03)
1. **Toolchain móvil**: Android SDK (`ANDROID_HOME`) y Xcode sin configurar. Se resuelven
   antes del PASO 04 (móvil). Para Android, además, usar un JDK estándar en vez del JBR.
2. **Node**: confirmar si se fija la línea 22.x o se adopta la LTS activa actual (decisión de PASO 02).
3. **Rol de BD**: resuelto en PASO 01 (`tarjeta_app` / `tarjeta_migrator`).
4. **Test de integración con testcontainers**: escrito y correcto, pero en esta máquina
   OrbStack **no logra descargar imágenes** (pulls colgados vía su proxy interno; incluso
   `alpine` no baja). El test se saltea limpio si la imagen no está local. El mismo camino
   api → sesión async → base se verificó **en vivo contra el PostgreSQL 18.6 nativo**
   (`GET /health/db` devuelve `uuidv7()` + "PostgreSQL 18.6"). Para correr el de
   testcontainers, una vez que Docker pueda bajar imágenes: `docker pull postgres:18.6`.

## Estructura del proyecto (nota)
El documento del PASO 00 planteaba `mkdir suite-tarjeta && git init`. Como este repositorio
(`Suite-Tarjeta/`) ya estaba inicializado y sincronizado con GitHub, se usa **este repo como
raíz del proyecto** en lugar de anidar otro repositorio.
