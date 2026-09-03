"""Unit: dominio y aplicación del módulo gobierno (roles, doble conformidad, parametría)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from tarjeta.modules.gobierno.application.auditoria_consumer import _redactar, consumir_evento
from tarjeta.modules.gobierno.application.doble_conformidad import (
    DecidirAprobacion,
    ExpirarPendientes,
    SolicitarAprobacion,
)
from tarjeta.modules.gobierno.application.parametria import ParametriaService
from tarjeta.modules.gobierno.application.permisos import exigir, resolver_rol
from tarjeta.modules.gobierno.domain.aprobacion import EstadoSolicitud, SolicitudAprobacion
from tarjeta.modules.gobierno.domain.auditoria import RegistroAuditoria
from tarjeta.modules.gobierno.domain.errors import (
    AutoaprobacionProhibida,
    ParametroFueraDeRango,
    ParametroInexistente,
    PermisoDenegado,
    RangoInsuficiente,
    SolicitudNoAprobable,
)
from tarjeta.modules.gobierno.domain.parametro import CATALOGO, validar_valor
from tarjeta.modules.gobierno.domain.roles import (
    DOBLE_CONFORMIDAD,
    MATRIZ,
    Permiso,
    RolMunicipal,
    rango_suficiente,
    tiene_permiso,
)
from tarjeta.shared.domain.types import EntityId

# --------------------------------------------------------------------------- roles


def test_matriz_super_admin_tiene_todos_los_permisos() -> None:
    for permiso in Permiso:
        assert tiene_permiso(RolMunicipal.SUPER_ADMIN, permiso)


def test_matriz_auditor_es_solo_lectura() -> None:
    # AUDITOR puede ver, nunca modificar.
    assert tiene_permiso(RolMunicipal.AUDITOR, Permiso.AUDITORIA_VER)
    assert tiene_permiso(RolMunicipal.AUDITOR, Permiso.TABLERO_VER)
    for prohibido in (
        Permiso.PARAMETRIA_EDITAR,
        Permiso.CIUDADANO_ALTA,
        Permiso.CIUDADANO_SUSPENDER,
        Permiso.AJUSTE_PUNTOS,
        Permiso.ROLES_GESTIONAR,
        Permiso.APROBAR_DOBLE_CONF,
    ):
        assert not tiene_permiso(RolMunicipal.AUDITOR, prohibido)


def test_matriz_personal_no_puede_suspender_ni_editar_parametria() -> None:
    assert tiene_permiso(RolMunicipal.PERSONAL, Permiso.CIUDADANO_ALTA)
    assert tiene_permiso(RolMunicipal.PERSONAL, Permiso.CIUDADANO_FICHA)
    assert not tiene_permiso(RolMunicipal.PERSONAL, Permiso.CIUDADANO_SUSPENDER)
    assert not tiene_permiso(RolMunicipal.PERSONAL, Permiso.PARAMETRIA_EDITAR)


def test_matriz_encargado_no_gestiona_roles_ni_parametria() -> None:
    assert tiene_permiso(RolMunicipal.ENCARGADO, Permiso.CIUDADANO_SUSPENDER)
    assert not tiene_permiso(RolMunicipal.ENCARGADO, Permiso.ROLES_GESTIONAR)
    assert not tiene_permiso(RolMunicipal.ENCARGADO, Permiso.PARAMETRIA_EDITAR)
    assert not tiene_permiso(RolMunicipal.ENCARGADO, Permiso.AUDITORIA_VER)


def test_matriz_cada_celda_es_consistente_con_los_datos() -> None:
    # Verifica celda por celda que tiene_permiso refleje exactamente MATRIZ.
    for rol in RolMunicipal:
        permitidos = MATRIZ.get(rol, set())
        for permiso in Permiso:
            assert tiene_permiso(rol, permiso) is (permiso in permitidos)


def test_rango_suficiente() -> None:
    assert rango_suficiente(RolMunicipal.ADMINISTRADOR, RolMunicipal.ENCARGADO)
    assert rango_suficiente(RolMunicipal.ENCARGADO, RolMunicipal.ENCARGADO)
    assert not rango_suficiente(RolMunicipal.ENCARGADO, RolMunicipal.ADMINISTRADOR)


def test_doble_conformidad_incluye_las_acciones_sensibles() -> None:
    assert Permiso.REGLAS_NIVEL_EDITAR in DOBLE_CONFORMIDAD
    assert Permiso.RECLAMO_CUENTA in DOBLE_CONFORMIDAD
    assert Permiso.EXPORTAR_MASIVO in DOBLE_CONFORMIDAD


# --------------------------------------------------------------------------- parametro


def test_validar_valor_ok() -> None:
    validar_valor("grupo_max_miembros", 6)  # dentro de [1, 20]


def test_validar_valor_fuera_de_rango() -> None:
    with pytest.raises(ParametroFueraDeRango):
        validar_valor("grupo_max_miembros", 999)


def test_validar_valor_parametro_inexistente() -> None:
    with pytest.raises(ParametroInexistente):
        validar_valor("no_existe", 1)


def test_catalogo_tiene_defaults_dentro_de_rango() -> None:
    for d in CATALOGO.values():
        assert d.minimo <= d.default <= d.maximo


# --------------------------------------------------------------------------- aprobacion


def _solicitud(
    solicitante: str = "s1", rol: RolMunicipal = RolMunicipal.ENCARGADO
) -> SolicitudAprobacion:
    return SolicitudAprobacion.crear(
        accion="reglas_nivel:editar",
        payload={"clave": "grupo_max_miembros", "valor": 8},
        id_solicitante=solicitante,
        rol=rol,
    )


def test_crear_solicitud_pendiente_con_expiracion_72h() -> None:
    s = _solicitud()
    assert s.estado is EstadoSolicitud.PENDIENTE
    delta = s.fecha_expiracion - s.fecha_solicitud
    assert abs(delta - timedelta(hours=72)) < timedelta(seconds=1)


def test_aprobar_ok() -> None:
    s = _solicitud(solicitante="s1", rol=RolMunicipal.ENCARGADO)
    s.aprobar(id_aprobador="a1", rol_aprobador=RolMunicipal.ADMINISTRADOR, motivo="ok")
    assert s.estado is EstadoSolicitud.APROBADA
    assert s.id_aprobador == "a1"


def test_no_autoaprobacion() -> None:
    s = _solicitud(solicitante="s1")
    with pytest.raises(AutoaprobacionProhibida):
        s.aprobar(id_aprobador="s1", rol_aprobador=RolMunicipal.SUPER_ADMIN, motivo="x")


def test_aprobador_de_rango_inferior_falla() -> None:
    s = _solicitud(solicitante="s1", rol=RolMunicipal.ADMINISTRADOR)
    with pytest.raises(RangoInsuficiente):
        s.aprobar(id_aprobador="a1", rol_aprobador=RolMunicipal.ENCARGADO, motivo="x")


def test_solicitud_expirada_no_es_aprobable() -> None:
    s = _solicitud()
    s.fecha_expiracion = datetime.now(UTC) - timedelta(hours=1)
    assert not s.esta_vigente(datetime.now(UTC))
    with pytest.raises(SolicitudNoAprobable):
        s.aprobar(id_aprobador="a1", rol_aprobador=RolMunicipal.SUPER_ADMIN, motivo="x")


def test_rechazar_ok_y_autorechazo_prohibido() -> None:
    s = _solicitud(solicitante="s1")
    with pytest.raises(AutoaprobacionProhibida):
        s.rechazar(id_aprobador="s1", motivo="x")
    s.rechazar(id_aprobador="a1", motivo="no")
    assert s.estado is EstadoSolicitud.RECHAZADA


def test_marcar_error() -> None:
    s = _solicitud()
    s.marcar_error("explotó")
    assert s.estado is EstadoSolicitud.ERROR
    assert s.motivo_decision == "explotó"


# --------------------------------------------------------------------------- fakes


class _FakeUow:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


class _FakeAuditoria:
    def __init__(self) -> None:
        self.registros: list[RegistroAuditoria] = []
        self._eventos: set[str] = set()

    async def agregar(self, registro: RegistroAuditoria) -> None:
        self.registros.append(registro)
        if registro.id_evento_origen:
            self._eventos.add(registro.id_evento_origen)

    async def existe_evento(self, id_evento_origen: str) -> bool:
        return id_evento_origen in self._eventos

    async def listar(self, **kwargs: Any) -> list[RegistroAuditoria]:
        return list(self.registros)


class _FakeAprobaciones:
    def __init__(self) -> None:
        self.items: dict[str, SolicitudAprobacion] = {}

    async def agregar(self, s: SolicitudAprobacion) -> None:
        self.items[str(s.id)] = s

    async def obtener(self, id: EntityId) -> SolicitudAprobacion | None:
        return self.items.get(str(id))

    async def guardar(self, s: SolicitudAprobacion) -> None:
        self.items[str(s.id)] = s

    async def listar_pendientes(self) -> list[SolicitudAprobacion]:
        return [s for s in self.items.values() if s.estado is EstadoSolicitud.PENDIENTE]

    async def expirar_vencidas(self, ahora: datetime) -> int:
        n = 0
        for s in self.items.values():
            if s.estado is EstadoSolicitud.PENDIENTE and s.fecha_expiracion < ahora:
                s.estado = EstadoSolicitud.EXPIRADA
                n += 1
        return n


class _FakeParametros:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    async def obtener(self, clave: str) -> int | None:
        return self.store.get(clave)

    async def todos(self) -> dict[str, int]:
        return dict(self.store)

    async def guardar(self, clave: str, valor: int) -> None:
        self.store[clave] = valor


class _FakeAgentes:
    def __init__(self, mapa: dict[str, RolMunicipal] | None = None) -> None:
        self.mapa = mapa or {}

    async def rol_de(self, id_persona: EntityId) -> RolMunicipal | None:
        return self.mapa.get(str(id_persona))

    async def asignar(self, id_persona: EntityId, rol: RolMunicipal) -> None:
        self.mapa[str(id_persona)] = rol

    async def listar(self) -> list[tuple[str, RolMunicipal]]:
        return list(self.mapa.items())


class _Puertos:
    def __init__(self) -> None:
        self.uow = _FakeUow()
        self.auditoria = _FakeAuditoria()
        self.aprobaciones = _FakeAprobaciones()
        self.parametros = _FakeParametros()
        self.agentes = _FakeAgentes()
        self.recaudacion = None


# --------------------------------------------------------------------------- parametría


async def test_parametria_obtener_default_y_guardado() -> None:
    p = _Puertos()
    svc = ParametriaService(p)  # type: ignore[arg-type]
    assert await svc.obtener("grupo_max_miembros") == 6  # default del catálogo
    await svc.cambiar(
        clave="grupo_max_miembros", valor=10, actor="a1", rol="ADMINISTRADOR", motivo="m"
    )
    assert await svc.obtener("grupo_max_miembros") == 10
    # queda auditado con valor anterior y nuevo
    assert p.auditoria.registros[-1].accion == "parametria:editar"
    assert p.auditoria.registros[-1].valor_nuevo == {"valor": 10}


async def test_parametria_todos_mezcla_defaults() -> None:
    p = _Puertos()
    svc = ParametriaService(p)  # type: ignore[arg-type]
    todos = await svc.todos()
    assert todos["grupo_max_miembros"] == 6
    assert set(todos) == set(CATALOGO)


async def test_parametria_rechaza_fuera_de_rango() -> None:
    p = _Puertos()
    svc = ParametriaService(p)  # type: ignore[arg-type]
    with pytest.raises(ParametroFueraDeRango):
        await svc.cambiar(
            clave="grupo_max_miembros", valor=999, actor="a", rol="ADMINISTRADOR", motivo="m"
        )
    assert p.auditoria.registros == []  # no audita un cambio inválido


# --------------------------------------------------------------------------- doble conf


async def test_flujo_doble_conformidad_aprobar_ejecuta_accion() -> None:
    p = _Puertos()
    id_sol = await SolicitarAprobacion(p).ejecutar(  # type: ignore[arg-type]
        accion="reglas_nivel:editar",
        payload={"clave": "grupo_max_miembros", "valor": 12},
        id_solicitante="s1",
        rol="ENCARGADO",
    )
    ejecutado: list[dict[str, Any]] = []

    async def ejecutor(payload: dict[str, Any]) -> None:
        ejecutado.append(payload)

    await DecidirAprobacion(p).aprobar(  # type: ignore[arg-type]
        id_solicitud=id_sol,
        id_aprobador="a1",
        rol_aprobador="ADMINISTRADOR",
        motivo="ok",
        ejecutor=ejecutor,
    )
    s = p.aprobaciones.items[id_sol]
    assert s.estado is EstadoSolicitud.APROBADA
    assert ejecutado and ejecutado[0]["valor"] == 12


async def test_doble_conformidad_ejecutor_que_falla_deja_error() -> None:
    p = _Puertos()
    id_sol = await SolicitarAprobacion(p).ejecutar(  # type: ignore[arg-type]
        accion="reglas_nivel:editar", payload={}, id_solicitante="s1", rol="ENCARGADO"
    )

    async def ejecutor(_: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    await DecidirAprobacion(p).aprobar(  # type: ignore[arg-type]
        id_solicitud=id_sol,
        id_aprobador="a1",
        rol_aprobador="ADMINISTRADOR",
        motivo="ok",
        ejecutor=ejecutor,
    )
    assert p.aprobaciones.items[id_sol].estado is EstadoSolicitud.ERROR


async def test_aprobar_solicitud_inexistente() -> None:
    p = _Puertos()
    with pytest.raises(SolicitudNoAprobable):
        await DecidirAprobacion(p).aprobar(  # type: ignore[arg-type]
            id_solicitud=str(EntityId.new()),
            id_aprobador="a1",
            rol_aprobador="ADMINISTRADOR",
            motivo="x",
        )


async def test_rechazar_solicitud_inexistente() -> None:
    p = _Puertos()
    with pytest.raises(SolicitudNoAprobable):
        await DecidirAprobacion(p).rechazar(  # type: ignore[arg-type]
            id_solicitud=str(EntityId.new()), id_aprobador="a1", motivo="x"
        )


async def test_expirar_pendientes() -> None:
    p = _Puertos()
    s = _solicitud()
    s.fecha_expiracion = datetime.now(UTC) - timedelta(hours=1)
    await p.aprobaciones.agregar(s)
    n = await ExpirarPendientes(p).ejecutar()  # type: ignore[arg-type]
    assert n == 1
    assert p.aprobaciones.items[str(s.id)].estado is EstadoSolicitud.EXPIRADA


# --------------------------------------------------------------------------- permisos


async def test_exigir_sin_rol_deniega() -> None:
    with pytest.raises(PermisoDenegado):
        exigir(None, Permiso.PARAMETRIA_EDITAR)


async def test_exigir_rol_sin_permiso_deniega() -> None:
    with pytest.raises(PermisoDenegado):
        exigir(RolMunicipal.AUDITOR, Permiso.PARAMETRIA_EDITAR)


async def test_resolver_rol() -> None:
    pid = str(EntityId.new())
    agentes = _FakeAgentes({pid: RolMunicipal.ENCARGADO})
    assert await resolver_rol(agentes, pid) is RolMunicipal.ENCARGADO  # type: ignore[arg-type]


# --------------------------------------------------------------------------- auditoría consumer


def test_redactar_oculta_dni_y_cuil() -> None:
    salida = _redactar({"texto": "el dni 12345678 y cuil 20-12345678-3", "lista": ["87654321"]})
    assert "12345678" not in salida["texto"]
    assert "[DNI_REDACTADO]" in salida["texto"]
    assert "[CUIL_REDACTADO]" in salida["texto"]
    assert salida["lista"] == ["[DNI_REDACTADO]"]


class _SesionAuditoria:
    """Sesión mínima para el consumer: solo necesita ser pasada al repo fake."""


async def test_consumir_evento_es_idempotente(monkeypatch: pytest.MonkeyPatch) -> None:
    audit = _FakeAuditoria()
    import tarjeta.modules.gobierno.application.auditoria_consumer as mod

    monkeypatch.setattr(mod, "SqlAlchemyAuditoriaRepository", lambda _session: audit)
    payload = {"event_id": "ev-1", "__tipo__": "persona_registrada", "dni": "12345678"}
    await consumir_evento(payload, session=None)  # type: ignore[arg-type]
    await consumir_evento(payload, session=None)  # type: ignore[arg-type]  # repetido
    assert len(audit.registros) == 1  # idempotencia por id_evento_origen
    # y sin PII en claro
    assert "12345678" not in str(audit.registros[0].valor_nuevo)
