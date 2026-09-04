# PASO 12 — Informe de cierre (auditoría y corrección)

PASO sin funcionalidad nueva: corregir desvíos, quitar integraciones falsas y documentar el
estado real. Todo entró en PRs chicos (uno por bloque), en orden de prioridad, con CI verde.

**Estado:** completado salvo **P1-A** (sesión web con cookie HttpOnly), que se deja como
**decisión humana** por su alcance transversal (ver al final). El informe de auditoría vivo está en
[`docs/auditoria-12.md`](auditoria-12.md); la matriz funcional en
[`docs/estado-funcional.md`](estado-funcional.md).

## PRs del PASO 12

| PR | Bloque |
|---|---|
| #17 | Auditoría: informe P0–P3 + matriz funcional + docs alineadas a v2.3 |
| #18 | P0: RENAPER fuera del código + guardas de arranque en prod |
| #19 | Regla de negocio §12.1: comercio validado en todos los caminos (BR-1..BR-5) |
| #20 | P0-A: el cliente no reintenta mutaciones (+ infra de tests de frontend) |
| #21 | P0-B: el QR se renderiza como código escaneable |
| #22 | P1-C middleware centralizado + P1-D health sin fingerprinting |
| #23 | P1-E: IDOR de escritura entre comercios (confirmar/anular) + auditoría |
| #24 | P2-C (web): manejo de errores por código |
| #25 | P2-C/P2-B (móvil): errores por código + no más datos de mentira |
| #26 | P2-B (cierre): placeholders honestos |
| #27 | P1-B: almacén seguro para credenciales móviles (seam + migración + tests) |
| #28 | 12.6-C: procedimiento de restauración probado |

## Hallazgos corregidos (cada uno con test)

- **P0-A — reintentos peligrosos.** El cliente ya no reintenta POST/PUT/DELETE (un canje no se
  duplica). Test: `packages/api-client/src/index.test.ts`.
- **P0-B — QR falso.** La tarjeta muestra un QR escaneable (no texto plano), rota cada 45 s.
  Test: `apps/mobile/.../QrToken.test.tsx`.
- **P0-C — RENAPER simulado.** Se quitó del código; `MetodoVerificacion` pasa a `AUTODECLARADA`;
  **migración de datos** `e1f3b9c7a840`. Tests de grep + de registro.
- **P0-D — arranque inseguro.** En prod, la app se niega a arrancar con simulaciones críticas o
  config débil (`validar_arranque`). Tests de arranque.
- **§12.1 — comercio no aprobado.** Filtro por estado del comercio en mapa, feed/motor y operación
  de canje. Tests: `test_regla_negocio.py` (un test por camino).
- **P1-C — middleware.** Política centralizada por espacio de nombres; sin sesión ⇒ login (la API
  valida igual). Test: `apps/web/src/middleware.test.ts`.
- **P1-D — health.** `/health` (liveness) y `/health/ready` (readiness) ya no exponen la versión
  del motor. Tests de integración.
- **P1-E — IDOR entre comercios.** `confirmar`/`anular` no verificaban dueño: un comercio podía
  operar sobre canjes ajenos. Corregido + tests. Resto de la superficie (doble confirmación, doble
  acreditación/consumo, reuso de nonce/refresh, vencimientos) verificada con evidencia.
- **P2-B — datos de mentira.** Fuera "Vecino de ejemplo", PAN realista de portada y "12 beneficios";
  placeholders "En construcción (PASO 02)" ⇒ "Todavía no está disponible".
- **P2-C — errores del frontend.** Clasificador por código en web y móvil: solo el 401 expulsa al
  login; el resto se muestra. **Crítico:** el error al **confirmar un canje** en móvil ya no se
  ignoraba en silencio (corría sin `try/catch`). Tests: `errores.test.ts` (web/móvil),
  `perfil/page.test.tsx`, `tarjeta/page.test.tsx`.
