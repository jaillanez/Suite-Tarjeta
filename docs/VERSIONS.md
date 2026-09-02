# Versiones fijadas — suite-tarjeta

Última verificación: **2026-09-02**

> **Estado del PASO 00: INCOMPLETO.** Hay 3 acciones de instalación pendientes que
> requieren ejecución en terminal por el usuario (Python 3.14.7, PostgreSQL 18.6,
> PostGIS) y la prueba de compatibilidad 00.6, que depende de ellas. Ver
> "Incompatibilidades y pendientes detectados".

## Entorno base
| Componente | Versión | Comando de verificación | Notas |
|---|---|---|---|
| Sistema operativo | macOS 15.3 (24D60), arm64 | `sw_vers` / `uname -a` | Apple Silicon (T6000) |
| Git | 2.39.5 (Apple Git-154) | `git --version` | OK |

## Base de datos
| Componente | Versión | Notas |
|---|---|---|
| PostgreSQL servidor (corriendo) | **18.3** (Homebrew) | ⚠️ Objetivo 18.6. Homebrew ya ofrece 18.6 (`brew upgrade postgresql@18`). |
| PostgreSQL cliente (`psql` en PATH) | 18.1 (libpq keg) | ⚠️ Segundo cliente conviviendo. Tras el upgrade, alinear el PATH. |
| `uuidv7()` nativo | ✅ disponible en 18.3 | Devuelve UUID. No instalar extensión de terceros. |
| PostGIS | ❌ **no disponible** | No figura en `pg_available_extensions`. Instalar (`brew install postgis`) y verificar versión compatible con PG18. |
| pgcrypto | ✅ 1.4 | disponible |
| pg_trgm | ✅ 1.6 | disponible |
| btree_gist | ✅ 1.8 | disponible |
| unaccent | ✅ 1.1 | disponible |

## Backend
| Componente | Versión | ¿Rueda binaria? | Notas |
|---|---|---|---|
| Python (objetivo) | **3.14.7** | — | ❌ No instalado. Ver pendiente. |
| Python (instalado) | 3.14.5 (Homebrew) / 3.13.5 (sistema) | — | `python3.14` = 3.14.5; `python3` = 3.13.5. |
| uv | 0.11.7 (2026-04-15) | — | ⚠️ Su índice solo llega a 3.14.4 descargable; **no lista 3.14.6/3.14.7**. Requiere `uv self update`. |
| SQLAlchemy | (sin verificar) | | Bloqueado hasta tener 3.14.7 (paso 00.6). |
| psycopg | (sin verificar) | | Idem. |
| Pydantic | (sin verificar) | | Idem. |
| Alembic | (sin verificar) | | Idem. |
| Framework web | (sin definir) | | Se decide en PASO 01. |

## Frontend
| Componente | Versión | Notas |
|---|---|---|
| Node.js | 22.18.0 | Línea 22 LTS. Confirmar si se adopta la LTS activa actual o se fija la 22.x. |
| npm | 11.5.2 | — |
| pnpm | 10.28.2 | vía corepack (0.33.0) |
| Next.js / React / Tailwind / shadcn/ui | (sin definir) | Se fijan en PASO 02 |

## Móvil
| Componente | Versión | Notas |
|---|---|---|
| @capacitor/core | **8.5.1** (a fijar) | Última estable de la serie 8.5.x (8.5.2 solo nightly). No subir a 9.x (alpha). |
| @capacitor/cli | 8.5.1 | — |
| @capacitor/android | 8.5.1 | — |
| @capacitor/ios | 8.5.1 | SPM por defecto desde Capacitor 8. |
| JDK | 17.0.14 (JBR) | Es el runtime de JetBrains. Para build Android conviene un JDK estándar (17/21). |
| Android SDK | ❌ `ANDROID_HOME` vacío | Pendiente. No bloquea pasos 01–03. |
| Xcode | ❌ no disponible | `xcodebuild` no responde. Capacitor 8.5 requiere UIScene con Xcode 27. Pendiente. No bloquea 01–03. |

## Incompatibilidades y pendientes detectados

1. **Python 3.14.7 no instalable con el uv actual.** El índice de uv 0.11.7 (abr-2026)
   solo ofrece hasta 3.14.4 descargable; 3.14.6/3.14.7 no aparecen. Acción propuesta:
   `uv self update` y reintentar `uv python install 3.14.7`. Si tras actualizar uv la
   versión sigue sin existir en el índice → **detener y reportar** (Regla 1), no sustituir.
2. **PostgreSQL servidor en 18.3, objetivo 18.6.** Homebrew ya tiene 18.6 bottled.
   Acción: `brew upgrade postgresql@18` + reinicio del servicio, luego reverificar
   `SHOW server_version;`.
3. **Dos clientes psql** (18.1 libpq + 18.3 postgresql@18). Resolver precedencia de PATH
   tras el upgrade para que cliente y servidor coincidan en 18.6.
4. **PostGIS ausente.** Instalar y registrar la versión exacta, confirmando compatibilidad
   con PG18 antes de asumir nada.
5. **Rol `postgres` inexistente.** El superusuario del server Homebrew es el usuario del SO
   (`Jorge`), no `postgres`. Las verificaciones se corrieron con `psql -d postgres`. Decidir
   en PASO 01 si se crea un rol `postgres`/rol de aplicación dedicado.
6. **00.6 (compatibilidad SQLAlchemy/psycopg/Pydantic/Alembic en 3.14.7) pendiente**,
   bloqueada por el pendiente 1.
7. **Toolchain móvil incompleto** (Android SDK, Xcode). No bloquea backend/web (pasos 01–03).
