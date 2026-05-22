from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AzureOpenAI


DEFAULT_MAX_BLOCKS = 5
DEFAULT_INITIAL_SELECTED = 3
DEFAULT_MAX_SELECTABLE = 5

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


def _safe_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []

        # 「A、B、C」「A,B,C」「A・B・C」も軽く分割
        for sep in ["、", ",", "・", "\n"]:
            if sep in text:
                return [x.strip() for x in text.split(sep) if x.strip()]

        return [text]

    if isinstance(value, (list, tuple)):
        results: List[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                results.append(text)
        return results

    text = str(value).strip()
    return [text] if text else []


def _pick_subq_text(subq_item: Any) -> str:
    if isinstance(subq_item, dict):
        return str(
            subq_item.get("subq")
            or subq_item.get("question")
            or ""
        ).strip()

    return str(
        getattr(subq_item, "subq", None)
        or getattr(subq_item, "question", None)
        or ""
    ).strip()


def _pick_axis(subq_item: Any) -> List[str]:
    if isinstance(subq_item, dict):
        return _safe_list(subq_item.get("axis"))

    return _safe_list(getattr(subq_item, "axis", None))


def _pick_items(subq_item: Any) -> List[str]:
    if isinstance(subq_item, dict):
        return _safe_list(subq_item.get("items"))

    return _safe_list(getattr(subq_item, "items", None))


def _pick_id(subq_item: Any, idx: int) -> str:
    if isinstance(subq_item, dict):
        return str(subq_item.get("id") or f"SQ{idx}").strip()

    return str(getattr(subq_item, "id", None) or f"SQ{idx}").strip()


def _dedupe_subqs(subq_list: List[Any]) -> List[Any]:
    seen = set()
    unique_items = []

    for item in subq_list:
        subq = _pick_subq_text(item)
        key = subq.strip()
        if not key:
            continue
        if key in seen:
            continue

        seen.add(key)
        unique_items.append(item)

    return unique_items


def _priority_for_index(idx: int) -> str:
    if idx <= 3:
        return "recommended"
    if idx <= 5:
        return "candidate"
    return "excluded"


def _score_for_index(idx: int, priority: str) -> int:
    base_map = {
        "recommended": 95,
        "candidate": 78,
        "excluded": 55,
    }
    base = base_map.get(priority, 60)
    return max(base - (idx - 1) * 3, 0)


def _fallback_approach_text(subq: str, axis: List[str], items: List[str]) -> str:
    axis_part = "・".join(axis[:2]) if axis else "対象者属性・行動差分"
    item_part = "、".join(items[:3]) if items else "主要評価指標"

    return (
        f"{axis_part}を切り口として、{item_part}を比較・整理し、"
        f"「{subq}」に対する示唆を抽出する。"
    )


def _fallback_hypothesis_text(subq: str, axis: List[str], items: List[str]) -> str:
    if axis:
        return f"{axis[0]}によって認識・評価・行動に差があり、「{subq}」の答えが変わる可能性がある。"
    if items:
        return f"{items[0]}の評価差が、「{subq}」を説明する主要要因になっている可能性がある。"
    return f"対象者ごとの認識・評価・行動差が、「{subq}」の背景要因になっている可能性がある。"


def _fallback_selection_reason(priority: str) -> str:
    if priority == "recommended":
        return "主問いへの回答ストーリーを構成する中核論点のため、優先的に検証すべき。"
    if priority == "candidate":
        return "主問いを補完する論点として有効だが、優先論点との重複を確認しながら扱うべき。"
    return "現時点では優先度が低く、他の論点を優先すべき。"


def _normalize_llm_blocks(
    obj: Any,
    source_items: List[Dict[str, Any]],
    initial_selected: int,
) -> List[Dict[str, Any]]:
    if not isinstance(obj, list):
        raise ValueError("LLM output is not a JSON array.")

    blocks: List[Dict[str, Any]] = []

    for idx, source in enumerate(source_items, start=1):
        generated = obj[idx - 1] if idx - 1 < len(obj) and isinstance(obj[idx - 1], dict) else {}

        subq = str(generated.get("subq") or source["subq"]).strip()
        axis = _safe_list(generated.get("axis") or source["axis"])
        items = _safe_list(generated.get("items") or source["items"])

        priority = str(generated.get("priority") or _priority_for_index(idx)).strip()
        if priority not in ["recommended", "candidate", "excluded"]:
            priority = _priority_for_index(idx)

        score_raw = generated.get("score")
        try:
            score = int(score_raw)
        except Exception:
            score = _score_for_index(idx, priority)

        approach = str(generated.get("approach") or "").strip()
        if not approach:
            approach = _fallback_approach_text(subq=subq, axis=axis, items=items)

        hypothesis = str(generated.get("hypothesis") or "").strip()
        if not hypothesis:
            hypothesis = _fallback_hypothesis_text(subq=subq, axis=axis, items=items)

        selection_reason = str(generated.get("selection_reason") or "").strip()
        if not selection_reason:
            selection_reason = _fallback_selection_reason(priority)

        block = {
            "id": f"ap-{idx:02d}",
            "source_subq_ids": [source["source_subq_id"]],
            "subq": subq,
            "axis": axis,
            "items": items,
            "approach": approach,
            "hypothesis": hypothesis,
            "priority": priority,
            "score": score,
            "selection_reason": selection_reason,
            "selected": idx <= initial_selected,
        }
        blocks.append(block)

    blocks.sort(key=lambda x: x["score"], reverse=True)

    for i, block in enumerate(blocks):
        block["selected"] = i < min(initial_selected, len(blocks))

    return blocks


def _generate_blocks_by_llm(
    source_items: List[Dict[str, Any]],
    initial_selected: int,
) -> List[Dict[str, Any]]:
    prompt = f"""
あなたは市場調査の分析設計に強いリサーチディレクターです。
以下のサブクエスチョン一覧をもとに、各SQに対応する分析アプローチと想定仮説を生成してください。

【重要】
- 入力されたSQは、画面上でユーザーが編集した後の最新版です。
- 必ず、この最新版SQの文意を最優先して分析アプローチと想定仮説を作成してください。
- 古いSQや一般論に引っ張られず、subq / axis / items の内容に基づいて再設計してください。
- axisは分析の切り口のことでターゲットの特性やブランドへの態度などが入ることが多いです。優先度の高いもの1つを提示してください。
- approach は「どの切り口で、何を比較・確認し、どのような示唆を出すか」が分かる文にしてください。また定性調査の利用は提案しないでください。
- hypothesis は「分析前に置く検証仮説」として、具体的にしてください。
- priority は recommended / candidate / excluded のいずれかにしてください。
- score は 0〜100 の整数にしてください。
- 出力はJSON配列のみ。説明文、Markdown、コードブロックは不要です。

【入力SQ一覧】
{json.dumps(source_items, ensure_ascii=False, indent=2)}

【出力形式】
[
  {{
    "subq": "SQ本文",
    "axis": ["分析軸1", "分析軸2"],
    "items": ["確認項目1", "確認項目2", "確認項目3"],
    "approach": "分析アプローチ本文",
    "hypothesis": "想定仮説本文",
    "priority": "recommended",
    "score": 95,
    "selection_reason": "この分析を優先する理由"
  }}
]
""".strip()

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "あなたは市場調査の分析設計に強いリサーチディレクターです。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=3000,
    )

    ai_text = response.choices[0].message.content or ""
    ai_text = _strip_code_fence(ai_text)

    try:
        obj = json.loads(ai_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM output is not valid JSON: {ai_text}") from exc

    return _normalize_llm_blocks(
        obj=obj,
        source_items=source_items,
        initial_selected=initial_selected,
    )


def _generate_blocks_by_fallback(
    source_items: List[Dict[str, Any]],
    initial_selected: int,
) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []

    for idx, source in enumerate(source_items, start=1):
        subq = source["subq"]
        axis = source["axis"]
        items = source["items"]

        priority = _priority_for_index(idx)
        score = _score_for_index(idx, priority)

        blocks.append(
            {
                "id": f"ap-{idx:02d}",
                "source_subq_ids": [source["source_subq_id"]],
                "subq": subq,
                "axis": axis,
                "items": items,
                "approach": _fallback_approach_text(subq=subq, axis=axis, items=items),
                "hypothesis": _fallback_hypothesis_text(subq=subq, axis=axis, items=items),
                "priority": priority,
                "score": score,
                "selection_reason": _fallback_selection_reason(priority),
                "selected": idx <= initial_selected,
            }
        )

    blocks.sort(key=lambda x: x["score"], reverse=True)

    for i, block in enumerate(blocks):
        block["selected"] = i < min(initial_selected, len(blocks))

    return blocks


def generate_analysis_approach_draft(
    subq_list: List[Any],
    max_blocks: int = DEFAULT_MAX_BLOCKS,
    initial_selected: int = DEFAULT_INITIAL_SELECTED,
    max_selectable: int = DEFAULT_MAX_SELECTABLE,
) -> Dict[str, Any]:
    """
    編集済み subq_list をもとに、分析アプローチと想定仮説をLLMで生成する。

    返却形式:
    {
      "analysis_blocks": [...],
      "selection_summary": {
        "selected_count": 3,
        "max_selectable": 5
      }
    }
    """
    if not subq_list:
        return {
            "analysis_blocks": [],
            "selection_summary": {
                "selected_count": 0,
                "max_selectable": max_selectable,
            },
        }

    unique_subqs = _dedupe_subqs(subq_list)
    target_items = unique_subqs[:max_blocks]

    source_items: List[Dict[str, Any]] = []

    for idx, sq in enumerate(target_items, start=1):
        subq = _pick_subq_text(sq)
        if not subq:
            continue

        source_items.append(
            {
                "source_subq_id": _pick_id(sq, idx),
                "subq": subq,
                "axis": _pick_axis(sq),
                "items": _pick_items(sq),
            }
        )

    if not source_items:
        return {
            "analysis_blocks": [],
            "selection_summary": {
                "selected_count": 0,
                "max_selectable": max_selectable,
            },
        }

    try:
        analysis_blocks = _generate_blocks_by_llm(
            source_items=source_items,
            initial_selected=initial_selected,
        )
    except Exception:
        # LLMのJSON崩れや一時エラー時も画面が止まらないよう、最低限の生成にフォールバック
        analysis_blocks = _generate_blocks_by_fallback(
            source_items=source_items,
            initial_selected=initial_selected,
        )

    selected_count = sum(1 for b in analysis_blocks if b["selected"])

    return {
        "analysis_blocks": analysis_blocks,
        "selection_summary": {
            "selected_count": selected_count,
            "max_selectable": max_selectable,
        },
    }