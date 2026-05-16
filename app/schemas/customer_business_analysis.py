from pydantic import BaseModel, Field
from typing import List, Optional


class CustomerBusinessAnalysisRequest(BaseModel):
    client_name: Optional[str] = ""
    research_title: Optional[str] = ""
    orien_outline_text: str = Field(..., description="オリエン整理結果")
    manual_text: Optional[str] = ""
    extracted_texts: List[str] = []


class SourceItem(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = ""


class CustomerBusinessAnalysisResponse(BaseModel):
    market_events: str
    business_brand_status: str
    risks_opportunities: str
    decision_points: str
    required_information: str
    search_summary: str
    sources: List[SourceItem] = []