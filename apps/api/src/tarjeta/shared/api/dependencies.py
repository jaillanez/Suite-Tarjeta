"""Dependencias reutilizables de FastAPI (composition root del lado HTTP)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.config import Settings, get_settings
from tarjeta.shared.infrastructure.database import session_scope

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(session_scope)]
