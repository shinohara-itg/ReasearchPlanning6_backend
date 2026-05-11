from typing import List

from pydantic import BaseModel, Field


class KickoffInput(BaseModel):
    目標: str = Field(default="")
    現状: str = Field(default="")
    ビジネス課題: str = Field(default="")
    調査目的: str = Field(default="")
    問い: str = Field(default="")
    仮説: str = Field(default="")
    ポイント: str = Field(default="")


class SubQuestionItem(BaseModel):
    id: str = Field(default="")
    subq: str = Field(default="")
    axis: List[str] = Field(default_factory=list)
    items: List[str] = Field(default_factory=list)


class AnalysisApproachRequest(BaseModel):
    orien_outline_text: str = Field(..., min_length=1)
    selected_axis_text: str = Field(..., min_length=1)
    kickoff: KickoffInput
    subq_list: List[SubQuestionItem] = Field(default_factory=list)


class AnalysisBlock(BaseModel):
    id: str
    source_subq_ids: List[str]
    subq: str
    axis: List[str]
    items: List[str]
    approach: str
    hypothesis: str
    priority: str
    score: int
    selection_reason: str
    selected: bool


class SelectionSummary(BaseModel):
    selected_count: int
    max_selectable: int


class AnalysisApproachResponse(BaseModel):
    analysis_blocks: List[AnalysisBlock]
    selection_summary: SelectionSummary