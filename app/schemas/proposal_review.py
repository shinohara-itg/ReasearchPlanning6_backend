from pydantic import BaseModel
from typing import List, Optional


class ProposalReviewRequest(BaseModel):
    orien_outline_text: str
    selected_axis_text: Optional[str] = ""
    kickoff_text: Optional[str] = ""
    subquestions_text: Optional[str] = ""
    analysis_text: Optional[str] = ""
    target_condition_text: Optional[str] = ""
    research_items_text: Optional[str] = ""


class ProposalReviewResponse(BaseModel):
    decision_change: str
    background_connection: str
    actionable_suggestions: List[str]