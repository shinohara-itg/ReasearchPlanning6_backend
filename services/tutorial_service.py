import json
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schemas.tutorial import (
    AnalysisSuggestion,
    SlidePlan,
    SlidePlanItem,
    TutorialOption,
    TutorialPlanResponse,
    TutorialQuestionBlock,
    TutorialRefreshResponse,
    TutorialSummary,
)

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


Q1_MARKET = "market_overview"
Q1_STP = "target_strategy"
Q1_4P = "measure_evaluation"

Q2_FOCUS = "theme_only"
Q2_TARGET = "include_target"
Q2_MARKET = "include_market"


def build_tutorial_plan(
    orien_outline_text: str,
    manual_text: Optional[str] = None,
    extracted_texts: Optional[List[str]] = None,
) -> TutorialPlanResponse:
    source_text = _merge_texts(orien_outline_text, manual_text, extracted_texts)

    detected_theme = _detect_q1_theme(source_text)
    detected_scope = _detect_q2_scope(source_text, detected_theme)
    contact_eval_type = _detect_contact_eval_type(source_text)
    reasoning = _build_reasoning(
        source_text, detected_theme, detected_scope, contact_eval_type
    )

    q1_default_wording = _get_q1_wording(source_text, contact_eval_type)
    q2_default_wording = _get_q2_wording(detected_theme, contact_eval_type)

    ai_wording = _generate_ai_tutorial_wording(
        orien_outline_text=orien_outline_text,
        manual_text=manual_text,
        extracted_texts=extracted_texts,
        detected_theme=detected_theme,
        detected_scope=detected_scope,
        contact_eval_type=contact_eval_type,
        q1_default_wording=q1_default_wording,
        q2_default_wording=q2_default_wording,
    )

    q1_wording = _merge_ai_wording(
        default_wording=q1_default_wording,
        ai_wording=ai_wording.get("q1_options", {}),
        allowed_keys=[Q1_MARKET, Q1_STP, Q1_4P],
    )
    q2_wording = _merge_ai_wording(
        default_wording=q2_default_wording,
        ai_wording=ai_wording.get("q2_options", {}),
        allowed_keys=[Q2_FOCUS, Q2_TARGET, Q2_MARKET],
    )

    q1 = _build_q1_block(
        selected_key=detected_theme,
        wording=q1_wording,
    )
    q2 = _build_q2_block(
        selected_key=detected_scope,
        wording=q2_wording,
    )
    q3 = _build_q3_suggestions(detected_theme, detected_scope)
    slide_plan = _build_slide_plan(detected_theme, detected_scope)

    summary = TutorialSummary(
        detected_theme=detected_theme,
        detected_scope=detected_scope,
        contact_evaluation_type=contact_eval_type,
        reasoning=reasoning,
        notes=_build_notes(detected_theme, contact_eval_type),
    )

    return TutorialPlanResponse(
        tutorial_summary=summary,
        q1=q1,
        q2=q2,
        q3=q3,
        slide_plan=slide_plan,
    )


def refresh_tutorial_plan(
    orien_outline_text: str,
    q1_selected_key: str,
    q2_selected_key: str,
) -> TutorialRefreshResponse:
    _ = orien_outline_text

    q3 = _build_q3_suggestions(q1_selected_key, q2_selected_key)
    slide_plan = _build_slide_plan(q1_selected_key, q2_selected_key)

    return TutorialRefreshResponse(
        q3=q3,
        slide_plan=slide_plan,
    )


def _merge_texts(
    orien_outline_text: str,
    manual_text: Optional[str],
    extracted_texts: Optional[List[str]],
) -> str:
    parts = [orien_outline_text or ""]
    if manual_text:
        parts.append(manual_text)
    if extracted_texts:
        parts.extend([t for t in extracted_texts if t])
    return "\n".join(parts).lower()


