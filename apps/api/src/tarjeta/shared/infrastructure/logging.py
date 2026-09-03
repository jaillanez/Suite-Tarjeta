"""Logging estructurado con redacción de datos sensibles.

Emite líneas JSON a stdout. Ningún log puede contener DNI, CUIL o domicilio en claro
(§8.3): se redactan por patrón los números de 7-8 dígitos (DNI) y de 11 dígitos (CUIL).
El domicilio es texto libre y no se debe loguear nunca; esa regla es de disciplina.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

# CUIL: 11 dígitos (con o sin guiones). DNI: 7-8 dígitos. El orden importa: primero CUIL.
_CUIL_RE = re.compile(r"\b\d{2}-?\d{8}-?\d\b")
_DNI_RE = re.compile(r"\b\d{7,8}\b")


def redact(text: str) -> str:
    text = _CUIL_RE.sub("[CUIL_REDACTADO]", text)
    text = _DNI_RE.sub("[DNI_REDACTADO]", text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        if record.exc_info:
            payload["exc_info"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(debug: bool = False) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
