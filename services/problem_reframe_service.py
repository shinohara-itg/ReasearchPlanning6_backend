import json
import os
from typing import List

from dotenv import load_dotenv
from openai import AzureOpenAI


load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


def _compose_orien_context_text(extracted_texts: List[str], manual_text: str) -> str:
    docs_text = "\n".join([t.strip() for t in extracted_texts if isinstance(t, str) and t.strip()]).strip()
    manual_text = (manual_text or "").strip()

    parts = []

    if docs_text:
        parts.append("【オリエン資料（アップロード抽出テキスト）】\n" + docs_text)

    if manual_text:
        parts.append("【オリエン内容レビュー（手入力：最優先）】\n" + manual_text)

    return "\n\n".join(parts).strip()


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

        if text.lower().startswith("json"):
            text = text[4:].strip()

    return text


def generate_problem_reframe_premise(
    orien_outline_text: str,
    extracted_texts: List[str],
    manual_text: str = "",
) -> dict:
    orien_outline_text = (orien_outline_text or "").strip()
    orien_context_text = _compose_orien_context_text(extracted_texts, manual_text)

    if not orien_outline_text:
        raise ValueError("orien_outline_text が空です。")

    if not orien_context_text:
        raise ValueError("extracted_texts または manual_text のいずれかに有効な入力が必要です。")

    prompt = f"""
あなたは市場調査の企画責任者です。
以下の入力を踏まえ、「真の課題」にたどり着くための前提整理として、次の3観点をそれぞれ具体的に考察してください。
この出力はユーザーが編集する前提の一次ドラフトです。

【出力形式】
次のキーを持つ JSON オブジェクト「だけ」を出力してください。
{{
  "c1_next_action": "...",
  "c2_exec_summary": "...",
  "c4_business_brand": "..."
}}

【制約】
- c1_next_action には、「調査を依頼したクライアント担当者が調査結果を受けて何を実行するか」を記述すること
- c2_exec_summary には、報告先（事業責任者・部門長・経営層）が
  「この調査結果を見て何を判断したいのか」「どの選択肢で迷っているのか」が
  明確に分かる形で記述すること
- c2_exec_summary は単なる事実確認や現状把握ではなく、意思決定に直結する論点に限定すること
- c4_business_brand には、短期的な施策課題ではなく、
  売上・シェア・ブランド価値・顧客構造など、
  事業またはブランドの中長期的な健全性に関わる論点として記述すること
- c4_business_brand は個別施策の良し悪しではなく、構造的な問題として表現すること
- 各項目は60〜120字程度
- 固有名詞・前提条件・意思決定者・意思決定タイミングなど、具体情報を優先する
- 不明な場合は「不明」と書いたうえで、推定ではなく不足情報として書く
- ###、**、コードブロック記号は使わない

【入力データ】
▼オリエン統合コンテキスト（アップロード抽出＋手入力）
{orien_context_text[:4000]}

▼オリエン内容の整理（抜粋）
{orien_outline_text[:2000]}
""".strip()

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": "あなたは市場調査の企画責任者です。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=800,
    )

    ai_text = response.choices[0].message.content or ""
    ai_text = _strip_code_fence(ai_text)

    try:
        obj = json.loads(ai_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"AIレスポンスのJSON解析に失敗しました: {e}. raw={ai_text[:500]}") from e

    result = {
        "c1_next_action": str(obj.get("c1_next_action", "")).strip(),
        "c2_exec_summary": str(obj.get("c2_exec_summary", "")).strip(),
        "c4_business_brand": str(obj.get("c4_business_brand", "")).strip(),
    }

    missing_keys = [k for k, v in result.items() if not v]
    if missing_keys:
        raise ValueError(f"AIレスポンスに必要項目が不足しています: {', '.join(missing_keys)}")

    return result