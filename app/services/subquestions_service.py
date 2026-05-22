import json
import os
from typing import List

from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schemas.subquestions import SubQuestionItem, SubQuestionsResponse

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
MAX_SUBQUESTIONS = 3


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    return text.strip()


def _normalize_subq_list(items: list) -> List[SubQuestionItem]:
    if not isinstance(items, list):
        raise ValueError("LLM output is not a JSON array.")

    cleaned: List[SubQuestionItem] = []

    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        subq = str(item.get("subq", "")).strip()
        if not subq:
            continue

        cleaned.append(
            SubQuestionItem(
                id=str(item.get("id") or f"SQ{i}").strip(),
                chapter_role=str(item.get("chapter_role", "")).strip(),
                subq=subq,
                axis=str(item.get("axis", "")).strip(),
                items=str(item.get("items", "")).strip(),
                report_image=str(item.get("report_image", "")).strip(),
            )
        )

        if len(cleaned) >= MAX_SUBQUESTIONS:
            break

    if not cleaned:
        raise ValueError("No valid subquestions were generated.")

    for idx, row in enumerate(cleaned, start=1):
        row.id = f"SQ{idx}"

    return cleaned


def generate_subquestions_draft(
    orien_outline_text: str,
    selected_axis_text: str,
    main_question: str,
) -> SubQuestionsResponse:
    orien_outline_text = (orien_outline_text or "").strip()
    selected_axis_text = (selected_axis_text or "").strip()
    main_question = (main_question or "").strip()

    if not orien_outline_text:
        raise ValueError("orien_outline_text is required.")
    if not selected_axis_text:
        raise ValueError("selected_axis_text is required.")
    if not main_question:
        raise ValueError("main_question is required.")

    prompt = f"""
あなたは市場調査設計とレポート構成設計の専門家です。
キックオフノートの「メインクエスチョン」に答えるために、サブクエスチョンを設計してください。

【最重要ルール】
- サブクエスチョンは、単なる思いつきの問いを3つ並べるのではなく、構造化した設計にすること
- SQ1 → SQ2 → SQ3 の順番に読むと、メインクエスチョンに答えるためのストーリーになること
- 例：SQ1は「現状把握」、SQ2は「要因・背景分析」、SQ3は「判断・施策示唆」のような役割を持たせる
- 3つのSQを並列の論点にしないこと
- 各SQは、レポートの各章で何を明らかにするかが分かる問いにすること
- 「選択された課題視点」と「オリエン内容」は、メインクエスチョンの意味を補足するためだけに使うこと
- メインクエスチョンに含まれない論点を、補助情報から無理に追加しないこと
- メインクエスチョンが意味不明、短すぎる、または市場調査の問いとして成立しない場合は、必ず空配列 [] のみを返すこと


【入力データ】
▼メインクエスチョン
{main_question[:1500]}

▼補助情報：選択された課題視点
{selected_axis_text[:800]}

▼補助情報：オリエン内容の整理
{orien_outline_text[:1200]}

【出力要件】
- 出力は JSON 配列のみ
- 前置き、説明文、コードブロック、Markdown記号は不要
- 要素数は必ず最大 {MAX_SUBQUESTIONS} 件
- 各要素は必ず次のキーを持つこと
  - id
  - chapter_role
  - subq
  - axis
  - items


【各キーの意味】
- id：SQ1、SQ2、SQ3
- chapter_role：そのSQがレポート上で担う役割。例：現状把握、要因・背景分析、判断・施策示唆
- subq：章の中心となる問い
- axis：axisは分析の切り口のことでターゲットの特性やブランドへの態度などが入ることが多いです。
- items：調査票・集計で見るべき調査項目案


]
""".strip()

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": "あなたは市場調査設計の専門家です。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=2000,
    )

    ai_text = response.choices[0].message.content or ""
    ai_text = _strip_code_fence(ai_text)

    try:
        obj = json.loads(ai_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM output is not valid JSON: {ai_text}") from exc

    subq_list = _normalize_subq_list(obj)
    return SubQuestionsResponse(subq_list=subq_list)