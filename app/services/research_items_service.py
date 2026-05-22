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

QUESTION_TYPE_DISPLAY_MAP = {
    "single": "SA",
    "multi": "MA",
    "numeric": "数値",
    "free_text": "FA",
    "single_grid": "SA表",
    "multi_grid": "MA表",
}


def to_question_type_display(value: str) -> str:
    return QUESTION_TYPE_DISPLAY_MAP.get(str(value or "").strip(), value)

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
- question は質問文ではなく「調査項目名」として出力する
- 「あなたは〜ですか」「〜をお答えください」「〜を教えてください」のような質問文は禁止
- 項目名は10〜20文字程度の名詞句にする
- 例：
  - 「あなたのご存じブランドをすべてお答えください。」→「ブランド認知」
  - 「購入時に重視する点を教えてください。」→「購入重視点」
  - 「現在利用しているサービスを教えてください。」→「利用サービス」
  - 「満足度を10点満点で教えてください。」→「総合満足度」
- choices_example は必ず配列で返す
- numeric の場合も choices_example は null ではなく空配列 [] にする

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
    print("[research_items] screening raw content:", content[:2000])
    data = _safe_json_load(content)
    raw_items = data.get("screening_items", [])

    result: List[ScreeningResearchItem] = []
    for i, item in enumerate(raw_items, start=1):
        choices_raw = item.get("choices_example") or []

        result.append(
            ScreeningResearchItem(
                id=f"scr-{i:03d}",
                number=i,
                question=str(item.get("question", "")).strip(),
                question_type=_normalize_question_type(item.get("question_type", "single")),
                choices_example=_dedupe_keep_order(
                    [str(x).strip() for x in choices_raw if str(x).strip()]
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
以下の情報をもとに、分析用の調査項目を生成してください。

# 要件
- 出力は JSON のみ
- サブクエスチョンごとにバランスよく配分する
- 各設問には以下を含める
  - subq_id
  - subq
  - source_analysis_id
  - question
  - question_type
  - choices_example
- question_type は次のいずれか
  ["single", "multi", "single_grid", "multi_grid"]
- 自由記入（"free_text"）で生成した方がよいと思う項目は、回答仮説をプリコードした選択肢をセットしたmulti形式で提案してください。  
- 数値項目（"numeric"）で生成した方がよいと思う項目は、回答をプリコード（10回未満、20回未満など）したsingle形式で提案してください。  
- question は質問文ではなく「調査項目名」として出力する
- 「あなたは〜ですか」「〜をお答えください」「〜を教えてください」のような質問文は禁止
- 項目名は10〜20文字程度の名詞句にする
- 例：
  - 「あなたのご存じブランドをすべてお答えください。」→「ブランド認知」
  - 「購入時に重視する点を教えてください。」→「購入重視点」
  - 「現在利用しているサービスを教えてください。」→「利用サービス」
  - 「満足度を10点満点で教えてください。」→「総合満足度」
- 選択された分析アプローチの items は「使用設問案」であり、調査項目生成の重要項目とする
- ただし、items は必須・中核項目の候補として扱い、approach / hypothesis / subq を踏まえて、分析に必要な周辺項目・比較項目・背景項目・阻害要因項目も追加する
- 各 analysis_block につき、以下の比率を目安に調査項目を構成する
  - 50〜60%：items に含まれる使用設問案を具体化した項目
  - 40〜50%：subq / approach / hypothesis から発想を広げた補完項目
- items にない項目を追加する場合も、必ずその analysis_block の subq と approach に紐づくものにする
- 単なる一般的な設問や、分析目的と関係の薄い項目は追加しない
- reason には、その項目が items 由来なのか、分析補完として追加したものなのかが分かるように記載する
- approach と hypothesis は、items の優先順位や設問意図を補足するために使う
- 重複を避ける

# 件数配分
- analysis_itemsは、選択された analysis_block が3件の場合、analysis_blockとごに最低10件ずつ生成する
- analysis_itemsは、選択された analysis_block が2件の場合、analysis_blockとごに最低15件ずつ生成する
- analysis_itemsは、選択された analysis_block が1件の場合、analysis_blockに最低20件生成する



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
    print("[research_items] analysis raw content:", content[:2000])
    data = _safe_json_load(content)
    raw_items = data.get("analysis_items", [])

    results: List[AnalysisResearchItem] = []
    for i, item in enumerate(raw_items, start=1):
        choices_raw = item.get("choices_example") or []

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
                    [str(x).strip() for x in choices_raw if str(x).strip()]
                ),
                adoption_status="adopted",
                score=float(item.get("score") or 50),
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
    screening_items = generate_screening_items_llm(
        orien_outline_text=orien_outline_text,
        target_condition_text=target_condition_text,
    )

    if not screening_items:
        raise ValueError(
            "スクリーニング調査項目を生成できませんでした。target_condition_text やオリエン整理の内容を確認してください。"
        )

    analysis_items = generate_analysis_items_llm(
        orien_outline_text=orien_outline_text,
        kickoff_text=kickoff_text,
        subquestions_text=subquestions_text,
        analysis_blocks=analysis_blocks,
        selected_analysis_ids=selected_analysis_ids,
        min_analysis_questions=min_analysis_questions,
    )

    if not analysis_items:
        raise ValueError(
            "本調査項目を生成できませんでした。分析アプローチ、SQ、KONの内容を確認してください。"
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