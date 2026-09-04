"""Almacén de OTP y rate limiter sobre Redis."""

from __future__ import annotations

import hashlib
import hmac

from redis.asyncio import Redis


def _hash_codigo(codigo: str) -> str:
    return hashlib.sha256(codigo.encode()).hexdigest()


class RedisAlmacenOtp:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, clave: str) -> str:
        return f"otp:{clave}"

    async def emitir(self, clave: str, codigo: str, ttl_seg: int) -> None:
        key = self._key(clave)
        await self._redis.delete(f"{key}:intentos")
        await self._redis.set(key, _hash_codigo(codigo), ex=ttl_seg)

    async def verificar_y_consumir(self, clave: str, codigo: str, max_intentos: int) -> bool:
        key = self._key(clave)
        guardado = await self._redis.get(key)
        if guardado is None:
            return False
        guardado_str = guardado.decode() if isinstance(guardado, bytes) else str(guardado)
        intentos = await self._redis.incr(f"{key}:intentos")
        if intentos > max_intentos:
            await self._redis.delete(key, f"{key}:intentos")
            return False
        if hmac.compare_digest(guardado_str, _hash_codigo(codigo)):
            await self._redis.delete(key, f"{key}:intentos")
            return True
        return False


class RedisAlmacenReset:
    """Token de recuperación de un solo uso sobre Redis: token -> id_persona, con TTL.

    Guarda el hash del token (no el token en claro) y lo consume atómicamente (GETDEL), de modo
    que un token sirve una sola vez.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, token: str) -> str:
        return f"reset:{_hash_codigo(token)}"

    async def emitir(self, token: str, id_persona: str, ttl_seg: int) -> None:
        await self._redis.set(self._key(token), id_persona, ex=ttl_seg)

    async def consumir(self, token: str) -> str | None:
        valor = await self._redis.getdel(self._key(token))
        if valor is None:
            return None
        return valor.decode() if isinstance(valor, bytes) else str(valor)


class RedisRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def permitido(self, clave: str, limite: int, ventana_seg: int) -> bool:
        key = f"rl:{clave}"
        actual = await self._redis.incr(key)
        if actual == 1:
            await self._redis.expire(key, ventana_seg)
        return actual <= limite