def _detect_q1_theme(text: str) -> str:
    score_market = 0
    score_stp = 0
    score_4p = 0

    market_keywords = [
        "市場",
        "顧客",
        "全体像",
        "構造",
        "実態",
        "理解",
        "把握",
        "ニーズ",
        "生活者",
        "カテゴリ",
    ]
    stp_keywords = [
        "ターゲット",
        "セグメント",
        "狙う",
        "ポジション",
        "競合",
        "差別化",
        "stp",
        "誰に",
        "ターゲティング",
    ]
    p4_keywords = [
        "広告",
        "店頭",
        "施策",
        "認知",
        "比較検討",
        "商品",
        "サービス",
        "接点",
        "訴求",
        "効果",
        "評価",
        "ブランド",
    ]

    for kw in market_keywords:
        if kw in text:
            score_market += 1
    for kw in stp_keywords:
        if kw in text:
            score_stp += 1
    for kw in p4_keywords:
        if kw in text:
            score_4p += 1

    scores = {
        Q1_MARKET: score_market,
        Q1_STP: score_stp,
        Q1_4P: score_4p,
    }

    best_key = max(scores, key=scores.get)
    if scores[best_key] == 0:
        return Q1_STP
    return best_key


def _detect_q2_scope(text: str, detected_theme: str) -> str:
    market_signals = ["市場全体", "カテゴリ理解", "生活者理解", "顧客理解", "市場構造"]
    target_signals = ["ターゲット", "誰に", "セグメント", "ポジション", "競合"]
    direct_eval_signals = ["施策評価", "広告評価", "接点評価", "効果測定", "店頭評価"]

    if any(kw in text for kw in market_signals):
        return Q2_MARKET
    if any(kw in text for kw in target_signals):
        return Q2_TARGET
    if any(kw in text for kw in direct_eval_signals):
        return Q2_FOCUS

    if detected_theme == Q1_MARKET:
        return Q2_MARKET
    if detected_theme == Q1_STP:
        return Q2_TARGET
    return Q2_TARGET


def _detect_contact_eval_type(text: str) -> Optional[str]:
    if any(kw in text for kw in ["広告", "cm", "sns", "動画", "認知"]):
        return "advertising_awareness"
    if any(kw in text for kw in ["店頭", "売場", "棚", "陳列", "販促物"]):
        return "instore_consideration"
    if any(kw in text for kw in ["商品", "サービス体験", "利用体験", "使用感", "機能評価"]):
        return "product_service_experience"
    if any(kw in text for kw in ["ブランド", "企業", "コーポレート", "好意", "信頼"]):
        return "brand_corporate_understanding"
    return None


def _build_reasoning(
    text: str,
    detected_theme: str,
    detected_scope: str,
    contact_eval_type: Optional[str],
) -> List[str]:
    reasons = []

    if detected_theme == Q1_MARKET:
        reasons.append("市場・顧客・全体像に関する記述が多いため、主題は市場理解寄りと判断しました。")
    elif detected_theme == Q1_STP:
        reasons.append("ターゲット・競合・ポジションに関する記述が見られるため、主題はSTP整理寄りと判断しました。")
    else:
        reasons.append("施策・接点・広告・商品評価に関する記述が見られるため、主題は4P評価寄りと判断しました。")

    if detected_scope == Q2_FOCUS:
        reasons.append("今回テーマへの直接回答を優先する構成が適していると判断しました。")
    elif detected_scope == Q2_TARGET:
        reasons.append("施策評価だけでなく、誰に向けた施策かの整理まで含めた方が企画として自然と判断しました。")
    else:
        reasons.append("市場全体や顧客構造の前提整理から含めた方が、提案の納得性が高いと判断しました。")

    if contact_eval_type:
        reasons.append(f"施策評価系の詳細タイプは {contact_eval_type} と暫定判定しました。")

    if len(text.strip()) < 40:
        reasons.append("入力情報がまだ少ないため、一部は標準的な推奨パターンで補っています。")

    return reasons


