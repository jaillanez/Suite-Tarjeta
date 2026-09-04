"""Generación de Puntos Municipales por conductas útiles al municipio (§09.5).

En este paso alcanza con dejar el mecanismo y una regla activa: **estar al día**, detectado por la
transición del padrón que ya se registra. Las demás reglas (referidos, campañas) se agregan por
parametría llamando a `por_concepto`, sin tocar el código.

Las variantes `acreditar_*` NO confirman la transacción (las usa el dispatcher de eventos, que es
el dueño de la unidad de trabajo). Las variantes `por_*` confirman (para uso directo desde HTTP).
"""

from __future__ import annotations

from tarjeta.modules.puntos.domain.events import PuntosAcreditados
from tarjeta.modules.puntos.domain.moneda import COMERCIO_MUNICIPAL, TipoMoneda

from .contabilidad import Contabilidad
from .deps import PuntosPuertos


class AcreditarPuntosMunicipales:
    def __init__(self, puertos: PuntosPuertos) -> None:
        self.p = puertos
        self.conta = Contabilidad(puertos)

    async def _acreditar(self, *, id_persona: str, puntos: int, concepto: str, clave: str) -> int:
        otorgados = await self.conta.acreditar(
            id_titular=id_persona,
            tipo_moneda=TipoMoneda.PM,
            id_comercio=None,
            puntos=puntos,
            concepto=concepto,
            clave_dedup=clave,
        )
        if otorgados > 0:
            await self.p.outbox.escribir(
                [
                    PuntosAcreditados(
                        id_titular=id_persona,
                        tipo_moneda=TipoMoneda.PM.value,
                        id_comercio=COMERCIO_MUNICIPAL,
                        puntos=otorgados,
                        concepto=concepto,
                    )
                ]
            )
        return otorgados

    # --- variantes sin commit (dispatcher de eventos) -----------------------

    async def acreditar_al_dia(self, *, id_persona: str, periodo: str) -> int:
        """Regla activa: PM por estar al día. Idempotente por período (año-mes)."""
        return await self._acreditar(
            id_persona=id_persona,
            puntos=self.p.config.pm_al_dia,
            concepto="Puntos por estar al día",
            clave=f"pm-aldia:{id_persona}:{periodo}",
        )

    # --- variantes con commit (HTTP directo) --------------------------------

    async def por_estar_al_dia(self, *, id_persona: str, periodo: str) -> int:
        otorgados = await self.acreditar_al_dia(id_persona=id_persona, periodo=periodo)
        await self.p.uow.commit()
        return otorgados

    async def por_concepto(
        self, *, id_persona: str, puntos: int, concepto: str, clave_dedup: str
    ) -> int:
        """Mecanismo genérico (referidos, campañas, participación): parametrizable (§09.5)."""
        otorgados = await self._acreditar(
            id_persona=id_persona, puntos=puntos, concepto=concepto, clave=clave_dedup
        )
        await self.p.uow.commit()
        return otorgados
