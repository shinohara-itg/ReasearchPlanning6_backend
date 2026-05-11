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
あなたは市場調査企画の品質レビュー専門家です。

以下の情報をもとに、
「オリエン内容と企画書案の整合性」を厳しく評価してください。

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


【評価観点】
1. オリエン内容との整合性
2. 調査目的・問い・SQの一貫性
3. 分析アプローチが意思決定に資するか
4. 対象者条件の妥当性
5. 調査項目とSQ/分析の対応関係

【出力ルール】
必ず以下のJSON形式で出力してください。
説明文は不要です。

{{
  "score": 0〜100の整数,
  "overall_comment": "全体評価（簡潔に）",
  "good_points": ["良い点1", "良い点2"],
  "concerns": ["懸念点1", "懸念点2"],
  "recommended_fixes": ["修正提案1", "修正提案2"]
}}

※各項目は3つ以内に収めてください
※曖昧な表現は禁止（例：やや〜、ある程度〜）
※必ず改善アクションまで踏み込むこと
"""

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": "あなたは厳格な市場調査レビュー専門家です。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content.strip()

    # JSON抽出（安全対策）
    try:
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        json_str = content[json_start:json_end]

        data = json.loads(json_str)
    except Exception as e:
        raise ValueError(f"JSONパースに失敗しました: {content}")

    return ProposalReviewResponse(
        score=data.get("score", 0),
        overall_comment=data.get("overall_comment", ""),
        good_points=data.get("good_points", []),
        concerns=data.get("concerns", []),
        recommended_fixes=data.get("recommended_fixes", []),
    )