def _build_notes(detected_theme: str, contact_eval_type: Optional[str]) -> List[str]:
    notes = []

    if detected_theme == Q1_4P and contact_eval_type:
        mapping = {
            "advertising_awareness": "広告・認知接点の評価として扱うと、接触/非接触比較が中心になります。",
            "instore_consideration": "店頭・比較検討接点の評価として扱うと、比較検討有無や売場接点比較が中心になります。",
            "product_service_experience": "商品/サービス体験の評価として扱うと、利用状況別の差分確認が中心になります。",
            "brand_corporate_understanding": "ブランド/コーポレート理解の評価として扱うと、認知や好意の差分確認が中心になります。",
        }
        note = mapping.get(contact_eval_type)
        if note:
            notes.append(note)

    return notes


def _build_q1_block(
    selected_key: str,
    wording: Dict[str, Dict[str, str]],
) -> TutorialQuestionBlock:
    options = [
        TutorialOption(
            key=Q1_MARKET,
            title=wording[Q1_MARKET]["title"],
            description=wording[Q1_MARKET]["description"],
            recommended=(selected_key == Q1_MARKET),
        ),
        TutorialOption(
            key=Q1_STP,
            title=wording[Q1_STP]["title"],
            description=wording[Q1_STP]["description"],
            recommended=(selected_key == Q1_STP),
        ),
        TutorialOption(
            key=Q1_4P,
            title=wording[Q1_4P]["title"],
            description=wording[Q1_4P]["description"],
            recommended=(selected_key == Q1_4P),
        ),
    ]

    return TutorialQuestionBlock(
        question_key="q1",
        title="この調査で一番知りたいことは？",
        description="今回の案件内容に合わせて、主題に近いものを選んでください",
        options=options,
        recommended_key=selected_key,
        selected_key=selected_key,
    )


def _build_q2_block(
    selected_key: str,
    wording: Dict[str, Dict[str, str]],
) -> TutorialQuestionBlock:
    options = [
        TutorialOption(
            key=Q2_FOCUS,
            title=wording[Q2_FOCUS]["title"],
            description=wording[Q2_FOCUS]["description"],
            recommended=(selected_key == Q2_FOCUS),
        ),
        TutorialOption(
            key=Q2_TARGET,
            title=wording[Q2_TARGET]["title"],
            description=wording[Q2_TARGET]["description"],
            recommended=(selected_key == Q2_TARGET),
        ),
        TutorialOption(
            key=Q2_MARKET,
            title=wording[Q2_MARKET]["title"],
            description=wording[Q2_MARKET]["description"],
            recommended=(selected_key == Q2_MARKET),
        ),
    ]

    return TutorialQuestionBlock(
        question_key="q2",
        title="この企画書では、どこまで整理して提案しますか？",
        description="今回の案件で、どこまで前提整理を含めるかを選んでください",
        options=options,
        recommended_key=selected_key,
        selected_key=selected_key,
    )


