from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PptShapeSource(BaseModel):
    type: str = "react_state"
    key: str = ""


class PptShapeItem(BaseModel):
    slide_index: int = Field(..., ge=0)
    slide_no: int | None = None
    shape_name: str
    text: str
    source: PptShapeSource | dict[str, Any] | None = None


class PptExportPayload(BaseModel):
    meta: dict[str, Any] = Field(default_factory=dict)
    items: list[PptShapeItem] = Field(default_factory=list)