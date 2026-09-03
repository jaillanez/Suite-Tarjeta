"""Tests unitarios de la infraestructura de identidad (sin DB)."""

from __future__ import annotations

import base64
import os

import pyotp
import pytest

from tarjeta.modules.identidad.infrastructure.argon2_hasher import Argon2Hasher
from tarjeta.modules.identidad.infrastructure.jwt_generador import JwtGenerador
from tarjeta.modules.identidad.infrastructure.otp_consola import OtpConsola
from tarjeta.modules.identidad.infrastructure.renaper_stub import RenaperStub
from tarjeta.modules.identidad.infrastructure.totp_pyotp import TotpPyotp
from tarjeta.shared.domain.errors import AuthenticationError
from tarjeta.shared.infrastructure.crypto import FieldCipher, search_hash
from tarjeta.shared.infrastructure.logging import redact

_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()


def test_cipher_roundtrip() -> None:
    cipher = FieldCipher(_KEY, "v1")
    token = cipher.encrypt("20123456786")
    assert token.startswith("v1:")
    assert cipher.decrypt(token) == "20123456786"


def test_search_hash_normaliza_dni() -> None:
    # El mismo DNI con y sin puntos produce el mismo hash.
    assert search_hash("12.345.678", "pepper") == search_hash("12345678", "pepper")


def test_search_hash_depende_del_pepper() -> None:
    assert search_hash("12345678", "p1") != search_hash("12345678", "p2")


def test_jwt_roundtrip_y_tamper() -> None:
    gen = JwtGenerador(secret="secreto-de-test-con-mas-de-32-bytes-ok", ttl_seg=900)
    token = gen.crear(id_persona="abc", perfil="CIUDADANO", permisos=["x"])
    claims = gen.decodificar(token)
    assert claims.id_persona == "abc"
    assert claims.perfil == "CIUDADANO"
    with pytest.raises(AuthenticationError):
        gen.decodificar(token + "tamper")


def test_argon2_hash_y_verifica() -> None:
    hasher = Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1)
    h = hasher.hash("contrasena-larga")
    assert hasher.verificar(h, "contrasena-larga")
    assert not hasher.verificar(h, "otra")
    assert isinstance(hasher.necesita_rehash(h), bool)


def test_totp_verifica_codigo() -> None:
    totp = TotpPyotp(issuer="Test")
    secreto = totp.generar_secreto()
    codigo = pyotp.TOTP(secreto).now()
    assert totp.verificar(secreto, codigo)
    assert "issuer=Test" in totp.uri(secreto, "20123456786")


async def test_renaper_stub_resultados() -> None:
    assert (await RenaperStub(resultado="aprobado").verificar(dni="1", cuil="2")).aprobado
    assert (await RenaperStub(resultado="revision").verificar(dni="1", cuil="2")).requiere_revision
    assert not (await RenaperStub(resultado="rechazado").verificar(dni="1", cuil="2")).aprobado


async def test_otp_consola_solo_en_dev() -> None:
    await OtpConsola(environment="dev").enviar("2644123456", "123456")  # no lanza
    with pytest.raises(RuntimeError):
        await OtpConsola(environment="prod").enviar("2644123456", "123456")


def test_redaccion_de_logs() -> None:
    salida = redact("registro dni=12345678 cuil=20-12345678-6 fin")
    assert "12345678" not in salida
    assert "20-12345678-6" not in salida
    assert "[DNI_REDACTADO]" in salida
    assert "[CUIL_REDACTADO]" in salida
