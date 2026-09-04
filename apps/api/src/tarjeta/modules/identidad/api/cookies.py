"""§12 P1-A: entrega del refresh token por cookie HttpOnly para clientes web.

El móvil (Capacitor) sigue recibiendo el refresh en el cuerpo y lo guarda en el almacén seguro
del SO. La web pide "modo cookie" (header `X-Auth-Mode: cookie`) y entonces:

- el refresh viaja en una cookie `HttpOnly; Secure; SameSite=Strict` (inaccesible a JS ⇒ no robable
  por XSS) y NO se devuelve en el cuerpo;
- el resto de los endpoints se autentican con `Authorization: Bearer <access>` (no con la cookie),
  así que no son vulnerables a CSRF; `SameSite=Strict` protege además al propio `/auth/refresh`.

El access token es de vida corta y la web lo mantiene en memoria (no en `localStorage`).
"""

from __future__ import annotations

from fastapi import Request, Response

from tarjeta.config import Settings

REFRESH_COOKIE = "tarjeta_refresh"
_HEADER = "x-auth-mode"


def modo_cookie(request: Request) -> bool:
    """La web opera en modo cookie: lo pide por header, o ya tiene la cookie de refresh."""
    if request.headers.get(_HEADER, "").lower() == "cookie":
        return True
    return REFRESH_COOKIE in request.cookies


def leer_refresh(request: Request, body_token: str) -> str:
    """El refresh sale de la cookie si está; si no, del cuerpo (móvil)."""
    return request.cookies.get(REFRESH_COOKIE) or body_token


def set_refresh_cookie(response: Response, refresh: str, settings: Settings) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh,
        max_age=settings.refresh_ttl_seconds,
        httponly=True,
        secure=settings.environment != "dev",
        samesite="strict",
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/", httponly=True, samesite="strict")
