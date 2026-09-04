"""Cola sin conexión y su sincronización (§08.5).

En Argentina el modo offline no es opcional. Las operaciones se aceptaron en el mostrador con
el ciudadano presente; al recuperar conexión se suben en orden. Regla de conflicto: si el tope
se agotó mientras el comercio estaba sin conexión, **se honra al ciudadano** y se avisa al
comercio (evento). Límites reforzados: monto máximo por operación y cantidad máxima en cola.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from tarjeta.modules.canje.domain.descuento import calcular_descuento
from tarjeta.modules.canje.domain.errors import LimiteSinConexion
from tarjeta.modules.canje.domain.events import ConflictoTopeSinConexion
from tarjeta.modules.canje.domain.transaccion import Transaccion, ViaCanje
from tarjeta.shared.domain.errors import ConflictError

from .deps import CanjePuertos
from .operaciones import formato_comprobante


@dataclass(slots=True)
class OperacionEncolada:
    clave_idempotencia: str
    id_persona: str
    nivel: str
    id_comercio: str
    id_sucursal: str
    id_cajero: str
    id_promocion: str | None
    mecanica: str | None
    valor: int
    monto: int
    via: str


@dataclass(slots=True)
class ResultadoSync:
    clave_idempotencia: str
    aplicada: bool
    id_transaccion: str | None
    conflicto_tope: bool
    motivo: str


class SincronizarSinConexion:
    def __init__(
        self,
        puertos: CanjePuertos,
        *,
        prefijo_comprobante: str,
        monto_max: int,
        max_operaciones: int,
    ) -> None:
        self.p = puertos
        self.prefijo = prefijo_comprobante
        self.monto_max = monto_max
        self.max_operaciones = max_operaciones

    async def ejecutar(self, operaciones: list[OperacionEncolada]) -> list[ResultadoSync]:
        if len(operaciones) > self.max_operaciones:
            raise LimiteSinConexion(
                f"La cola supera el máximo de {self.max_operaciones} operaciones sin conexión."
            )
        resultados: list[ResultadoSync] = []
        hoy = datetime.now(UTC).date()
        for op in operaciones:
            existente = await self.p.transacciones.por_idempotencia(op.clave_idempotencia)
            if existente is not None:
                resultados.append(
                    ResultadoSync(
                        op.clave_idempotencia, True, str(existente.id), False, "duplicada"
                    )
                )
                continue
            if op.monto <= 0 or op.monto > self.monto_max:
                resultados.append(
                    ResultadoSync(
                        op.clave_idempotencia, False, None, False, "monto fuera de límite"
                    )
                )
                continue

            conflicto = False
            if op.id_promocion:
                try:
                    await self.p.reserva.reservar(op.id_promocion, op.id_persona, hoy)
                except ConflictError:
                    # §08.5: tope agotado offline -> se honra al ciudadano igual.
                    conflicto = True

            descuento = (
                calcular_descuento(op.mecanica, op.valor, op.monto)
                if op.id_promocion and op.mecanica
                else 0
            )
            numero = formato_comprobante(self.prefijo, await self.p.secuencia.siguiente())
            t = Transaccion.crear(
                numero_comprobante=numero,
                id_persona=op.id_persona,
                nivel_aplicado=op.nivel,
                id_comercio=op.id_comercio,
                id_sucursal=op.id_sucursal,
                id_cajero=op.id_cajero,
                id_promocion=op.id_promocion,
                monto_bruto=op.monto,
                descuento=descuento,
                via=ViaCanje(op.via),
                clave_idempotencia=op.clave_idempotencia,
                ttl_confirmacion_seg=0,
                sin_conexion=True,
            )
            t.aplicar_directo()  # ya se aceptó en el mostrador
            await self.p.transacciones.agregar(t)
            eventos = list(t.pull_events())
            if conflicto and op.id_promocion:
                eventos.append(
                    ConflictoTopeSinConexion(
                        id_transaccion=str(t.id),
                        id_comercio=op.id_comercio,
                        id_promocion=op.id_promocion,
                    )
                )
            await self.p.outbox.escribir(eventos)
            resultados.append(
                ResultadoSync(op.clave_idempotencia, True, str(t.id), conflicto, "aplicada")
            )
        await self.p.uow.commit()
        return resultados
