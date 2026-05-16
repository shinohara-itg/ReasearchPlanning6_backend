import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schemas.proposal_review import (
    ProposalReviewRequest,
    ProposalReviewResponse,
)

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


def generate_proposal_review(req: ProposalReviewRequest) -> ProposalReviewResponse:
    prompt = f"""
あなたは市場調査企画のシニアプランナーです。

以下の情報をもとに、この調査企画によって
クライアントの判断や行動がどのように変わるかを整理してください。

単なる良し悪しの評価ではなく、
「この調査結果が、どの意思決定・行動変化に効くのか」
を具体的に示してください。

また、調査背景やKONで整理した課題に対して、
この調査がどのように有効な情報になるのかを説明してください。

さらに、もう一歩クライアントの意思決定や行動につながる調査にするために、
追加で考慮すべき観点を提案してください。

▼オリエン整理
{req.orien_outline_text[:4000]}

▼課題視点
{req.selected_axis_text[:2000]}

▼KON（目的・仮説など）
{req.kickoff_text[:3000]}

▼サブクエスチョン
{req.subquestions_text[:3000]}

▼分析アプローチ
{req.analysis_text[:3000]}

▼対象者条件
{req.target_condition_text[:2000]}

▼調査項目
{req.research_items_text[:4000]}


【出力ルール】
必ず以下のJSON形式で出力してください。
説明文は不要です。

{{
  "decision_change": "この調査結果からクライアントの判断や行動はこう変わると考えられます、に続く文章",
  "background_connection": "これは、調査背景やKONで整理したどの課題に対して有効な情報なのか",
  "actionable_suggestions": [
    "もう一歩意思決定につなげるために考慮すべき点1",
    "もう一歩意思決定につなげるために考慮すべき点2"
  ]
}}

【記述条件】
- decision_change は、クライアントが何を判断できるようになるかまで書く
- background_connection は、調査背景・KONの内容と接続して書く
- actionable_suggestions は2〜3個にする
- 抽象論だけで終わらせず、調査設計上の追加観点として書く
- 「やや」「ある程度」など曖昧な表現は避ける
"""

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "あなたは市場調査企画のシニアプランナーです。調査結果がクライアントの意思決定や行動にどう接続するかを具体化してください。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content.strip()

    try:
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        json_str = content[json_start:json_end]
        data = json.loads(json_str)
    except Exception:
        raise ValueError(f"JSONパースに失敗しました: {content}")

    return ProposalReviewResponse(
        decision_change=data.get("decision_change", ""),
        background_connection=data.get("background_connection", ""),
        actionable_suggestions=data.get("actionable_suggestions", []),
    )