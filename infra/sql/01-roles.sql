-- Rol de runtime con privilegios mínimos (sin DDL), separado del dueño del esquema.
-- Reproduce el esquema de dos roles de producción (tarjeta_migrator = dueño / Alembic,
-- tarjeta_app = runtime de la API). Se ejecuta COMO EL DUEÑO del esquema, antes de las
-- migraciones, para que las DEFAULT PRIVILEGES apliquen a las tablas que cree Alembic.
--
-- En CI el dueño/migrador es el rol `tarjeta`; en local es `tarjeta_migrator`. Este archivo
-- solo crea y habilita `tarjeta_app`; las DEFAULT PRIVILEGES se cuelgan del rol que ejecuta
-- el script (ALTER DEFAULT PRIVILEGES sin FOR ROLE aplica al rol actual).

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tarjeta_app') THEN
        CREATE ROLE tarjeta_app LOGIN PASSWORD 'tarjeta_app';
    END IF;
END$$;

GRANT USAGE ON SCHEMA public TO tarjeta_app;

-- Toda tabla/secuencia que cree el rol actual (dueño/migrador) otorga automáticamente el
-- acceso de runtime a tarjeta_app. La migración de gobierno revoca UPDATE/DELETE sobre
-- registro_auditoria para dejar la auditoría inmutable (append-only) a nivel motor.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tarjeta_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO tarjeta_app;
