"""Entorno de Alembic.

Corre con el rol `tarjeta_migrator` (dueño del esquema), nunca con el rol de la app.
La URL sale de la configuración, no del alembic.ini.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from tarjeta.config import get_settings
from tarjeta.modules.canje.infrastructure import models as _canje_models  # noqa: F401
from tarjeta.modules.ciudadania.infrastructure import models as _ciudadania_models  # noqa: F401
from tarjeta.modules.comercios.infrastructure import models as _comercios_models  # noqa: F401
from tarjeta.modules.gobierno.infrastructure import models as _gobierno_models  # noqa: F401
from tarjeta.modules.identidad.infrastructure import models as _identidad_models  # noqa: F401
from tarjeta.modules.padron.infrastructure import models as _padron_models  # noqa: F401
from tarjeta.modules.promociones.infrastructure import models as _promociones_models  # noqa: F401
from tarjeta.shared.infrastructure import outbox as _shared_outbox  # noqa: F401
from tarjeta.shared.infrastructure.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
migrator_url = str(get_settings().database_migrator_url)


def run_migrations_offline() -> None:
    context.configure(
        url=migrator_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(migrator_url, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
