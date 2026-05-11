from pydantic import BaseModel, Field
from typing import List


class SubQuestionItem(BaseModel):
    id: str = Field(..., description="サブクエスチョンID")
    subq: str = Field(..., description="サブクエスチョン本文")
    axis: str = Field(default="", description="分析軸案")
    items: str = Field(default="", description="評価項目案")


class SubQuestionsRequest(BaseModel):
    orien_outline_text: str = Field(..., min_length=1, description="オリエン整理済みテキスト")
    selected_axis_text: str = Field(..., min_length=1, description="選択した課題視点テキスト")
    main_question: str = Field(..., min_length=1, description="キックオフノートの問い")


class SubQuestionsResponse(BaseModel):
    subq_list: List[SubQuestionItem]