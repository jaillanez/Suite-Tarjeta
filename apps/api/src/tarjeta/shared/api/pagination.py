"""Paginación estándar para los endpoints de listado."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
