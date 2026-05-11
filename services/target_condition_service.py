import os

from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schemas.target_condition import (
    TargetConditionRequest,
    TargetConditionResponse,
)

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


def build_target_condition_prompt(req: TargetConditionRequest) -> str:
    return f"""
あなたは市場調査設計の専門家です。
以下の情報をもとに、この調査の「対象者条件」を検討してください。

【出力形式】
- 対象者イメージ：
- エリア：
- 年齢・性別条件：
- 行動・意識・その他属性の条件：
- 除外条件：

【オリエン内容の整理（抜粋）】
{req.orien_outline_text[:2000]}

【キックオフノート（参考）】
{req.kickoff_text}

【問いの分解（AI生成サブクエスチョン）】
{req.subquestions}

【分析アプローチ管理】
{req.bunseki}

【条件めも】
{req.memo}

【条件】
- 市場調査綱領にて、15歳未満にはアンケートを依頼することができないので対象者条件に含めないこと
- 80歳以上はアンケートに回答できない可能性が高いので対象者条件に含めないこと
- 対象者イメージは冒頭に簡潔に記載してください。
- “なんとなく広く”ではなく、上記の軸と問いに対して検証力が最大化するように絞り込んでください。
- 「●●来場経験者であること」ではなく「●●来場者」、「購買意思決定に関与する層」ではなく「購買意思決定者」など、簡潔な表現を用いてください。
- 除外条件に"調査に協力する意思がない層"、"過去の調査で回答の質に問題があった層"などアンケート条件とならないものは含めないでください。
- ###、** などの記号は使わないでください。
""".strip()


def generate_target_condition(
    req: TargetConditionRequest,
) -> TargetConditionResponse:
    prompt = build_target_condition_prompt(req)

    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは市場調査設計の専門家です。"
                    "実務でそのまま使える、簡潔で明快な日本語で出力してください。"
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.4,
    )

    content = response.choices[0].message.content or ""
    text = content.strip()

    return TargetConditionResponse(target_condition_text=text)