import json
import os

from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schemas.kickoff import KickoffResponse

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    return text.strip()


def generate_kickoff_draft(
    orien_outline_text: str,
    selected_axis_text: str,
    customer_business_analysis: str = "",
) -> KickoffResponse:
    orien_outline_text = (orien_outline_text or "").strip()
    selected_axis_text = (selected_axis_text or "").strip()
    customer_business_analysis = (customer_business_analysis or "").strip()

    if not orien_outline_text:
        raise ValueError("orien_outline_text is required.")
    if not selected_axis_text:
        raise ValueError("selected_axis_text is required.")

    prompt = f"""
あなたは市場調査会社のシニアアナリストです。
以下のオリエン内容、選択された課題視点、顧客事業分析をもとに、
調査設計の初期段階で用いる「キックオフノート」を作成してください。

今回のKONは、単なる調査背景の整理ではありません。
顧客がなぜ今この調査を必要としているのか、
どの事業判断に接続するのかが伝わるレベルまで、事業文脈を反映してください。

【出力形式】
必ず次のJSONオブジェクトのみを出力してください。
前置き、説明文、コードブロック、Markdown記号は不要です。

{{
  "目標": "...",
  "現状": "...",
  "ビジネス課題": "...",
  "調査目的": "...",
  "問い": "...",
  "仮説": "...",
  "ポイント": "..."
}}

【記述方針】
- 各項目は120〜180字程度を目安に、以前より少し厚めに記述すること
- 顧客事業分析がある場合は、必ずその内容を優先的に反映すること
- 「目標」は単なるKPIではなく、事業として何を実現したいかを書くこと
- 「現状」は単なる事実列挙ではなく、なぜそれが事業上問題なのかまで書くこと
- 「ビジネス課題」は、売上・顧客接点・ブランド体験・競争優位・収益構造などの観点で書くこと
- 「調査目的」は、調査で何を明らかにすれば意思決定できるのかを書くこと
- 「問い」は、この案件で最も見極めるべきリサーチクエスチョンとして書くこと
- 「仮説」は、顧客事業分析から読み取れる仮説を明示すること
- 「ポイント」は、見落とすと危険な論点、または調査設計上の注意点を書くこと
- 抽象的すぎる表現は避け、オリエン内容にある固有名詞・背景・制約・文脈を反映すること
- 不明な外部事実は断定せず、「可能性」「仮説」として扱うこと

【特に重視する観点】
- 顧客事業が置かれている状況
- 市場・顧客・競争の変化
- 顧客が感じていそうな焦りや違和感
- なぜ今この調査が必要なのか
- 今回の意思決定で何を判断したいのか
- 調査がどの事業判断に接続するのか

【入力データ】
▼オリエン内容の整理
{orien_outline_text[:4000]}

▼選択された課題視点（最優先で反映）
{selected_axis_text[:3000]}

▼顧客事業分析・事業仮説整理
{customer_business_analysis[:6000] if customer_business_analysis else "未入力"}
""".strip()

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": "あなたは市場調査設計の専門家です。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=1000,
    )

    ai_text = response.choices[0].message.content or ""
    ai_text = _strip_code_fence(ai_text)

    try:
        obj = json.loads(ai_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM output is not valid JSON: {ai_text}") from exc

    required_keys = [
        "目標",
        "現状",
        "ビジネス課題",
        "調査目的",
        "問い",
        "仮説",
        "ポイント",
    ]

    normalized = {}
    for key in required_keys:
        value = obj.get(key, "")
        normalized[key] = str(value).strip()

    return KickoffResponse(**normalized)