- **P1-B — credenciales móviles.** access/refresh salen de Preferences y pasan por un almacén seguro
  (puerto), con migración transparente de lo ya guardado. Test: `session.test.ts`. *(La elección del
  plugin nativo de Keychain/Keystore queda como decisión — ver abajo.)*
- **12.6-C — restore probado.** Prueba real de `pg_dump`/`pg_restore` con verificación de conteos,
  versión de esquema e inmutabilidad efectiva. Doc: [`docs/restauracion-backup.md`](restauracion-backup.md).

## Decisiones de negocio aplicadas (v2.3)

- Adhesión ciudadana **abierta** (auto-declarada); el **padrón solo fija el nivel** y nunca bloquea
  ni degrada; si el padrón se cae, no se degrada al ciudadano.
- **RENAPER fuera de alcance**; verificación obligatoria **solo para comercios**.
- Distinción explícita solicitar / aprobar / publicar; solo comercios **habilitados** operan.
- Flags que quedan **apagadas** y sin camino expuesto: `ff_canje_contra_tasas`,
  `ff_exigir_identidad_verificada`.

## Migraciones creadas

- `e1f3b9c7a840_metodo_verificacion_autodeclarada.py` — `UPDATE persona SET metodo_verificacion=
  'AUTODECLARADA' WHERE metodo_verificacion='RENAPER'`. (No se borró ninguna migración aplicada.)

## Resultados de tests (exactos, en `main`)

- **Backend:** ruff ✅ · ruff format ✅ · mypy ✅ · import-linter 3/3 ✅ · **pytest 294 passed**.
- **Frontend:** web **37** · móvil **20** · api-client **5** (vitest). typecheck/lint/build ✅ en
  web y móvil. Cliente OpenAPI regenerado y determinista (freshness gate).
- **Restore:** restauración sin errores; 46 tablas y conteos idénticos; `alembic_version`
  `e1f3b9c7a840`; `UPDATE` de `tarjeta_app` sobre `registro_auditoria` ⇒ *permission denied*.

## Pendientes / riesgos que requieren decisión humana

1. **P1-A — sesión web con cookie HttpOnly (seguridad).** Hoy el refresh vive en `localStorage`
   (robable por XSS). Llevarlo a cookie `HttpOnly`/`Secure`/`SameSite` es un cambio **transversal**
   (backend: login/mfa/refresh/logout/activar-perfil; cliente; web: `api.ts`/`session.ts`/
   middleware) con **decisiones de diseño**: (a) cookie HttpOnly para web vs. cuerpo para móvil
   (que usa almacén seguro nativo); (b) estrategia CSRF (SameSite=Strict en la cookie de refresh, o
   token anti-CSRF); (c) refresh silencioso al cargar la web. Por su alcance se dejó como decisión
   (evitar refactor de medio módulo sin acuerdo). **Recomendación:** cookie de refresh
   `HttpOnly; Secure; SameSite=Strict`, access token en memoria (no `localStorage`), refresh
   silencioso al montar; el resto de endpoints siguen con `Authorization: Bearer` (inmunes a CSRF).
2. **Plugin nativo de almacén seguro (P1-B).** El seam y la migración están listos y testeados;
   falta elegir/cablear el plugin de Keychain/Keystore (Capacitor 8) en el bootstrap nativo.
3. **Proveedores reales** (padrón, notificaciones, imágenes IA): sin elegir; las guardas de prod
   bloquean el arranque hasta configurarlos.
4. **Canal de notificaciones:** no existe (ni push/SMS/email real). Define qué se puede prometer al
   lanzar. Detalle en `estado-funcional.md`.
5. **Tiles del mapa:** bloqueante de lanzamiento sin responsable.
6. **Backup en producción:** repetir la prueba contra la infraestructura real y, sobre todo,
   respaldar la **clave de cifrado de campos** (sin ella el DNI/CUIL es irrecuperable).
