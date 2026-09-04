"""Contenedor de puertos y configuración para los casos de uso."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.identidad.domain.ports import (
    AlmacenMfa,
    AlmacenOtp,
    AlmacenRefresh,
    AlmacenReset,
    ConsentimientoRepository,
    CredencialRepository,
    DispositivoRepository,
    EnviarEmail,
    EnvioOtp,
    GeneradorTokenAcceso,
    GeneradorTotp,
    HashDeContrasena,
    Outbox,
    PersonaRepository,
    RateLimiter,
    TextosLegales,
)
from tarjeta.shared.application.unit_of_work import AbstractUnitOfWork


@dataclass(slots=True)
class Puertos:
    uow: AbstractUnitOfWork
    personas: PersonaRepository
    credenciales: CredencialRepository
    dispositivos: DispositivoRepository
    consentimientos: ConsentimientoRepository
    mfa: AlmacenMfa
    textos: TextosLegales
    outbox: Outbox
    hasher: HashDeContrasena
    totp: GeneradorTotp
    tokens: GeneradorTokenAcceso
    refresh: AlmacenRefresh
    envio_otp: EnvioOtp
    almacen_otp: AlmacenOtp
    rate_limiter: RateLimiter
    emisor_email: EnviarEmail
    almacen_reset: AlmacenReset
    # configuración
    password_min_length: int = 10
    otp_length: int = 6
    otp_ttl_seg: int = 300
    otp_max_intentos: int = 5
    otp_max_solicitudes_hora: int = 5
    rate_limit_login: int = 10
    rate_limit_registro: int = 5
    reset_ttl_seg: int = 3600
    reset_max_solicitudes_hora: int = 5
