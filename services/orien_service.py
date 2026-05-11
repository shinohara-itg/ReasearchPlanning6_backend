from openai import AzureOpenAI
import os

def build_orien_context_text(extracted_texts: list[str], manual_text: str, ai_text: str = "") -> str:
    docs_text = "\n".join([t for t in extracted_texts if t and t.strip()]).strip()
    manual_text = (manual_text or "").strip()
    ai_text = (ai_text or "").strip()

    parts = []
    if docs_text:
        parts.append("【オリエン資料（アップロード抽出テキスト）】\n" + docs_text)

    if manual_text:
        parts.append("【オリエン内容レビュー（手入力：最優先）】\n" + manual_text)
    elif ai_text:
        parts.append("【オリエン内容の整理（AI）】\n" + ai_text)

    return "\n\n".join(parts).strip()


def compose_orien_outline_text(manual_text: str, ai_text: str) -> str:
    manual = (manual_text or "").strip()
    ai = (ai_text or "").strip()

    if manual and ai:
        return (
            "【手入力（最優先：追記・修正）】\n"
            f"{manual}\n\n"
            "【整理結果（所定フォーム：AI）】\n"
            f"{ai}"
        )
    if manual:
        return "【手入力（最優先：追記・修正）】\n" + manual
    return "【整理結果（所定フォーム：AI）】\n" + ai


def generate_orien_outline(extracted_texts: list[str], manual_text: str) -> dict:
    ori_texts = build_orien_context_text(extracted_texts, manual_text)

    if not ori_texts.strip():
        raise ValueError("オリエン資料（アップロード）または手入力内容がありません。")

    client = AzureOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    prompt = f"""
あなたは市場調査の専門家です。
以下のオリエン資料から以下のことをまとめてください。
特に言及がなければ項目ごとに「なし」と記載してください。

【出力形式】
・企業名：
・ブランド名：
・カテゴリー（市場）名：
・議事録の要約（500文字程度）：
・分析手法に関する要望：
・調査仕様に関する要望
    調査エリア：
    スクリーニング調査有無：
    対象者条件：
    質問数：
    サンプルサイズ：
    調査画面で画像や動画の提示：
    ウェイトバック集計の有無：
    自由回答のコーディング処理の有無：
    調査票作成（クライアントがやるか当社がやるか）：
    報告書は必要か：
・スケジュールに関する要望
    企画提案予定日：
    調査票や画像に関する提供可能日：
    希望する納期：
    請求日/月：
    クライアントの重要な会議日：
    その他スケジュールに関する要望：
・費用に関する要望
    見積金額上限：
    複数パターンの見積を希望しているか：
・会議参加者のお名前・役職・役割
・調査とは直接関係ないが雑談したこと：
・その他調査に関する特記事項（広告がいつから投下されるかなど）：

オリエン資料：
{ori_texts[:4000]}
""".strip()

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "あなたは市場調査の専門家です。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=900,
    )

    ai_result = response.choices[0].message.content.strip()
    outline_text = compose_orien_outline_text(manual_text, ai_result)

    return {
        "orien_outline_ai_draft": ai_result,
        "orien_outline_text": outline_text,
    }
