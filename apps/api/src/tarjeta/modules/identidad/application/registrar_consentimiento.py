"""Casos de uso: registrar y listar consentimientos (§3.1)."""

from __future__ import annotations

from tarjeta.modules.identidad.domain.consentimiento import Consentimiento, TipoConsentimiento
from tarjeta.modules.identidad.domain.events import ConsentimientoOtorgado, ConsentimientoRevocado
from tarjeta.shared.domain.types import EntityId

from .deps import Puertos
from .dto import ConsentimientoInput


class RegistrarConsentimiento:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(
        self, *, id_persona: str, entrada: ConsentimientoInput, ip: str, ua: str
    ) -> None:
        p = self.p
        pid = EntityId.from_str(id_persona)
        tipo = TipoConsentimiento(entrada.tipo)
        version = await p.textos.version_vigente(tipo) or "v1"
        await p.consentimientos.agregar(
            Consentimiento.registrar(
                id_persona=pid,
                tipo=tipo,
                version_texto=version,
                otorgado=entrada.otorgado,
                ip=ip,
                user_agent=ua,
            )
        )
        evento = (
            ConsentimientoOtorgado(id_persona=id_persona, tipo=tipo.value, version=version)
            if entrada.otorgado
            else ConsentimientoRevocado(id_persona=id_persona, tipo=tipo.value)
        )
        await p.outbox.escribir([evento])
        await p.uow.commit()


class ListarConsentimientos:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str) -> dict[str, bool]:
        """Estado vigente por tipo (último registro)."""
        pid = EntityId.from_str(id_persona)
        estado: dict[str, bool] = {}
        for tipo in TipoConsentimiento:
            ultimo = await self.p.consentimientos.ultimo_por_tipo(pid, tipo)
            estado[tipo.value] = bool(ultimo and ultimo.otorgado)
        return estado
