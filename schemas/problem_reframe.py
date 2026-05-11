from typing import List, Optional

from pydantic import BaseModel, Field


class ProblemReframeRequest(BaseModel):
    orien_outline_text: str = Field(..., description="オリエン整理済みテキスト")
    extracted_texts: List[str] = Field(
        default_factory=list,
        description="アップロード資料から抽出したテキスト一覧",
    )
    manual_text: Optional[str] = Field(
        default="",
        description="ユーザーの手入力補足テキスト",
    )


class ProblemReframeResponse(BaseModel):
    c1_next_action: str = Field(..., description="調査結果を受けてクライアント担当者が実行すること")
    c2_exec_summary: str = Field(..., description="報告先が意思決定したい論点の要約")
    c4_business_brand: str = Field(..., description="事業・ブランドの中長期課題")