# Restauración de backup (§12.6-C)

> Un backup no probado no es un backup. Este procedimiento **se probó de punta a punta**
> (ver "Prueba realizada" al final) restaurando una copia en una base separada y verificando
> integridad, versión de esquema e **inmutabilidad** de la auditoría/libro contable.

## Qué se respalda (y qué no)

| Elemento | Herramienta | Nota |
|---|---|---|
| Datos + esquema de `tarjeta` | `pg_dump -Fc` | Incluye GRANT/REVOKE (privilegios de `tarjeta_app`). |
| Roles del clúster (`tarjeta_app`, `tarjeta_migrator`) | `pg_dumpall --roles-only` | Los roles son a nivel clúster, no van en el dump de una base. |
| **Clave de cifrado de campos (DNI/CUIL)** | Gestor de secretos | **No está en la base.** Sin ella, las columnas cifradas (AES-GCM) son **irrecuperables**. Hay que respaldarla aparte y en forma segura. |
| Redis | — | Efímero (nonces de QR, códigos de 6 dígitos, rate-limits). **No es objetivo de backup**: se reconstruye solo. |

Puntos críticos:

- **La clave de cifrado es tan importante como el dump.** Un dump restaurado sin la clave deja el
  DNI/CUIL ilegibles para siempre. Guardar la clave en el gestor de secretos con su propia copia.
- El **rol de restore debe ser superusuario** (o equivalente): el dump crea la extensión `postgis`,
  que exige superusuario. El runtime (`tarjeta_app`) y el migrador (`tarjeta_migrator`) **no** deben
  usarse para restaurar.

## Backup

```bash
# 1) Roles del clúster (una vez por clúster; cámbialos poco).
pg_dumpall --roles-only -f roles.sql

# 2) Base completa en formato custom (comprimido, restaurable selectivamente).
pg_dump -Fc -d "$TARJETA_DB_ADMIN_URL" -f tarjeta_$(date +%Y%m%d_%H%M).dump

# 3) Clave de cifrado de campos: exportarla del gestor de secretos y guardarla APARTE.
#    (No vive en la base; sin ella el DNI/CUIL no se puede descifrar.)
```

`TARJETA_DB_ADMIN_URL` es una conexión con privilegios de administración (dueño del esquema o
superusuario), no la de runtime.

## Restauración

```bash
# 1) (Clúster nuevo) recrear los roles primero.
psql -d postgres -f roles.sql

# 2) Crear la base destino, propiedad del migrador.
createdb -O tarjeta_migrator tarjeta

# 3) Restaurar como SUPERUSUARIO (crea extensiones y respeta dueños/privilegios).
pg_restore --exit-on-error -d tarjeta tarjeta_YYYYMMDD_HHMM.dump

# 4) Volver a inyectar la clave de cifrado en el gestor de secretos del entorno.
```

## Verificación post-restore (checklist)

```bash
# a) Nº de tablas y filas clave coinciden con el origen.
psql -d tarjeta -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
psql -d tarjeta -tAc "SELECT count(*) FROM persona;"

# b) La versión de esquema (Alembic) es la esperada.
psql -d tarjeta -tAc "SELECT version_num FROM alembic_version;"

# c) La inmutabilidad sobrevivió: tarjeta_app solo tiene INSERT/SELECT en las tablas append-only.
psql -d tarjeta -tAc "SELECT table_name, string_agg(privilege_type, ',' ORDER BY privilege_type) \
  FROM information_schema.role_table_grants \
  WHERE grantee='tarjeta_app' AND table_name IN ('registro_auditoria','movimiento_billetera') \
  GROUP BY table_name;"

# d) Prueba EFECTIVA de inmutabilidad: un UPDATE del runtime sobre la auditoría debe fallar.
psql -d tarjeta -U tarjeta_app -h localhost -c "UPDATE registro_auditoria SET id=id;"
#   -> se espera: ERROR: permission denied for table registro_auditoria
```

## Prueba realizada

- **Fecha:** 2026-09-04. **Motor:** PostgreSQL 18 (local, camino A).
- **Método:** `pg_dump -Fc` de `tarjeta` → `createdb -O tarjeta_migrator tarjeta_restore_test` →
  `pg_restore --exit-on-error` como superusuario → verificación → limpieza de la base scratch.
- **Resultado:**
  - Restore sin errores.
  - Tablas: **46** (origen) = **46** (restaurada).
  - `persona`: **1110** = **1110**. `registro_auditoria`: **18978** = **18978**.
  - `alembic_version`: **e1f3b9c7a840** en ambas.
  - Privilegios de `tarjeta_app` sobre `registro_auditoria` y `movimiento_billetera`:
    **INSERT,SELECT** (sin UPDATE/DELETE) — preservados.
  - Prueba efectiva: `UPDATE registro_auditoria` como `tarjeta_app` → **permission denied**.
  - Extensiones restauradas: `btree_gist pg_trgm pgcrypto plpgsql postgis unaccent`.

## Riesgos / decisiones pendientes (producción)

- Este ensayo corrió contra el PostgreSQL local. **Falta repetirlo contra la infraestructura real
  de producción** (backups automáticos, retención, almacenamiento off-site, cifrado del backup).
- Definir **RPO/RTO** y la cadencia de backups (y de pruebas de restore periódicas).
- Definir el respaldo y la rotación de la **clave de cifrado de campos** — es la dependencia más
  frágil de todo el plan de recuperación.
