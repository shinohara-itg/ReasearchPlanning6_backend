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


# 追加
class PptTableItem(BaseModel):
    slide_index: int = Field(..., ge=0)
    slide_no: int | None = None
    shape_name: str
    start_row: int = 1
    rows: list[list[Any]] = Field(default_factory=list)


class PptExportPayload(BaseModel):
    meta: dict[str, Any] = Field(default_factory=dict)
    items: list[PptShapeItem] = Field(default_factory=list)

    # 追加
    tables: list[PptTableItem] = Field(default_factory=list)

class PptExportPayload(BaseModel):
    meta: dict[str, Any] = Field(default_factory=dict)
    items: list[PptShapeItem] = Field(default_factory=list)
    tables: list[PptTableItem] = Field(default_factory=list)

    # 追加
    schedule_tables: list[list[list[Any]]] = Field(default_factory=list)
