"""Adaptador real del endpoint municipal (httpx). Programado contra el contrato cerrado."""

from __future__ import annotations

import httpx

from tarjeta.modules.padron.domain.errors import PadronNoDisponible, RespuestaPadronInvalida


class ClientePadronReal:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport  # inyectable para el test de contrato

    async def _get(self, params: dict[str, str]) -> dict[str, object]:
        headers = {"authorization": f"ApiKey {self._api_key}"}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                resp = await client.get(
                    f"{self._base_url}/padron/estado", params=params, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PadronNoDisponible(str(exc)) from exc
        if not isinstance(data, dict):
            raise RespuestaPadronInvalida("La respuesta del padrón no es un objeto JSON.")
        return data

    async def al_dia(self, dni: str) -> bool:
        data = self._validar_bool(await self._get({"dni": dni}), "al_dia")
        return data

    async def es_comerciante(self, cuit: str) -> bool:
        data = self._validar_bool(await self._get({"cuit": cuit}), "es_comerciante")
        return data

    @staticmethod
    def _validar_bool(data: dict[str, object], campo: str) -> bool:
        valor = data.get(campo)
        if not isinstance(valor, bool):
            raise RespuestaPadronInvalida(
                f"El campo '{campo}' debe ser booleano; llegó {type(valor).__name__}."
            )
        return valor
