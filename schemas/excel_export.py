from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExcelResearchItem(BaseModel):
    id: str | None = ""
    number: int | None = None
    question: str = ""
    question_type: str = ""
    choices_example: list[str] = Field(default_factory=list)
    section: str | None = None
    subq_id: str | None = ""
    subq: str | None = ""
    source_analysis_id: str | None = ""
    adoption_status: str | None = ""
    score: float | None = None
    reason: str | None = ""


class ResearchItemsExcelExportRequest(BaseModel):
    project_name: str = "調査項目案"
    client_name: str = ""
    research_title: str = ""
    screening_items: list[ExcelResearchItem] = Field(default_factory=list)
    analysis_items: list[ExcelResearchItem] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)