"""Unit: dominio y aplicación del módulo comercios."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pytest

from tarjeta.modules.comercios.application.permisos import exigir
from tarjeta.modules.comercios.domain.comercio import Comercio, EstadoComercio, EvidenciaConvenio
from tarjeta.modules.comercios.domain.errors import (
    CajeroBloqueado,
    ConvenioNoAceptado,
    DispositivoNoRegistrado,
    InvitacionExpirada,
    PermisoComercioDenegado,
    TransicionComercioInvalida,
    UbicacionRequerida,
)
from tarjeta.modules.comercios.domain.invitacion import Invitacion
from tarjeta.modules.comercios.domain.roles import (
    MATRIZ,
    Permiso,
    RolComercio,
    alcance_limitado,
    tiene_permiso,
)
from tarjeta.modules.comercios.domain.sucursal import EstadoSucursal, Franja, Horario, Sucursal
from tarjeta.modules.comercios.domain.usuario import RolComercio as _R
from tarjeta.modules.comercios.domain.usuario import UsuarioComercio
from tarjeta.modules.comercios.infrastructure.firma import FirmadorEstablecimientoHmac
from tarjeta.shared.domain.types import EntityId


def _convenio() -> EvidenciaConvenio:
    return EvidenciaConvenio(version="v1", fecha=datetime.now(UTC), ip="")


# ------------------------------------------------------------------ roles


def test_matriz_admin_comercio_todo() -> None:
    for permiso in Permiso:
        assert tiene_permiso(RolComercio.ADMIN_COMERCIO, permiso)


def test_matriz_cajero_solo_caja_y_turno() -> None:
    assert tiene_permiso(RolComercio.CAJERO, Permiso.CANJE_OPERAR)
    assert tiene_permiso(RolComercio.CAJERO, Permiso.TURNO_OPERAR)
    assert not tiene_permiso(RolComercio.CAJERO, Permiso.USUARIO_GESTIONAR)
    assert not tiene_permiso(RolComercio.CAJERO, Permiso.SUCURSAL_GESTIONAR)


def test_matriz_cada_celda() -> None:
    for rol in RolComercio:
        permitidos = MATRIZ.get(rol, set())
        for permiso in Permiso:
            assert tiene_permiso(rol, permiso) is (permiso in permitidos)


def test_alcance_por_sucursal() -> None:
    assert not alcance_limitado(RolComercio.ADMIN_COMERCIO)
    assert alcance_limitado(RolComercio.ENCARGADO)
    assert alcance_limitado(RolComercio.CAJERO)


def test_exigir_permiso() -> None:
    with pytest.raises(PermisoComercioDenegado):
        exigir(RolComercio.CAJERO, Permiso.USUARIO_GESTIONAR)
    exigir(RolComercio.ADMIN_COMERCIO, Permiso.USUARIO_GESTIONAR)  # no lanza


# ------------------------------------------------------------------ comercio (máquina de estados)


def _comercio() -> Comercio:
    return Comercio.solicitar(
        cuit="20304050607",
        razon_social="Kiosco Rivadavia",
        nombre_fantasia="El Kiosco",
        rubro="kiosco",
        logo_url="",
        id_responsable=EntityId.new(),
        convenio=_convenio(),
    )


def test_solicitar_requiere_convenio() -> None:
    with pytest.raises(ConvenioNoAceptado):
        Comercio.solicitar(
            cuit="20304050607",
            razon_social="X",
            nombre_fantasia="",
            rubro="",
            logo_url="",
            id_responsable=EntityId.new(),
            convenio=None,
        )


def test_flujo_estados_valido() -> None:
    c = _comercio()
    assert c.estado is EstadoComercio.SOLICITADA
    c.transicionar(EstadoComercio.EN_REVISION)
    c.transicionar(EstadoComercio.APROBADA)
    c.transicionar(EstadoComercio.ACTIVA)
    c.transicionar(EstadoComercio.SUSPENDIDA, motivo="control")
    c.transicionar(EstadoComercio.ACTIVA)
    c.transicionar(EstadoComercio.BAJA, motivo="cierre")
    assert c.estado is EstadoComercio.BAJA


def test_transicion_invalida() -> None:
    c = _comercio()
    with pytest.raises(TransicionComercioInvalida):
        c.transicionar(EstadoComercio.ACTIVA)  # SOLICITADA -> ACTIVA no existe


def test_baja_es_terminal() -> None:
    c = _comercio()
    c.transicionar(EstadoComercio.EN_REVISION)
    c.transicionar(EstadoComercio.RECHAZADA, motivo="no cumple")
    with pytest.raises(TransicionComercioInvalida):
        c.transicionar(EstadoComercio.EN_REVISION)


# ------------------------------------------------------------------ sucursal


def _sucursal(horarios: list[Horario] | None = None) -> Sucursal:
    return Sucursal.crear(
        id_comercio=EntityId.new(),
        nombre="Central",
        direccion="San Isidro 123",
        lat=-31.5,
        lon=-68.5,
        horarios=horarios,
    )


def test_sucursal_requiere_ubicacion() -> None:
    with pytest.raises(UbicacionRequerida):
        Sucursal.crear(id_comercio=EntityId.new(), nombre="X", direccion="", lat=None, lon=None)


def test_abierto_ahora_doble_turno() -> None:
    # Lunes con doble turno 09-13 y 17-21.
    horario = Horario(
        dia=0,
        franjas=(
            Franja(desde=time(9, 0), hasta=time(13, 0)),
            Franja(desde=time(17, 0), hasta=time(21, 0)),
        ),
    )
    s = _sucursal([horario])
    lunes_10 = datetime(2026, 9, 7, 10, 0)  # 2026-09-07 es lunes
    lunes_14 = datetime(2026, 9, 7, 14, 0)  # entre turnos
    lunes_18 = datetime(2026, 9, 7, 18, 0)
    martes_10 = datetime(2026, 9, 8, 10, 0)
    assert s.abierto_ahora(lunes_10) is True
    assert s.abierto_ahora(lunes_14) is False
    assert s.abierto_ahora(lunes_18) is True
    assert s.abierto_ahora(martes_10) is False  # no hay horario el martes


def test_cerrada_no_abre() -> None:
    s = _sucursal([Horario(dia=0, franjas=(Franja(time(0, 0), time(23, 59)),))])
    s.cerrar_temporal("vacaciones", "2026-10-01")
    assert s.estado is EstadoSucursal.CERRADA_TEMPORAL
    assert s.abierto_ahora(datetime(2026, 9, 7, 10, 0)) is False
    s.reabrir()
    assert s.estado is EstadoSucursal.ACTIVA


# ------------------------------------------------------------------ usuario / PIN


def _usuario(rol: RolComercio = _R.CAJERO) -> UsuarioComercio:
    return UsuarioComercio.crear(id_comercio=EntityId.new(), id_persona=EntityId.new(), rol=rol)


def test_opera_sucursal_scope() -> None:
    suc = EntityId.new()
    otra = EntityId.new()
    cajero = UsuarioComercio.crear(
        id_comercio=EntityId.new(), id_persona=EntityId.new(), rol=_R.CAJERO, sucursales=[suc]
    )
    assert cajero.opera_sucursal(suc) is True
    assert cajero.opera_sucursal(otra) is False
    admin = _usuario(_R.ADMIN_COMERCIO)
    assert admin.opera_sucursal(otra) is True  # sin alcance limitado


def test_pin_solo_en_dispositivo_registrado() -> None:
    u = _usuario()
    u.establecer_pin("hash", huella_dispositivo="device-1")
    with pytest.raises(DispositivoNoRegistrado):
        u.exigir_dispositivo("device-otro")
    u.exigir_dispositivo("device-1")  # no lanza


def test_pin_bloqueo_por_intentos() -> None:
    u = _usuario()
    u.establecer_pin("hash", huella_dispositivo="d")
    ahora = datetime.now(UTC)
    for _ in range(3):
        u.registrar_pin_fallido(ahora, max_intentos=3, bloqueo_seg=300)
    with pytest.raises(CajeroBloqueado):
        u.exigir_no_bloqueado(ahora + timedelta(seconds=10))
    # tras el bloqueo, se puede de nuevo
    u.exigir_no_bloqueado(ahora + timedelta(seconds=400))


# ------------------------------------------------------------------ invitacion


def test_invitacion_expira() -> None:
    inv = Invitacion.crear(
        id_comercio=EntityId.new(),
        rol=RolComercio.ENCARGADO,
        sucursales=[],
        destino="alguien@example.com",
        token_hash="h",
    )
    inv.aceptar(datetime.now(UTC))  # dentro de las 72h: ok
    inv2 = Invitacion.crear(
        id_comercio=EntityId.new(),
        rol=RolComercio.ENCARGADO,
        sucursales=[],
        destino="x",
        token_hash="h2",
    )
    with pytest.raises(InvitacionExpirada):
        inv2.aceptar(datetime.now(UTC) + timedelta(hours=73))


# ------------------------------------------------------------------ firma QR


def test_firma_qr_roundtrip_y_tamper() -> None:
    firmador = FirmadorEstablecimientoHmac("secreto-de-prueba")
    token = firmador.token("suc-123")
    assert firmador.verificar(token) == "suc-123"
    assert firmador.verificar("suc-123.firmafalsa") is None
    assert firmador.verificar("sin-punto") is None
