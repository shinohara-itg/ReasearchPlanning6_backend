from __future__ import annotations

import json
import re
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.schemas.ppt_export import PptExportPayload
from app.services.ppt_export_service import export_ppt_from_template_bytes
from urllib.parse import quote

router = APIRouter(prefix="/api/ppt", tags=["ppt"])


def _safe_filename(value: str) -> str:
    value = (value or "").strip() or "企画書"
    value = re.sub(r'[\\/:*?"<>|]', "", value)
    value = re.sub(r"\s+", "_", value)
    return value[:80]


@router.post("/export")
async def export_ppt_api(
    template_file: UploadFile = File(...),
    payload_json: str = Form(...),
):
    try:
        if not template_file.filename.lower().endswith(".pptx"):
            raise HTTPException(status_code=400, detail="PPTテンプレートは .pptx を指定してください。")

        payload_dict = json.loads(payload_json)
        payload = PptExportPayload(**payload_dict)

        if not payload.items:
            raise HTTPException(status_code=400, detail="PPTに反映する items が空です。")

        template_bytes = await template_file.read()
        if not template_bytes:
            raise HTTPException(status_code=400, detail="PPTテンプレートファイルが空です。")

        ppt_stream, report = export_ppt_from_template_bytes(
            template_bytes=template_bytes,
            items=payload.items,
        )

        title = payload.meta.get("research_title") or payload.meta.get("project_name") or "企画書"
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{_safe_filename(title)}_{date_str}.pptx"

        # デバッグしたい場合に備えて最低限の結果をヘッダに載せる
        ascii_filename = "proposal.pptx"
        encoded_filename = quote(filename)

        headers = {
            "Content-Disposition": (
                f"attachment; filename={ascii_filename}; "
                f"filename*=UTF-8''{encoded_filename}"
            ),
            "X-PPT-Applied": str(report.get("applied", 0)),
            "X-PPT-Shape-Not-Found": str(report.get("shape_not_found", 0)),
            "X-PPT-Slide-OOB": str(report.get("slide_oob", 0)),
        }

        return StreamingResponse(
            ppt_stream,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers=headers,
        )

    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="payload_json がJSONとして解釈できません。")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPT出力に失敗しました: {str(e)}")