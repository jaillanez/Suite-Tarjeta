-- Extensiones requeridas por el proyecto.
-- En el camino B (PostgreSQL en Docker) este archivo se ejecuta automáticamente
-- vía /docker-entrypoint-initdb.d en el primer arranque del contenedor.
-- En el camino A (nativo) las extensiones se crean como superusuario en el alta
-- de la base (ver docs/VERSIONS.md / PASO 01).
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS unaccent;
