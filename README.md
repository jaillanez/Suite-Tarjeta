# Suite Tarjeta — Tarjeta de Beneficios Municipal (Rivadavia)

Plataforma de **tarjeta de beneficios municipal** para el municipio de Rivadavia (San Juan). Conecta a **vecinos**, **comercios** y **el municipio** en un único sistema de descuentos, puntos y campañas, con el objetivo de fomentar el consumo local y **premiar al contribuyente al día**.

> 📄 Especificación funcional completa: [`docs/especificacion.md`](docs/especificacion.md) — es la fuente de verdad del producto.
> 🔧 Versiones fijadas del entorno: [`docs/VERSIONS.md`](docs/VERSIONS.md).

---

## El modelo en una frase

El **comercio absorbe el 100% del descuento** (el municipio no pone caja) y fija libremente el porcentaje. El municipio aporta **alcance, herramientas y visibilidad**, y verifica contra su padrón si una persona es contribuyente y está al día para asignarle un mejor nivel de beneficios.

## Decisiones cerradas (resumen)

| Tema | Definición |
|---|---|
| Financiamiento | El comercio absorbe el 100%; el municipio no aporta caja. |
| Descuento | Lo fija libremente el comercio, sin mínimo ni máximo. |
| Verificación municipal | Endpoint que devuelve: contribuyente sí/no, al día sí/no, comercio inscripto sí/no, fecha de corte. **Sin montos, cuotas ni vencimientos.** |
| Aplicaciones | **Una sola app**, una publicación, tres perfiles (ciudadano, comercio, municipal) + portales web complementarios. |
| Niveles | **General** vs **Black** (Black = contribuyente al día, o heredado por grupo familiar). |
| Puntos | **Puntos Comercio** (circuito cerrado por comercio) y **Puntos Municipales** (contra inventario del municipio). Vencen a 24 meses, consumo FIFO. |

## Perfiles

- **Ciudadano** — tarjeta digital (QR dinámico), descubrimiento de beneficios, mapa, canje, billetera de puntos, grupo familiar.
- **Comercio** — adhesión, sucursales, promociones, generación de creatividades con IA, caja (QR / código de 6 dígitos / navegador), reportes con benchmark de rubro.
- **Municipal** — bandeja de comercios, ficha 360 de ciudadanos y comercios, moderación, campañas, tablero de gobierno, captación de comercios.

## Reglas de negocio (especificación v2.3)

- **Registro ciudadano abierto:** cualquier persona crea cuenta, recibe tarjeta y **canjea**. No
  hace falta figurar en el padrón, estar al día ni verificar identidad. La identidad es
  **autodeclarada** en el alta (**RENAPER está fuera de alcance**).
- **El padrón solo asigna el nivel:** `al_dia = true` habilita Black; cualquier otro resultado
  —o el padrón caído— deja Platino y **nunca bloquea ni degrada** el uso.
- **El comercio sí se valida:** solo un comercio **inscripto y aprobado** aparece en búsquedas y en
  el mapa, publica promociones utilizables, opera canjes y emite puntos. Solicitar ≠ estar publicado.
- Estado real de cada módulo e integraciones pendientes: ver [`docs/estado-funcional.md`](docs/estado-funcional.md).

## Módulos

| Módulo | Descripción |
|---|---|
| M1 · Ciudadano | Registro abierto (identidad autodeclarada), motor de nivel (padrón solo para el nivel), grupo familiar, tarjeta, descubrimiento, canje, billetera. |
| M2 · Comercio | Adhesión, sucursales, usuarios, promociones, creatividades con IA, caja, reportes. |
| M3 · Administrador Municipal | Comercios, ciudadanos, moderación, campañas, parametría, tablero de gobierno. |
| M4 · Redes sociales | Publicación en canales oficiales y propios, cola editorial, métricas. |
| M5 · Endpoint de verificación municipal | Contrato mínimo servidor-a-servidor con el padrón. |
| M6 · Antifraude, seguridad y cumplimiento | Vectores de fraude, motor de alertas, seguridad técnica, Ley 25.326. |
| M7 · Captación de comercios | CRM de captación, promotores, alertas de riesgo de baja. |
| M8 · Notificaciones | Push, email, SMS/WhatsApp con reglas de higiene. |

## Stack técnico sugerido

| Capa | Recomendación |
|---|---|
| Backend | Node.js (NestJS) o .NET 8 |
| Base de datos | PostgreSQL + PostGIS |
| Caché / colas | Redis |
| Almacenamiento | S3 compatible (MinIO / cloud) |
| App única | Flutter o React Native |
| Portales web | React / Next.js |
| Notificaciones | Firebase Cloud Messaging + proveedor SMS/WhatsApp local |

> **Multi-tenant desde el día uno:** incluir `id_municipio` en el modelo de datos desde el inicio, aunque el primer tenant sea solo Rivadavia.

## Roadmap

1. **Fase 1 — Piloto (3-4 meses):** núcleo, identidad, motor de nivel, app ciudadano, app con perfil comercio (caja QR + código 6 dígitos), portales básicos. Solo descuento directo.
2. **Fase 2 — Programa completo (3-4 meses):** puntos, grupo familiar, promociones avanzadas, IA, redes, reportes, tarjeta física, modo offline, tablero de gobierno.
3. **Fase 3 — Escala e integración fiscal (3 meses):** canje contra tasas (sujeto a ordenanza), campañas, inventario municipal, perfil municipal en la app, captación, multi-tenant activo.

## Estructura del repositorio

```
Suite-Tarjeta/
├── apps/
│   ├── api/                 # backend FastAPI (Python 3.14 + SQLAlchemy 2)
│   ├── web/                 # Next.js SSR — público + portales (PASO 02)
│   └── mobile/              # Next.js export + Capacitor (PASO 02)
├── packages/
│   ├── ui/                  # componentes shadcn/ui compartidos (PASO 02)
│   ├── api-client/          # cliente TS generado del OpenAPI (PASO 02)
│   └── config/              # tsconfig/eslint/tailwind compartidos (PASO 02)
├── docs/
│   ├── especificacion.md    # Especificación funcional completa (v2.0)
│   ├── VERSIONS.md          # Versiones fijadas del entorno
│   └── arquitectura.md      # Capas, módulos y reglas de dependencia
├── infra/
│   ├── docker-compose.yml   # PostgreSQL (perfil) + Redis para desarrollo
│   └── sql/00-extensions.sql
├── package.json             # workspace pnpm
├── pnpm-workspace.yaml
├── .editorconfig
├── .gitignore
└── README.md
```

### Correr el backend (desarrollo)

```bash
cd apps/api && cp .env.example .env && uv sync --group dev && uv run alembic upgrade head && uv run uvicorn tarjeta.main:app --reload
```

Salud: `GET http://localhost:8000/health` y `GET /health/db`. Detalle de arquitectura en [`docs/arquitectura.md`](docs/arquitectura.md).

## Estado

📋 **Fase de especificación.** El documento funcional está cerrado (v2.0) con un único pendiente: confirmar con Sistemas del municipio que el endpoint de padrón devuelva **dos booleanos separados** (`es_contribuyente` y `al_dia`).
