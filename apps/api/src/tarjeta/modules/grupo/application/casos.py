"""Casos de uso del grupo familiar (§10).

La herencia de nivel NO se toca acá: cada caso emite el evento correspondiente y el composition
root recalcula el nivel por evento (§10.4). El pozo común (puntos) también lo orquesta el
composition root, porque cruza el módulo `puntos`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tarjeta.modules.grupo.domain.errors import (
    GrupoInexistente,
    InvitacionInvalida,
    MiembroInexistente,
    NoEsTitular,
    NoPuedeCrearGrupo,
    YaPerteneceAGrupo,
)
from tarjeta.modules.grupo.domain.events import MiembroInvitado, MiembroSalio
from tarjeta.modules.grupo.domain.grupo import Grupo
from tarjeta.modules.grupo.domain.invitacion import Invitacion
from tarjeta.modules.grupo.domain.miembro import Miembro
from tarjeta.modules.grupo.domain.tipos import ModoBilletera, RolGrupo
from tarjeta.shared.domain.types import EntityId

from .antifraude import EvaluarAntifraude
from .deps import GrupoPuertos


class CrearGrupo:
    def __init__(self, puertos: GrupoPuertos) -> None:
        self.p = puertos

    async def ejecutar(
        self, *, id_titular: str, modo: ModoBilletera, es_black_propio_al_dia: bool
    ) -> Grupo:
        # §10.1: solo Black por mérito propio y al día. El composition root aporta el booleano.
        if not es_black_propio_al_dia:
            raise NoPuedeCrearGrupo(
                "Solo un Black por mérito propio y al día puede crear un grupo."
            )
        if await self.p.grupos.miembro_de(id_titular) is not None:
            raise YaPerteneceAGrupo("Ya pertenecés a un grupo.")
        grupo = Grupo.crear(id_titular=id_titular, modo_billetera=modo)
        await self.p.grupos.agregar(grupo)
        await self.p.grupos.agregar_miembro(
            Miembro.crear(id_grupo=grupo.id, id_persona=id_titular, rol=RolGrupo.TITULAR)
        )
        await self.p.outbox.escribir(grupo.pull_events())
        await self.p.uow.commit()
        return grupo


class InvitarMiembro:
    def __init__(self, puertos: GrupoPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_grupo: str, id_actor: str, ip: str) -> Invitacion:
        grupo = await self._grupo_del_titular(id_grupo, id_actor)
        inv = Invitacion.crear(id_grupo=grupo.id, id_titular=id_actor, ip_titular=ip)
        await self.p.invitaciones.agregar(inv)
        await self.p.outbox.escribir([MiembroInvitado(id_grupo=str(grupo.id), id_titular=id_actor)])
        await self.p.uow.commit()
        return inv

    async def _grupo_del_titular(self, id_grupo: str, id_actor: str) -> Grupo:
        grupo = await self.p.grupos.obtener(EntityId.from_str(id_grupo))
        if grupo is None or not grupo.activo:
            raise GrupoInexistente("El grupo no existe.")
        if grupo.id_titular != id_actor:
            raise NoEsTitular("Solo el titular puede invitar.")
        return grupo


class AceptarInvitacion:
    def __init__(self, puertos: GrupoPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, token: str, id_invitado: str) -> Grupo:
        inv = await self.p.invitaciones.por_token(token)
        if inv is None:
            raise InvitacionInvalida("Invitación inexistente.")
        if await self.p.grupos.miembro_de(id_invitado) is not None:
            raise YaPerteneceAGrupo("Ya pertenecés a un grupo.")
        inv.aceptar(id_invitado=id_invitado, ahora=datetime.now(UTC))  # valida vigencia
        grupo = await self.p.grupos.obtener(inv.id_grupo)
        if grupo is None or not grupo.activo:
            raise GrupoInexistente("El grupo no existe.")
        await self.p.grupos.agregar_miembro(
            Miembro.crear(id_grupo=grupo.id, id_persona=id_invitado, rol=RolGrupo.MIEMBRO)
        )
        await self.p.invitaciones.guardar(inv)
        from tarjeta.modules.grupo.domain.events import MiembroAgregado

        await self.p.outbox.escribir(
            [
                MiembroAgregado(
                    id_grupo=str(grupo.id), id_titular=grupo.id_titular, id_persona=id_invitado
                )
            ]
        )
        # Antifraude: solo observa (genera caso si corresponde), nunca frena el alta (§10.7).
        await EvaluarAntifraude(self.p).al_agregar_miembro(grupo.id)
        await self.p.uow.commit()
        return grupo


class SalirDelGrupo:
    def __init__(self, puertos: GrupoPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_grupo: str, id_persona: str) -> None:
        gid = EntityId.from_str(id_grupo)
        miembro = await self.p.grupos.miembro_en(gid, id_persona)
        if miembro is None or not miembro.activo:
            raise MiembroInexistente("No sos miembro activo de este grupo.")
        if miembro.rol is RolGrupo.TITULAR:
            raise NoEsTitular("El titular no puede salir: debe suceder o disolver el grupo.")
        miembro.dar_de_baja()
        await self.p.grupos.guardar_miembro(miembro)
        await self.p.outbox.escribir([MiembroSalio(id_grupo=id_grupo, id_persona=id_persona)])
        await self.p.uow.commit()


class DisolverGrupo:
    def __init__(self, puertos: GrupoPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_grupo: str, id_actor: str) -> list[str]:
        gid = EntityId.from_str(id_grupo)
        grupo = await self.p.grupos.obtener(gid)
        if grupo is None or not grupo.activo:
            raise GrupoInexistente("El grupo no existe.")
        if grupo.id_titular != id_actor:
            raise NoEsTitular("Solo el titular puede disolver el grupo.")
        miembros = await self.p.grupos.miembros_activos(gid)
        afectados = [m.id_persona for m in miembros if m.rol is RolGrupo.MIEMBRO]
        for m in miembros:
            m.dar_de_baja()
            await self.p.grupos.guardar_miembro(m)
        grupo.disolver(id_miembros=afectados)
        await self.p.grupos.guardar(grupo)
        await self.p.outbox.escribir(grupo.pull_events())
        await self.p.uow.commit()
        return afectados


class SucederTitular:
    def __init__(self, puertos: GrupoPuertos) -> None:
        self.p = puertos

    async def ejecutar(
        self, *, id_grupo: str, id_titular_actual: str, id_nuevo_titular: str
    ) -> None:
        gid = EntityId.from_str(id_grupo)
        grupo = await self.p.grupos.obtener(gid)
        if grupo is None or not grupo.activo:
            raise GrupoInexistente("El grupo no existe.")
        if grupo.id_titular != id_titular_actual:
            raise NoEsTitular("Solo el titular actual puede ceder la titularidad.")
        viejo = await self.p.grupos.miembro_en(gid, id_titular_actual)
        nuevo = await self.p.grupos.miembro_en(gid, id_nuevo_titular)
        if nuevo is None or not nuevo.activo:
            raise MiembroInexistente("El sucesor no es un miembro activo.")
        if viejo is not None:
            viejo.dar_de_baja()
            await self.p.grupos.guardar_miembro(viejo)
        nuevo.rol = RolGrupo.TITULAR
        await self.p.grupos.guardar_miembro(nuevo)
        grupo.suceder_titular(id_nuevo_titular)
        await self.p.grupos.guardar(grupo)
        await self.p.outbox.escribir(
            [*grupo.pull_events(), MiembroSalio(id_grupo=id_grupo, id_persona=id_titular_actual)]
        )
        await self.p.uow.commit()


class GestionMiembro:
    """Panel del titular: suspender/reactivar y tope mensual por miembro (§10.6)."""

    def __init__(self, puertos: GrupoPuertos) -> None:
        self.p = puertos

    async def _miembro(self, id_grupo: str, id_actor: str, id_persona: str) -> Miembro:
        gid = EntityId.from_str(id_grupo)
        grupo = await self.p.grupos.obtener(gid)
        if grupo is None or not grupo.activo:
            raise GrupoInexistente("El grupo no existe.")
        if grupo.id_titular != id_actor:
            raise NoEsTitular("Solo el titular gestiona a los miembros.")
        miembro = await self.p.grupos.miembro_en(gid, id_persona)
        if miembro is None or miembro.rol is RolGrupo.TITULAR:
            raise MiembroInexistente("Miembro inexistente.")
        return miembro

    async def suspender(self, *, id_grupo: str, id_actor: str, id_persona: str) -> None:
        m = await self._miembro(id_grupo, id_actor, id_persona)
        m.suspender()
        await self.p.grupos.guardar_miembro(m)
        await self.p.uow.commit()

    async def reactivar(self, *, id_grupo: str, id_actor: str, id_persona: str) -> None:
        m = await self._miembro(id_grupo, id_actor, id_persona)
        m.reactivar()
        await self.p.grupos.guardar_miembro(m)
        await self.p.uow.commit()

    async def fijar_tope(
        self, *, id_grupo: str, id_actor: str, id_persona: str, tope_mensual: int | None
    ) -> None:
        m = await self._miembro(id_grupo, id_actor, id_persona)
        m.tope_mensual = tope_mensual
        await self.p.grupos.guardar_miembro(m)
        await self.p.uow.commit()