def _get_q1_wording(
    source_text: str,
    contact_eval_type: Optional[str],
) -> Dict[str, Dict[str, str]]:
    if contact_eval_type == "advertising_awareness":
        return {
            Q1_MARKET: {
                "title": "広告接点を含めた市場・顧客の全体像を把握したい",
                "description": "どんな層が市場の中心で、認知や利用の広がりがどうなっているかを広く理解します",
            },
            Q1_STP: {
                "title": "どのターゲット層に広告が効きやすいかを整理したい",
                "description": "狙うべき層や、効いている層・効いていない層の違いを整理します",
            },
            Q1_4P: {
                "title": "今回の広告施策が、認知や比較検討にどう影響したかを評価したい",
                "description": "広告接触者と非接触者の差を見ながら、施策効果を確認します",
            },
        }

    if contact_eval_type == "instore_consideration":
        return {
            Q1_MARKET: {
                "title": "売場や比較検討を含めた顧客行動の全体像を把握したい",
                "description": "来店者がどのように商品を見て、比較し、選んでいるかを広く理解します",
            },
            Q1_STP: {
                "title": "どの来店者層を重点ターゲットとして見るべきか整理したい",
                "description": "誰に対して売場訴求を強めるべきかを整理します",
            },
            Q1_4P: {
                "title": "店頭接点が比較検討や購買意向にどう影響したかを評価したい",
                "description": "売場接触の有無や接触内容による差を確認します",
            },
        }

    if contact_eval_type == "product_service_experience":
        return {
            Q1_MARKET: {
                "title": "商品・サービス利用者の全体像を把握したい",
                "description": "どんな人が利用し、どこに満足や課題があるかを広く整理します",
            },
            Q1_STP: {
                "title": "どの利用者層を重点ターゲットとして見るべきか整理したい",
                "description": "評価の高い層・伸ばすべき層を見つけ、狙う相手を整理します",
            },
            Q1_4P: {
                "title": "商品・サービス体験が評価や継続意向にどう影響したかを評価したい",
                "description": "利用状況や体験内容の差を見ながら、改善ポイントを確認します",
            },
        }

    if contact_eval_type == "brand_corporate_understanding":
        return {
            Q1_MARKET: {
                "title": "ブランドや企業に対する受け止め方の全体像を把握したい",
                "description": "認知・好意・信頼などの構造を広く理解します",
            },
            Q1_STP: {
                "title": "どの層にブランド理解を深めるべきか整理したい",
                "description": "ターゲット候補ごとに理解の深さや反応差を整理します",
            },
            Q1_4P: {
                "title": "ブランド接点が理解や好意形成にどう影響したかを評価したい",
                "description": "接点の有無や内容による態度差を確認します",
            },
        }

    if _detect_q1_theme(source_text) == Q1_MARKET:
        return {
            Q1_MARKET: {
                "title": "今回の市場や顧客の全体像を把握したい",
                "description": "誰が利用し、どんな構造になっているかを広く理解します",
            },
            Q1_STP: {
                "title": "どのターゲット層を狙うべきか整理したい",
                "description": "重点的に見るべき層や狙いどころを整理します",
            },
            Q1_4P: {
                "title": "施策や接点がどう影響しているかを確認したい",
                "description": "市場理解だけでなく、接点や施策との関係も確認します",
            },
        }

    if _detect_q1_theme(source_text) == Q1_STP:
        return {
            Q1_MARKET: {
                "title": "ターゲット検討の前提として市場や顧客の全体像を把握したい",
                "description": "まずは顧客構造や全体傾向を確認したい場合はこちらです",
            },
            Q1_STP: {
                "title": "今回、どの層を狙うべきかを整理したい",
                "description": "ターゲット候補や競合との差分を整理します",
            },
            Q1_4P: {
                "title": "狙う層に対して施策や接点がどう効くかを評価したい",
                "description": "ターゲット整理に加え、施策の効き方まで見たい場合はこちらです",
            },
        }

    return {
        Q1_MARKET: {
            "title": "今回テーマの前提として市場や顧客の全体像を把握したい",
            "description": "利用実態や顧客構造を広く理解したい場合はこちらです",
        },
        Q1_STP: {
            "title": "今回、どの層を重点的に見るべきか整理したい",
            "description": "狙うべき相手や優先層を整理したい場合はこちらです",
        },
        Q1_4P: {
            "title": "今回の施策や接点が、評価や行動にどう影響したかを確認したい",
            "description": "接触有無や利用状況の差を見ながら、施策効果を確認します",
        },
    }


