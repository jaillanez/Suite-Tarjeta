# PASO 14 — Informe de cierre (correcciones del PASO 13)

**Estado:** completado en lo que es código y datos. Lo que no puede hacer el agente quedó listado
(§14.3) con su responsable, y la decisión sobre iOS quedó registrada.

## PRs

| PR | Bloque |
|---|---|
| #44 | 14.1 guarda de tiles: fallar cerrado en producción |
| #45 | 14.2 comercios reales de Rivadavia (OpenStreetMap) |
| (este) | 14.3 lista de lo que no puede el agente + decisión de iOS |

## 14.1 — Tiles fail-closed

En producción, sin `NEXT_PUBLIC_TILES_URL` propia, el mapa **no carga** (avisa) y **no** cae al OSM
público. En desarrollo sigue usando OSM público sin configurar nada. La distinción es por entorno de
compilación (`NODE_ENV`), no por una bandera olvidable. `apps/web/src/lib/tiles.ts` (`resolverTiles`)
con **test de las dos ramas**. Matriz y nota de seguridad actualizadas.

## 14.2 — Comercios reales

- **36 comercios reales** de Rivadavia (San Juan), en **13 rubros**, repartidos por zona.
- **Fuente:** **OpenStreetMap** (Overpass), relevado 2026-09-05. Se registró el nodo OSM + la fecha
  en el campo `origen` de cada uno.
- **Real:** nombre, rubro y **coordenadas**; **teléfono real en 3** (los que OSM tenía); **dirección
  de calle en 3** (idem). Las coordenadas son reales en los 36.
- **Estimado (marcado):** **las 36 promociones son estimadas** (representativas del rubro), marcadas
  como tales en `origen`. El CUIT es inventado con formato válido; los horarios son un patrón estándar.
- **Lo que no se pudo relevar:** las **promociones reales** de las redes/Google Maps de cada
  comercio — `WebSearch` (US-only) da datos sueltos, el directorio local devuelve 403 a `WebFetch`,
  e Instagram/Maps requieren login. Por eso se usó OSM (fuente web con datos estructurados y
  coordenadas reales) y las promos quedan estimadas hasta que el promotor las confirme.
- `datos/padron.yaml` marca esos CUIT como inscriptos. Carga y baja en bloque siguen idempotentes.

## 14.3 — Lo que no puede hacer el agente

Listado en `docs/lista-para-lanzar.md` (sección 6) con su responsable: compilar APK/AAB, probar en
teléfono real, confirmar el almacén seguro en dispositivo, compilar iOS, revisión legal, y cuentas
de tiendas.

**Decisión de iOS (registrada):** **iOS entra en el lanzamiento inicial, junto con Android.** Queda
pendiente compilarlo en una Mac con Xcode 27 (`docs/apps-build.md`).

**Almacén seguro:** sigue **parcial** en la matriz (solo se verifica en dispositivo); nunca como
resuelto hasta confirmarlo.

## Resumen para el informe

- **36** comercios reales cargados, fuente **OpenStreetMap**.
- **0 promociones reales / 36 estimadas** (marcadas), por no poder acceder a las redes/Maps de cada
  comercio con las herramientas disponibles.
- **Quedó sin relevar:** promos reales, y la mayoría de teléfonos/direcciones de calle (OSM no los
  tenía); las coordenadas sí son reales en todos.
