"""Base para value objects.

Un value object es inmutable y se compara por valor, no por identidad. Se modela como
dataclass congelada. Este módulo ofrece un marcador común y utilidades mínimas.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Marcador base para value objects (inmutables, comparados por valor)."""
