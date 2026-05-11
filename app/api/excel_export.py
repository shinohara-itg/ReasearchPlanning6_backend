from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.excel_export import ResearchItemsExcelExportRequest
from app.services.excel_export_service import create_research_items_excel


router = APIRouter(prefix="/api/excel", tags=["excel"])


def _safe_filename(value: str) -> str:
    value = (value or "").strip() or "調査項目案"
    value = re.sub(r'[\\/:*?"<>|]', "", value)
    value = re.sub(r"\s+", "_", value)
    return value[:80]


@router.post("/research-items")
def export_research_items_excel_api(request: ResearchItemsExcelExportRequest):
    try:
        if not request.screening_items and not request.analysis_items:
            raise HTTPException(status_code=400, detail="出力対象の調査項目がありません。")

        excel_stream = create_research_items_excel(
            screening_items=request.screening_items,
            analysis_items=request.analysis_items,
        )

        base = request.research_title or request.project_name or "調査項目案"
        filename = f"{_safe_filename(base)}_調査項目案_{datetime.now().strftime('%Y%m%d')}.xlsx"

        ascii_filename = "research_items.xlsx"
        encoded_filename = quote(filename)

        headers = {
            "Content-Disposition": (
                f"attachment; filename={ascii_filename}; "
                f"filename*=UTF-8''{encoded_filename}"
            )
        }

        return StreamingResponse(
            excel_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel出力に失敗しました: {str(e)}")