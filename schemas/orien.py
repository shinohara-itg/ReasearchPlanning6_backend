from pydantic import BaseModel, Field
from typing import List

class OrienOutlineRequest(BaseModel):
    extracted_texts: List[str] = Field(default_factory=list)
    manual_text: str = ""

class OrienOutlineResponse(BaseModel):
    orien_outline_ai_draft: str
    orien_outline_text: str
    