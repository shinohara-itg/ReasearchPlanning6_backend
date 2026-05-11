from pydantic import BaseModel, Field


class KickoffRequest(BaseModel):
    orien_outline_text: str = Field(..., min_length=1, description="オリエン整理済みテキスト")
    selected_axis_text: str = Field(..., min_length=1, description="選択した課題視点テキスト")


class KickoffResponse(BaseModel):
    目標: str
    現状: str
    ビジネス課題: str
    調査目的: str
    問い: str
    仮説: str
    ポイント: str