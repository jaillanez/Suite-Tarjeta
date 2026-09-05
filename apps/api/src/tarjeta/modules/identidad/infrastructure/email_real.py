"""Adaptador de email real por SMTP (§15.2).

Usa la biblioteca estándar (`smtplib` + STARTTLS). `smtplib` es bloqueante, así que el envío se
corre en un hilo para no bloquear el loop async. Los datos del servidor (host, puerto, usuario,
contraseña, remitente) vienen de la configuración de producción.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage


class EmailReal:
    def __init__(self, *, host: str, port: int, user: str, password: str, remitente: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._remitente = remitente

    async def enviar(self, email: str, asunto: str, cuerpo: str) -> None:
        await asyncio.to_thread(self._enviar_sync, email, asunto, cuerpo)

    def _enviar_sync(self, email: str, asunto: str, cuerpo: str) -> None:
        msg = EmailMessage()
        msg["From"] = self._remitente
        msg["To"] = email
        msg["Subject"] = asunto
        msg.set_content(cuerpo)
        with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
            smtp.starttls()
            if self._user:
                smtp.login(self._user, self._password)
            smtp.send_message(msg)
