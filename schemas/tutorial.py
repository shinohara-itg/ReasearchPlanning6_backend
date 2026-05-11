from typing import List, Optional
from pydantic import BaseModel, Field


class TutorialOption(BaseModel):
    key: str = Field(..., description="選択肢キー")
    title: str = Field(..., description="選択肢タイトル")
    description: str = Field(..., description="選択肢説明")
    recommended: bool = Field(False, description="推奨かどうか")


class TutorialQuestionBlock(BaseModel):
    question_key: str = Field(..., description="質問識別子")
    title: str = Field(..., description="質問タイトル")
    description: str = Field("", description="質問説明")
    options: List[TutorialOption] = Field(default_factory=list)
    recommended_key: Optional[str] = Field(None, description="推奨選択肢キー")
    selected_key: Optional[str] = Field(None, description="現在選択中キー")


class AnalysisSuggestion(BaseModel):
    key: str = Field(..., description="分析提案キー")
    axis_title: str = Field(..., description="分析軸名")
    scenario: str = Field(..., description="分析シナリオ")
    recommended: bool = Field(True, description="推奨表示")
    selected: bool = Field(True, description="選択状態")


class SlidePlanItem(BaseModel):
    slide_type: str = Field(..., description="スライド種別")
    title: str = Field(..., description="スライドタイトル")
    purpose: str = Field(..., description="そのスライドの役割")
    order: int = Field(..., description="表示順")


class SlidePlan(BaseModel):
    recommended_slide_count: int = Field(..., description="推奨スライド数")
    plan_type: str = Field(..., description="企画構成タイプ")
    slides: List[SlidePlanItem] = Field(default_factory=list)


class TutorialSummary(BaseModel):
    detected_theme: str = Field(..., description="オリエンから判定したテーマ")
    detected_scope: str = Field(..., description="推奨整理範囲")
    contact_evaluation_type: Optional[str] = Field(
        None, description="施策・接点評価系の場合の詳細判定"
    )
    reasoning: List[str] = Field(default_factory=list, description="判定理由")
    notes: List[str] = Field(default_factory=list, description="補足メモ")


class TutorialPlanRequest(BaseModel):
    orien_outline_text: str = Field(..., description="オリエン整理テキスト")
    manual_text: Optional[str] = Field(None, description="手入力補足")
    extracted_texts: Optional[List[str]] = Field(
        default=None, description="アップロードファイルから抽出されたテキスト群"
    )


class TutorialRefreshRequest(BaseModel):
    orien_outline_text: str = Field(..., description="オリエン整理テキスト")
    q1_selected_key: str = Field(..., description="Q1の選択キー")
    q2_selected_key: str = Field(..., description="Q2の選択キー")


class TutorialPlanResponse(BaseModel):
    tutorial_summary: TutorialSummary
    q1: TutorialQuestionBlock
    q2: TutorialQuestionBlock
    q3: List[AnalysisSuggestion]
    slide_plan: SlidePlan


class TutorialRefreshResponse(BaseModel):
    q3: List[AnalysisSuggestion]
    slide_plan: SlidePlan