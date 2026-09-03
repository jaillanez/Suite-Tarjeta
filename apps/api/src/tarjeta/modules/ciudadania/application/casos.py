"""Casos de uso de ciudadania (request-scoped; hacen commit por la unidad de trabajo)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from tarjeta.modules.ciudadania.domain.errors import PerfilCiudadanoInexistente
from tarjeta.modules.ciudadania.domain.events import SolicitudActualizarEstado
from tarjeta.modules.ciudadania.domain.excepcion import ExcepcionNivel
from tarjeta.modules.ciudadania.domain.nivel import Nivel
from tarjeta.shared.domain.errors import BusinessRuleViolation
from tarjeta.shared.domain.types import EntityId

from .deps import CiudadaniaPuertos


@dataclass(frozen=True, slots=True)
class EstadoCiudadano:
    nivel: str
    numero_tarjeta: str
    estado_tarjeta: str
    tiene_tarjeta_fisica: bool


class MiEstado:
    def __init__(self, puertos: CiudadaniaPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str) -> EstadoCiudadano:
        perfil = await self.p.perfiles.obtener(EntityId.from_str(id_persona))
        if perfil is None:
            raise PerfilCiudadanoInexistente("Todavía no tenés perfil de ciudadano.")
        return EstadoCiudadano(
            nivel=str(perfil.nivel),
            numero_tarjeta=perfil.numero_tarjeta,
            estado_tarjeta=str(perfil.estado_tarjeta),
            tiene_tarjeta_fisica=perfil.tiene_tarjeta_fisica,
        )


class SolicitarActualizarEstadoUC:
    def __init__(self, puertos: CiudadaniaPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str) -> None:
        p = self.p
        if not await p.rate_limiter.permitido(
            f"actualizar_estado:{id_persona}", p.actualizar_max_por_dia, 86400
        ):
            raise BusinessRuleViolation("Alcanzaste el máximo de actualizaciones por hoy.")
        await p.outbox.escribir([SolicitudActualizarEstado(id_persona=id_persona)])
        await p.uow.commit()


class BloquearTarjeta:
    def __init__(self, puertos: CiudadaniaPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str) -> None:
        p = self.p
        perfil = await p.perfiles.obtener(EntityId.from_str(id_persona))
        if perfil is None:
            raise PerfilCiudadanoInexistente("Perfil inexistente.")
        perfil.bloquear_tarjeta()
        await p.perfiles.guardar(perfil)
        await p.uow.commit()


class AplicarExcepcion:
    """Otorga Black por excepción (§5.2). La pantalla del agente es del PASO 05."""

    def __init__(self, puertos: CiudadaniaPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str, motivo: str, dias_vigencia: int) -> None:
        p = self.p
        pid = EntityId.from_str(id_persona)
        perfil = await p.perfiles.obtener(pid)
        if perfil is None:
            raise PerfilCiudadanoInexistente("Perfil inexistente.")
        ahora = datetime.now(UTC)
        await p.excepciones.agregar(
            ExcepcionNivel(
                id=EntityId.new(),
                id_persona=pid,
                motivo=motivo,
                vigencia_desde=ahora,
                vigencia_hasta=ahora + timedelta(days=dias_vigencia),
            )
        )
        hist = perfil.recalcular(
            al_dia=perfil.nivel is Nivel.BLACK,
            excepcion_black_vigente=True,
            motivo=f"excepción: {motivo}",
        )
        await p.perfiles.guardar(perfil)
        if hist is not None:
            await p.historial.agregar(hist)
        await p.outbox.escribir(perfil.pull_events())
        await p.uow.commit()
