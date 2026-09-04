"""Vigencia de una promoción (§07.2): fechas, días de la semana y franja horaria.

Todo se evalúa en la zona horaria de configuración (nunca UTC ni la del servidor). El
`datetime` que recibe `vigente_en` ya debe venir en hora local.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True, slots=True)
class Vigencia:
    fecha_desde: date
    fecha_hasta: date
    # Días de la semana permitidos (0=lunes .. 6=domingo). Vacío = todos.
    dias_semana: frozenset[int] = frozenset()
    # Franja horaria; None = todo el día. Puede cruzar medianoche (desde > hasta).
    hora_desde: time | None = None
    hora_hasta: time | None = None

    def _en_franja(self, t: time) -> bool:
        if self.hora_desde is None or self.hora_hasta is None:
            return True
        if self.hora_desde <= self.hora_hasta:
            return self.hora_desde <= t < self.hora_hasta
        # Cruza medianoche: p. ej. 22:00 a 02:00.
        return t >= self.hora_desde or t < self.hora_hasta

    def vigente_en(self, momento_local: datetime) -> bool:
        d = momento_local.date()
        if not (self.fecha_desde <= d <= self.fecha_hasta):
            return False
        if self.dias_semana and momento_local.weekday() not in self.dias_semana:
            return False
        return self._en_franja(momento_local.time())