def _get_q2_wording(
    detected_theme: str,
    contact_eval_type: Optional[str],
) -> Dict[str, Dict[str, str]]:
    theme_phrase = _resolve_theme_phrase(detected_theme, contact_eval_type)

    return {
        Q2_FOCUS: {
            "title": f"{theme_phrase}に必要な範囲に絞って整理する",
            "description": "今回の主題に直接関係する内容を優先し、短くまとまった企画にします",
        },
        Q2_TARGET: {
            "title": f"{theme_phrase}に加えて、狙う相手の整理まで含める",
            "description": "誰に向けた提案なのかまで整理して、企画の納得感を高めます",
        },
        Q2_MARKET: {
            "title": f"{theme_phrase}の前提として、市場や顧客理解から含める",
            "description": "市場全体や顧客構造から整理し、背景を含めて提案します",
        },
    }


def _resolve_theme_phrase(
    detected_theme: str,
    contact_eval_type: Optional[str],
) -> str:
    if detected_theme == Q1_MARKET:
        return "市場や顧客の全体像把握"
    if detected_theme == Q1_STP:
        return "ターゲット整理"
    if contact_eval_type == "advertising_awareness":
        return "広告施策の評価"
    if contact_eval_type == "instore_consideration":
        return "店頭接点の評価"
    if contact_eval_type == "product_service_experience":
        return "商品・サービス体験の評価"
    if contact_eval_type == "brand_corporate_understanding":
        return "ブランド接点の評価"
    return "今回テーマの評価"


