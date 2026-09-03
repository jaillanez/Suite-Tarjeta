"""Composición: arma el bundle de puertos con implementaciones concretas."""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.config import Settings
from tarjeta.modules.identidad.application.deps import Puertos
from tarjeta.shared.infrastructure.crypto import FieldCipher
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork

from .adapters import MfaCifrado, TextosLegalesSql
from .argon2_hasher import Argon2Hasher
from .jwt_generador import JwtGenerador
from .otp_consola import OtpConsola
from .outbox_repo import SqlAlchemyOutbox
from .redis_stores import RedisAlmacenOtp, RedisRateLimiter
from .refresh_store import SqlAlchemyAlmacenRefresh
from .renaper_stub import RenaperStub
from .repositories import (
    SqlAlchemyConsentimientoRepository,
    SqlAlchemyCredencialRepository,
    SqlAlchemyDispositivoRepository,
    SqlAlchemyMfaRepository,
    SqlAlchemyPersonaRepository,
)
from .totp_pyotp import TotpPyotp


def construir_puertos(session: AsyncSession, settings: Settings, redis: Redis) -> Puertos:
    cipher = FieldCipher(
        settings.field_encryption_key.get_secret_value(),
        settings.field_encryption_key_version,
    )
    pepper = settings.field_pepper.get_secret_value()
    return Puertos(
        uow=SqlAlchemyUnitOfWork(session),
        personas=SqlAlchemyPersonaRepository(session, cipher=cipher, pepper=pepper),
        credenciales=SqlAlchemyCredencialRepository(session),
        dispositivos=SqlAlchemyDispositivoRepository(session),
        consentimientos=SqlAlchemyConsentimientoRepository(session),
        mfa=MfaCifrado(SqlAlchemyMfaRepository(session), cipher),
        textos=TextosLegalesSql(session),
        outbox=SqlAlchemyOutbox(session),
        hasher=Argon2Hasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
        ),
        totp=TotpPyotp(issuer=settings.mfa_issuer),
        tokens=JwtGenerador(
            secret=settings.jwt_secret.get_secret_value(),
            ttl_seg=settings.jwt_access_ttl_seconds,
        ),
        refresh=SqlAlchemyAlmacenRefresh(session, ttl_seg=settings.refresh_ttl_seconds),
        envio_otp=OtpConsola(environment=settings.environment),
        almacen_otp=RedisAlmacenOtp(redis),
        rate_limiter=RedisRateLimiter(redis),
        verificador=RenaperStub(resultado=settings.renaper_stub_resultado),
        password_min_length=settings.password_min_length,
        otp_length=settings.otp_length,
        otp_ttl_seg=settings.otp_ttl_seconds,
        otp_max_intentos=settings.otp_max_intentos,
        otp_max_solicitudes_hora=settings.otp_max_solicitudes_por_hora,
        rate_limit_login=settings.rate_limit_login_por_minuto,
    )
