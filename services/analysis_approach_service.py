from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_MAX_BLOCKS = 5
DEFAULT_INITIAL_SELECTED = 3
DEFAULT_MAX_SELECTABLE = 5


def _safe_list(value: Any) -> List[str]:
    """
    値を必ず list[str] に寄せる。
    None -> []
    str -> [str]
    list/tuple -> str化して返す
    それ以外 -> [str(value)]
    """
    if value is None:
        return []

    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []

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
    """
    subq オブジェクト/辞書のどちらでも問い文を取り出せるようにする。
    """
    if isinstance(subq_item, dict):
        return (
            str(subq_item.get("subq") or subq_item.get("question") or "")
            .strip()
        )

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


def _priority_for_index(idx: int, total_count: int) -> str:
    """
    idx は 1 始まり
    基本ルール:
      1-3: recommended
      4-5: candidate
      6以降: excluded
    """
    if idx <= 3:
        return "recommended"
    if idx <= 5:
        return "candidate"
    return "excluded"


def _score_for_index(idx: int, priority: str) -> int:
    """
    仮のスコアリング。
    UI選択順の初期整列用として十分な単純ルール。
    """
    base_map = {
        "recommended": 95,
        "candidate": 78,
        "excluded": 55,
    }
    base = base_map.get(priority, 60)
    score = base - (idx - 1) * 3
    return max(score, 0)


def _selection_reason(subq: str, priority: str, axis: List[str], items: List[str]) -> str:
    """
    UI表示用の簡易理由文。
    """
    if priority == "recommended":
        if axis:
            return f"主問いとの関連が高く、分析軸（{axis[0]}）で具体化しやすいため"
        return "主問いとの関連が高く、優先的に検証すべき論点のため"

    if priority == "candidate":
        if items:
            return f"補助的な観点として有効で、確認項目（{items[0]}）に展開しやすいため"
        return "主問いを補完する観点として有効なため"

    return "現時点では優先度が低く、他候補を優先すべきため"


def _build_approach_text(subq: str, axis: List[str], items: List[str]) -> str:
    """
    分析アプローチ文の仮生成。
    """
    axis_part = "・".join(axis[:2]) if axis else "対象差分"
    item_part = "、".join(items[:3]) if items else "主要指標"

    return (
        f"{subq}を明らかにするために、{axis_part}を切り口として"
        f"{item_part}を比較・整理し、傾向差と示唆を抽出する。"
    )


def _build_hypothesis_text(subq: str, axis: List[str], items: List[str]) -> str:
    """
    仮説文の仮生成。
    """
    if axis:
        return f"{axis[0]}ごとに認識や評価に差があり、{subq}に影響している可能性がある。"
    if items:
        return f"{items[0]}の評価差が、{subq}の背景要因になっている可能性がある。"
    return "セグメント差または評価差が存在し、問いに対する説明要因になっている可能性がある。"


def _dedupe_subqs(subq_list: List[Any]) -> List[Any]:
    """
    同じ問い文が重複している場合は先頭のみ採用。
    """
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


def generate_analysis_approach_draft(
    subq_list: List[Any],
    max_blocks: int = DEFAULT_MAX_BLOCKS,
    initial_selected: int = DEFAULT_INITIAL_SELECTED,
    max_selectable: int = DEFAULT_MAX_SELECTABLE,
) -> Dict[str, Any]:
    """
    subq_list から複数の analysis_blocks をルールベースで生成する。

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

    # 最低3件、最大6件が理想だが、まずは最大5件で安定運用
    target_items = unique_subqs[:max_blocks]

    analysis_blocks: List[Dict[str, Any]] = []

    for idx, sq in enumerate(target_items, start=1):
        subq = _pick_subq_text(sq)
        axis = _pick_axis(sq)
        items = _pick_items(sq)

        priority = _priority_for_index(idx=idx, total_count=len(target_items))
        score = _score_for_index(idx=idx, priority=priority)
        selected = idx <= initial_selected

        block = {
            "id": f"ap-{idx:02d}",
            "source_subq_ids": [f"sq-{idx:02d}"],
            "subq": subq,
            "axis": axis,
            "items": items,
            "approach": _build_approach_text(subq=subq, axis=axis, items=items),
            "hypothesis": _build_hypothesis_text(subq=subq, axis=axis, items=items),
            "priority": priority,
            "score": score,
            "selection_reason": _selection_reason(
                subq=subq,
                priority=priority,
                axis=axis,
                items=items,
            ),
            "selected": selected,
        }
        analysis_blocks.append(block)

    # score降順で明示ソートして返す
    analysis_blocks.sort(key=lambda x: x["score"], reverse=True)

    # selected を score順の上位 initial_selected 件に再設定
    for i, block in enumerate(analysis_blocks):
        block["selected"] = i < min(initial_selected, len(analysis_blocks))

    selected_count = sum(1 for b in analysis_blocks if b["selected"])

    return {
        "analysis_blocks": analysis_blocks,
        "selection_summary": {
            "selected_count": selected_count,
            "max_selectable": max_selectable,
        },
    }