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
) -> KickoffResponse:
    orien_outline_text = (orien_outline_text or "").strip()
    selected_axis_text = (selected_axis_text or "").strip()

    if not orien_outline_text:
        raise ValueError("orien_outline_text is required.")
    if not selected_axis_text:
        raise ValueError("selected_axis_text is required.")

    prompt = f"""
あなたは市場調査設計の専門家です。
以下のオリエン内容の整理と、選択された課題視点をもとに、
調査設計の初期段階で用いる「キックオフノート」を作成してください。

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

【条件】
- 各項目は80〜120字程度を目安に、簡潔かつ具体的に記述すること
- オリエン内容にある固有名詞・背景・制約・文脈をできるだけ反映すること
- 「選択された課題視点」を最優先の前提として全体を構成すること
- 【目標】や【現状】は、市場調査で仮説検証可能な範囲に限定すること
- 【問い】は、この案件で明らかにすべきリサーチクエスチョンとして書くこと
- 【ポイント】には、なぜその構成にしたのか、注意点や補足を簡潔に書くこと
- 抽象的すぎる表現は避けること
- 不明な情報は勝手に補完しすぎず、与えられた情報の範囲で最善に構成すること

【入力データ】
▼オリエン内容の整理
{orien_outline_text[:4000]}

▼選択された課題視点（最優先で反映）
{selected_axis_text[:2000]}
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