def _generate_ai_tutorial_wording(
    orien_outline_text: str,
    manual_text: Optional[str],
    extracted_texts: Optional[List[str]],
    detected_theme: str,
    detected_scope: str,
    contact_eval_type: Optional[str],
    q1_default_wording: Dict[str, Dict[str, str]],
    q2_default_wording: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Q1/Q2 の表示文言だけを Azure OpenAI で案件向けに調整する。
    失敗時は空 dict を返し、呼び出し元でデフォルト文言を使う。
    """
    if not orien_outline_text.strip():
        return {}

    extracted_preview = "\n".join((extracted_texts or [])[:3])
    manual_preview = manual_text or ""

    prompt = f"""
あなたは市場調査企画のUI文言設計アシスタントです。
目的は、既存の内部キーの意味を変えずに、Q1/Q2の表示文言だけを今回案件向けに自然な日本語へ調整することです。

【重要ルール】
- 内部キーの意味は絶対に変えない
- Q1 は「何を一番知りたいか」という主題の違い
- Q2 は「どこまで整理して提案するか」という範囲の違い
- 選択肢どうしが重複しすぎないようにする
- 抽象語だけでなく、案件の文脈に寄せる
- ただし言いすぎ・断定しすぎは避ける
- タイトルは短めで、UI選択肢として自然な長さにする
- description は1文で簡潔に補足する
- 出力はJSONのみ
- key は指定どおり必ず残す
- キーの追加・削除は禁止

【案件情報】
orien_outline_text:
{orien_outline_text}

manual_text:
{manual_preview}

extracted_texts_preview:
{extracted_preview}

detected_theme:
{detected_theme}

detected_scope:
{detected_scope}

contact_eval_type:
{contact_eval_type}

【Q1 デフォルト文言】
{json.dumps(q1_default_wording, ensure_ascii=False, indent=2)}

【Q2 デフォルト文言】
{json.dumps(q2_default_wording, ensure_ascii=False, indent=2)}

【出力フォーマット】
{{
  "q1_options": {{
    "market_overview": {{
      "title": "...",
      "description": "..."
    }},
    "target_strategy": {{
      "title": "...",
      "description": "..."
    }},
    "measure_evaluation": {{
      "title": "...",
      "description": "..."
    }}
  }},
  "q2_options": {{
    "theme_only": {{
      "title": "...",
      "description": "..."
    }},
    "include_target": {{
      "title": "...",
      "description": "..."
    }},
    "include_market": {{
      "title": "...",
      "description": "..."
    }}
  }}
}}
""".strip()

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "あなたは市場調査企画のUI選択肢文言を整える専門家です。JSONのみを返してください。",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        content = response.choices[0].message.content
        if not content:
            return {}

        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return {}

        return parsed

    except Exception:
        return {}


def _merge_ai_wording(
    default_wording: Dict[str, Dict[str, str]],
    ai_wording: Dict[str, Dict[str, str]],
    allowed_keys: List[str],
) -> Dict[str, Dict[str, str]]:
    """
    AI文言を安全にマージする。
    title/description が空や不正なら default を維持する。
    """
    merged: Dict[str, Dict[str, str]] = {}

    for key in allowed_keys:
        base = default_wording.get(key, {"title": "", "description": ""})
        candidate = ai_wording.get(key, {}) if isinstance(ai_wording, dict) else {}

        title = candidate.get("title") if isinstance(candidate, dict) else None
        description = candidate.get("description") if isinstance(candidate, dict) else None

        safe_title = _sanitize_option_text(title, base["title"], max_len=70)
        safe_description = _sanitize_option_text(
            description, base["description"], max_len=120
        )

        merged[key] = {
            "title": safe_title,
            "description": safe_description,
        }

    return merged


def _sanitize_option_text(value: Optional[str], fallback: str, max_len: int) -> str:
    if not isinstance(value, str):
        return fallback

    normalized = " ".join(value.replace("\n", " ").split()).strip()
    if not normalized:
        return fallback

    if len(normalized) > max_len:
        return fallback

    return normalized


def _build_q3_suggestions(q1_selected_key: str, q2_selected_key: str) -> List[AnalysisSuggestion]:
    suggestions: List[AnalysisSuggestion] = []

    if q1_selected_key == Q1_MARKET:
        suggestions.extend(
            [
                AnalysisSuggestion(
                    key="gender_age",
                    axis_title="性年代",
                    scenario="広い軸で、自社ブランドがどの層にどのように利用されているかを把握します",
                    recommended=True,
                    selected=True,
                ),
                AnalysisSuggestion(
                    key="area",
                    axis_title="エリア",
                    scenario="地域差を確認し、利用実態やニーズ構造の違いを整理します",
                    recommended=True,
                    selected=True,
                ),
                AnalysisSuggestion(
                    key="basic_profile",
                    axis_title="基本属性",
                    scenario="職業・家族構成などの属性差を見ながら、顧客像の輪郭を整理します",
                    recommended=True,
                    selected=(q2_selected_key == Q2_MARKET),
                ),
            ]
        )

    elif q1_selected_key == Q1_STP:
        suggestions.extend(
            [
                AnalysisSuggestion(
                    key="awareness",
                    axis_title="認知 / 非認知",
                    scenario="まず知っている層と知らない層を分け、ターゲット候補の入口を整理します",
                    recommended=True,
                    selected=True,
                ),
                AnalysisSuggestion(
                    key="usage",
                    axis_title="利用 / 非利用",
                    scenario="利用有無で評価や期待の違いを見て、狙うべき層の優先度を整理します",
                    recommended=True,
                    selected=True,
                ),
                AnalysisSuggestion(
                    key="high_intent",
                    axis_title="意向高 / 意向低",
                    scenario="今後の伸長余地がある層を見つけ、狙う相手と訴求方向を整理します",
                    recommended=True,
                    selected=True,
                ),
            ]
        )

    else:
        suggestions.extend(
            [
                AnalysisSuggestion(
                    key="contact",
                    axis_title="接触 / 非接触",
                    scenario="施策に触れた人と触れていない人を比較し、態度変化の有無を確認します",
                    recommended=True,
                    selected=True,
                ),
                AnalysisSuggestion(
                    key="consideration",
                    axis_title="比較検討有無",
                    scenario="比較検討した人としていない人を分け、施策が検討行動にどう関与したかを整理します",
                    recommended=True,
                    selected=True,
                ),
                AnalysisSuggestion(
                    key="usage_frequency",
                    axis_title="利用状況（ヘビー / ライト）",
                    scenario="利用頻度の違いによって、評価やニーズの差を整理します",
                    recommended=True,
                    selected=(q2_selected_key != Q2_FOCUS),
                ),
            ]
        )

    if q2_selected_key == Q2_MARKET:
        suggestions.append(
            AnalysisSuggestion(
                key="customer_stage",
                axis_title="顧客ステージ",
                scenario="市場理解から施策評価までをつなぐため、認知・利用・定着の段階差を確認します",
                recommended=True,
                selected=True,
            )
        )

    return suggestions


def _build_slide_plan(q1_selected_key: str, q2_selected_key: str) -> SlidePlan:
    slides: List[SlidePlanItem] = []
    order = 1

    def add_slide(slide_type: str, title: str, purpose: str) -> None:
        nonlocal order
        slides.append(
            SlidePlanItem(
                slide_type=slide_type,
                title=title,
                purpose=purpose,
                order=order,
            )
        )
        order += 1

    add_slide("cover", "表紙", "企画全体のテーマを示します")
    add_slide("background", "調査の背景・目的・課題", "今回の調査で答えるべき論点を整理します")

    if q2_selected_key == Q2_MARKET:
        add_slide("market_understanding", "市場・顧客の前提理解", "市場全体と顧客構造の前提を共有します")

    if q2_selected_key in [Q2_TARGET, Q2_MARKET]:
        add_slide("target_structure", "ターゲット整理", "誰を狙うべきかを整理します")

    add_slide("question_structure", "問いの分解", "企画全体の問いをサブクエスチョンに分解します")

    if q1_selected_key == Q1_MARKET:
        add_slide("analysis_approach_1", "分析アプローチ①", "市場全体像を把握する分析を設計します")
        add_slide("analysis_approach_2", "分析アプローチ②", "顧客差分を捉える分析を設計します")
    elif q1_selected_key == Q1_STP:
        add_slide("analysis_approach_1", "分析アプローチ①", "狙うべき層を見つける分析を設計します")
        add_slide("analysis_approach_2", "分析アプローチ②", "競合や現状との違いを確認する分析を設計します")
    else:
        add_slide("analysis_approach_1", "分析アプローチ①", "施策接触差を捉える分析を設計します")
        add_slide("analysis_approach_2", "分析アプローチ②", "評価差や行動差を確認する分析を設計します")

    add_slide("evaluation_items", "評価項目", "何を評価するかを定義します")
    add_slide("analysis_axis", "分析軸", "どの切り口で比較するかを明確にします")
    add_slide("hypothesis", "検証する仮説", "分析で確かめる仮説を整理します")

    plan_type = _resolve_plan_type(q1_selected_key, q2_selected_key)

    return SlidePlan(
        recommended_slide_count=len(slides),
        plan_type=plan_type,
        slides=slides,
    )


def _resolve_plan_type(q1_selected_key: str, q2_selected_key: str) -> str:
    if q2_selected_key == Q2_FOCUS and q1_selected_key == Q1_4P:
        return "4P_only"
    if q2_selected_key == Q2_TARGET:
        return "STP_plus_theme"
    if q2_selected_key == Q2_MARKET:
        return "market_plus_STP_plus_theme"
    return "standard"


def get_theme_label(theme_key: str) -> str:
    mapping = {
        Q1_MARKET: "市場や顧客の全体像を把握したい",
        Q1_STP: "ターゲットや狙う相手を整理したい",
        Q1_4P: "施策や接点の効き方を評価したい",
    }
    return mapping.get(theme_key, theme_key)


def get_scope_label(scope_key: str) -> str:
    mapping = {
        Q2_FOCUS: "今回のテーマに必要な範囲に絞る",
        Q2_TARGET: "背景となるターゲット整理まで含める",
        Q2_MARKET: "市場や顧客の前提理解から含める",
    }
    return mapping.get(scope_key, scope_key)