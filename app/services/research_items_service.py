from __future__ import annotations

import json
import os
import re
from typing import List

from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schemas.research_items import (
    AnalysisBlockInput,
    AnalysisResearchItem,
    QuestionType,
    ResearchItemsConfirmResponse,
    ResearchItemsGenerateResponse,
    ResearchItemsGenerateSummary,
    ResearchItemsPreviewPayload,
    ResearchItemsShortlistResponse,
    ResearchItemsShortlistSummary,
    ScreeningResearchItem,
)

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


QUESTION_TYPE_MAP = {
    "SA": "single",
    "MA": "multi",
    "FA": "free_text",
    "NUM": "numeric",
    "SG": "single_grid",
    "MG": "multi_grid",
    "single": "single",
    "multi": "multi",
    "free_text": "free_text",
    "numeric": "numeric",
    "single_grid": "single_grid",
    "multi_grid": "multi_grid",
}


def _normalize_question_type(value: str) -> QuestionType:
    if not value:
        return "single"
    normalized = QUESTION_TYPE_MAP.get(str(value).strip(), "single")
    return normalized  # type: ignore[return-value]


def _safe_json_load(text: str):
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return json.loads(text)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        key = item.strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _chunk_to_lines(text: str) -> List[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _fallback_screening_items(target_condition_text: str) -> List[ScreeningResearchItem]:
    base_questions = [
        {
            "question": "現在、このカテゴリの商品・サービスを利用していますか。",
            "question_type": "single",
            "choices_example": ["現在利用している", "以前利用していた", "利用したことはない"],
        },
        {
            "question": "直近3か月以内にこのカテゴリの商品・サービスを購入・利用しましたか。",
            "question_type": "single",
            "choices_example": ["はい", "いいえ"],
        },
        {
            "question": "このカテゴリの主要ブランドの中で認知しているものを教えてください。",
            "question_type": "multi",
            "choices_example": ["ブランドA", "ブランドB", "ブランドC", "どれも知らない"],
        },
        {
            "question": "あなたの年代を教えてください。",
            "question_type": "single",
            "choices_example": ["20代", "30代", "40代", "50代以上"],
        },
        {
            "question": "あなたの性別を教えてください。",
            "question_type": "single",
            "choices_example": ["男性", "女性", "その他", "回答しない"],
        },
        {
            "question": "居住エリアを教えてください。",
            "question_type": "single",
            "choices_example": ["首都圏", "中京圏", "関西圏", "その他"],
        },
        {
            "question": "このカテゴリへの関与度を教えてください。",
            "question_type": "single",
            "choices_example": ["非常に高い", "やや高い", "あまり高くない", "低い"],
        },
    ]

    result: List[ScreeningResearchItem] = []
    for i, q in enumerate(base_questions, start=1):
        result.append(
            ScreeningResearchItem(
                id=f"scr-{i:03d}",
                number=i,
                question=q["question"],
                question_type=_normalize_question_type(q["question_type"]),
                choices_example=q["choices_example"],
            )
        )
    return result


def _fallback_analysis_items(
    analysis_blocks: List[AnalysisBlockInput],
    selected_analysis_ids: List[str],
    min_analysis_questions: int,
) -> List[AnalysisResearchItem]:
    selected_blocks = [b for b in analysis_blocks if b.id in selected_analysis_ids]
    if not selected_blocks:
        selected_blocks = analysis_blocks

    if not selected_blocks:
        return []

    templates = [
        ("{subq}を把握するため、現状の認識・実態を教えてください。", "single", ["非常によく当てはまる", "やや当てはまる", "あまり当てはまらない", "まったく当てはまらない"]),
        ("{subq}に関して、特に重視する点を教えてください。", "multi", ["価格", "品質", "使いやすさ", "ブランド信頼"]),
        ("{subq}に関して、不満・障壁になっている点を教えてください。", "multi", ["情報不足", "価格が高い", "選びにくい", "魅力を感じない"]),
        ("{subq}に関して、比較時に確認する情報を教えてください。", "multi", ["口コミ", "スペック比較", "価格比較", "利用者評価"]),
        ("{subq}に関する評価を10点満点で教えてください。", "numeric", []),
        ("{subq}について、あなたの考えに最も近いものを選んでください。", "single", ["非常にそう思う", "ややそう思う", "どちらともいえない", "そう思わない"]),
    ]

    results: List[AnalysisResearchItem] = []
    counter = 1
    block_index = 0

    while len(results) < min_analysis_questions:
        block = selected_blocks[block_index % len(selected_blocks)]
        tpl = templates[len(results) % len(templates)]

        question = tpl[0].format(subq=block.subq or "該当テーマ")
        question_type = tpl[1]
        choices = tpl[2]

        results.append(
            AnalysisResearchItem(
                id=f"ana-{counter:03d}",
                number=counter,
                subq_id=block.id,
                subq=block.subq,
                source_analysis_id=block.id,
                question=question,
                question_type=_normalize_question_type(question_type),
                choices_example=choices,
                adoption_status="adopted",
                score=float(max(1, 100 - counter)),
                reason="初期生成で採用",
            )
        )
        counter += 1
        block_index += 1

    return results


def generate_screening_items_llm(
    orien_outline_text: str,
    target_condition_text: str,
) -> List[ScreeningResearchItem]:
    prompt = f"""
あなたは市場調査票設計の専門家です。
以下の調査対象者条件をもとに、対象者判定用のスクリーニング設問を作成してください。

# 要件
- 出力は JSON のみ
- 5〜10問程度
- 対象者条件に合致するかを判定できる設問にする
- 各設問には以下を含める
  - question
  - question_type
  - choices_example
- question_type は次のいずれか:
  ["single", "multi", "free_text", "numeric", "single_grid", "multi_grid"]
- アクセスパネル前提のため、以下のような設問は作成しないこと
  - 調査協力意思の確認
  - アンケート参加可否の確認
  - 過去の調査回答態度や回答不備歴の確認
  - 調査参加経験の適否確認
- 例えば、次のような設問は出力しないこと
  - 「調査にご協力いただけますか？」
  - 「過去に市場調査に参加した際、回答に不備や問題を指摘されたことはありますか？」
- あくまで、対象者条件に関係する属性・利用実態・購買経験・認知・関与度などの判定設問に限定する

# オリエン整理
{orien_outline_text[:3000]}

# 調査対象者条件
{target_condition_text[:3000]}

# 出力形式
{{
  "screening_items": [
    {{
      "question": "...",
      "question_type": "single",
      "choices_example": ["...", "..."]
    }}
  ]
}}
""".strip()

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=0.4,
        messages=[
            {"role": "system", "content": "あなたは市場調査票設計の専門家です。JSONのみを返してください。"},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content or ""
    data = _safe_json_load(content)
    raw_items = data.get("screening_items", [])

    result: List[ScreeningResearchItem] = []
    for i, item in enumerate(raw_items, start=1):
        result.append(
            ScreeningResearchItem(
                id=f"scr-{i:03d}",
                number=i,
                question=str(item.get("question", "")).strip(),
                question_type=_normalize_question_type(item.get("question_type", "single")),
                choices_example=_dedupe_keep_order(
                    [str(x).strip() for x in item.get("choices_example", []) if str(x).strip()]
                ),
            )
        )
    return result


def generate_analysis_items_llm(
    orien_outline_text: str,
    kickoff_text: str,
    subquestions_text: str,
    analysis_blocks: List[AnalysisBlockInput],
    selected_analysis_ids: List[str],
    min_analysis_questions: int,
) -> List[AnalysisResearchItem]:
    selected_blocks = [b for b in analysis_blocks if b.id in selected_analysis_ids]
    if not selected_blocks:
        selected_blocks = analysis_blocks

    analysis_blocks_payload = [
        {
            "id": b.id,
            "subq": b.subq,
            "approach": b.approach,
            "hypothesis": b.hypothesis,
            "axis": b.axis,
            "items": b.items,
        }
        for b in selected_blocks
    ]

    prompt = f"""
あなたは市場調査票設計の専門家です。
以下の情報をもとに、分析用の調査項目を最低 {min_analysis_questions} 問生成してください。

# 要件
- 出力は JSON のみ
- 必ず最低 {min_analysis_questions} 問
- サブクエスチョンごとにバランスよく配分する
- 各設問には以下を含める
  - subq_id
  - subq
  - source_analysis_id
  - question
  - question_type
  - choices_example
  - score
  - reason
- question_type は次のいずれか
  ["single", "multi", "free_text", "numeric", "single_grid", "multi_grid"]
- questionは質問文ではなく項目で表す。例：「あなたは次のサービスを知っていますか」の場合は、「サービス認知」とする。
- 比較軸と使用設問の意図を反映する
- 市場調査票として自然な日本語にする
- 重複を避ける
- 初期状態では全件 adoption_status = "adopted" とみなす想定

# オリエン整理
{orien_outline_text[:2500]}

# KON
{kickoff_text[:2500]}

# SQ
{subquestions_text[:2500]}

# 選択された分析アプローチ
{json.dumps(analysis_blocks_payload, ensure_ascii=False, indent=2)}

# 出力形式
{{
  "analysis_items": [
    {{
      "subq_id": "sq-01",
      "subq": "サブクエスチョン",
      "source_analysis_id": "analysis-01",
      "question": "設問項目",
      "question_type": "single",
      "choices_example": ["A", "B", "C"],
      "score": 95,
      "reason": "主問いに直結するため"
    }}
  ]
}}
""".strip()

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=0.5,
        messages=[
            {"role": "system", "content": "あなたは市場調査票設計の専門家です。JSONのみを返してください。"},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content or ""
    data = _safe_json_load(content)
    raw_items = data.get("analysis_items", [])

    results: List[AnalysisResearchItem] = []
    for i, item in enumerate(raw_items, start=1):
        results.append(
            AnalysisResearchItem(
                id=f"ana-{i:03d}",
                number=i,
                subq_id=str(item.get("subq_id", "")).strip() or f"sq-{i:03d}",
                subq=str(item.get("subq", "")).strip() or "未設定サブクエスチョン",
                source_analysis_id=str(item.get("source_analysis_id", "")).strip() or "unknown",
                question=str(item.get("question", "")).strip(),
                question_type=_normalize_question_type(item.get("question_type", "single")),
                choices_example=_dedupe_keep_order(
                    [str(x).strip() for x in item.get("choices_example", []) if str(x).strip()]
                ),
                adoption_status="adopted",
                score=float(item.get("score", 50)),
                reason=str(item.get("reason", "")).strip() or "初期生成",
            )
        )

    return results


def generate_research_items(
    orien_outline_text: str,
    kickoff_text: str,
    subquestions_text: str,
    target_condition_text: str,
    analysis_blocks: List[AnalysisBlockInput],
    selected_analysis_ids: List[str],
    min_analysis_questions: int,
) -> ResearchItemsGenerateResponse:
    try:
        screening_items = generate_screening_items_llm(
            orien_outline_text=orien_outline_text,
            target_condition_text=target_condition_text,
        )
        if not screening_items:
            screening_items = _fallback_screening_items(target_condition_text)
    except Exception:
        screening_items = _fallback_screening_items(target_condition_text)

    try:
        analysis_items = generate_analysis_items_llm(
            orien_outline_text=orien_outline_text,
            kickoff_text=kickoff_text,
            subquestions_text=subquestions_text,
            analysis_blocks=analysis_blocks,
            selected_analysis_ids=selected_analysis_ids,
            min_analysis_questions=min_analysis_questions,
        )
        if len(analysis_items) < min_analysis_questions:
            analysis_items = _fallback_analysis_items(
                analysis_blocks=analysis_blocks,
                selected_analysis_ids=selected_analysis_ids,
                min_analysis_questions=min_analysis_questions,
            )
    except Exception:
        analysis_items = _fallback_analysis_items(
            analysis_blocks=analysis_blocks,
            selected_analysis_ids=selected_analysis_ids,
            min_analysis_questions=min_analysis_questions,
        )

    return ResearchItemsGenerateResponse(
        screening_items=screening_items,
        analysis_items=analysis_items,
        summary=ResearchItemsGenerateSummary(
            screening_count=len(screening_items),
            analysis_count=len(analysis_items),
        ),
    )


def shortlist_research_items(
    analysis_items: List[AnalysisResearchItem],
    desired_count: int,
) -> ResearchItemsShortlistResponse:
    before_count = len(analysis_items)

    sorted_items = sorted(
        analysis_items,
        key=lambda x: (x.score if x.score is not None else 0),
        reverse=True,
    )

    shortlisted = []
    for idx, item in enumerate(sorted_items):
        adopted = idx < desired_count
        shortlisted.append(
            item.model_copy(
                update={
                    "number": idx + 1,
                    "adoption_status": "adopted" if adopted else "rejected",
                }
            )
        )

    return ResearchItemsShortlistResponse(
        analysis_items=shortlisted,
        summary=ResearchItemsShortlistSummary(
            before_count=before_count,
            after_count=sum(1 for x in shortlisted if x.adoption_status == "adopted"),
        ),
    )


def confirm_research_items(
    screening_items: List[ScreeningResearchItem],
    analysis_items: List[AnalysisResearchItem],
) -> ResearchItemsConfirmResponse:
    confirmed_analysis_items = [
        item for item in analysis_items if item.adoption_status == "adopted"
    ]

    for idx, item in enumerate(screening_items, start=1):
        item.number = idx

    for idx, item in enumerate(confirmed_analysis_items, start=1):
        item.number = idx

    return ResearchItemsConfirmResponse(
        confirmed_screening_items=screening_items,
        confirmed_analysis_items=confirmed_analysis_items,
        preview_payload=ResearchItemsPreviewPayload(
            slide_title="調査項目案",
            screening_items=screening_items,
            analysis_items=confirmed_analysis_items,
        ),
        summary=ResearchItemsShortlistSummary(
            before_count=len(analysis_items),
            after_count=len(confirmed_analysis_items),
        ),
    )