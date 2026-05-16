import os
import json
from typing import Dict, Any

from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schemas.customer_business_analysis import (
    CustomerBusinessAnalysisRequest,
    CustomerBusinessAnalysisResponse,
)

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


def _safe_json_loads(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= 0:
            return json.loads(text[start : end + 1])
        raise


def _build_context(req: CustomerBusinessAnalysisRequest) -> str:
    extracted_joined = "\n\n".join(req.extracted_texts[:5])

    return f"""
【クライアント名】
{req.client_name or "不明"}

【調査名】
{req.research_title or "不明"}

【オリエン整理結果】
{req.orien_outline_text[:6000]}

【手入力メモ】
{(req.manual_text or "")[:2000]}

【アップロード資料からの抽出テキスト】
{extracted_joined[:8000]}
""".strip()


def generate_customer_business_analysis(
    req: CustomerBusinessAnalysisRequest,
) -> CustomerBusinessAnalysisResponse:
    context = _build_context(req)

    prompt = f"""
あなたは市場調査会社のシニアアナリストです。
以下の案件情報だけをもとに、調査企画書の「中心テーマ見直し」に使える顧客事業分析を作成してください。

今回はWeb検索を使いません。
そのため、外部事実を断定せず、案件情報から読み取れること・推察できること・追加確認が必要なことを分けてください。

重要方針:
- 単なるオリエン要約ではなく、顧客の事業判断に接続する
- 「この調査で何を決めたいのか」を明確にする
- 顧客がすでに言っている課題と、言っていないが重要そうな課題を分ける
- アナリストの読みとして、違和感・リスク・機会を出す
- 断定ではなく、仮説として表現する
- KON、SQ、分析アプローチの生成に使える粒度で書く
- 日本語で簡潔に書く
- JSONのみで返す

回答項目:
1. market_events:
   ターゲット市場で何が起きていそうか。
   ※案件情報から推察される市場変化・顧客変化・競争変化を書く。

2. business_brand_status:
   対象事業やブランドの現状はどう整理できるか。
   ※強み・弱み・置かれている状況・顧客が抱えていそうな焦りを書く。

3. risks_opportunities:
   今後どのようなリスクや機会を感じるか。
   ※調査で見落とすと危ない論点、逆に掘ると価値がありそうな論点を書く。

4. decision_points:
   今回の意思決定ポイントとなることは何か。
   ※この調査後に顧客が判断したいことを、事業判断の言葉で書く。

5. required_information:
   判断に必要な情報やデータは何か。
   ※調査で取得すべき情報、分析軸、比較すべき対象を書く。

6. search_summary:
   Web検索なしであることを前提に、今回の分析の位置づけを書く。
   ※「案件情報ベースの仮説整理」であり、外部環境の裏取りは別途必要である旨も含める。

出力形式:
{{
  "market_events": "...",
  "business_brand_status": "...",
  "risks_opportunities": "...",
  "decision_points": "...",
  "required_information": "...",
  "search_summary": "..."
}}

【案件情報】
{context}
"""

    res = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "あなたは市場調査企画と事業戦略設計に強いシニアアナリストです。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.35,
    )

    data = _safe_json_loads(res.choices[0].message.content)

    return CustomerBusinessAnalysisResponse(
        market_events=data.get("market_events", ""),
        business_brand_status=data.get("business_brand_status", ""),
        risks_opportunities=data.get("risks_opportunities", ""),
        decision_points=data.get("decision_points", ""),
        required_information=data.get("required_information", ""),
        search_summary=data.get("search_summary", ""),
        sources=[],
    )