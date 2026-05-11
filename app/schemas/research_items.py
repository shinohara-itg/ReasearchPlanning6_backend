from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


QuestionType = Literal["single", "multi", "free_text", "numeric", "single_grid", "multi_grid"]
AdoptionStatus = Literal["adopted", "rejected"]


class AnalysisBlockInput(BaseModel):
    id: str = Field(..., description="分析アプローチID")
    subq: str = Field(..., description="サブクエスチョン")
    approach: str = Field(default="", description="分析アプローチ説明")
    hypothesis: str = Field(default="", description="仮説")
    axis: List[str] = Field(default_factory=list, description="比較軸")
    items: List[str] = Field(default_factory=list, description="使用設問")
    priority: Optional[str] = Field(default=None, description="recommended/candidate/excluded")
    selected: Optional[bool] = Field(default=None, description="採用状態")


class ResearchItemBase(BaseModel):
    id: str
    number: int
    question: str
    question_type: QuestionType
    choices_example: List[str] = Field(default_factory=list)


class ScreeningResearchItem(ResearchItemBase):
    section: str = Field(default="対象者判定用")


class AnalysisResearchItem(ResearchItemBase):
    subq_id: str
    subq: str
    source_analysis_id: str
    adoption_status: AdoptionStatus = Field(default="adopted")
    score: Optional[float] = None
    reason: Optional[str] = None


class ResearchItemsGenerateRequest(BaseModel):
    orien_outline_text: str
    kickoff_text: str = ""
    subquestions_text: str = ""
    target_condition_text: str
    analysis_blocks: List[AnalysisBlockInput]
    selected_analysis_ids: List[str] = Field(default_factory=list)
    min_analysis_questions: int = Field(default=40, ge=10, le=100)


class ResearchItemsGenerateSummary(BaseModel):
    screening_count: int
    analysis_count: int


class ResearchItemsGenerateResponse(BaseModel):
    screening_items: List[ScreeningResearchItem]
    analysis_items: List[AnalysisResearchItem]
    summary: ResearchItemsGenerateSummary


class ResearchItemsShortlistRequest(BaseModel):
    analysis_items: List[AnalysisResearchItem]
    desired_count: int = Field(..., ge=1, le=100)


class ResearchItemsShortlistSummary(BaseModel):
    before_count: int
    after_count: int


class ResearchItemsShortlistResponse(BaseModel):
    analysis_items: List[AnalysisResearchItem]
    summary: ResearchItemsShortlistSummary


class ResearchItemsConfirmRequest(BaseModel):
    screening_items: List[ScreeningResearchItem]
    analysis_items: List[AnalysisResearchItem]


class ResearchItemsPreviewPayload(BaseModel):
    slide_title: str = "調査項目案"
    screening_items: List[ScreeningResearchItem]
    analysis_items: List[AnalysisResearchItem]


class ResearchItemsConfirmResponse(BaseModel):
    confirmed_screening_items: List[ScreeningResearchItem]
    confirmed_analysis_items: List[AnalysisResearchItem]
    preview_payload: ResearchItemsPreviewPayload
    summary: ResearchItemsShortlistSummary