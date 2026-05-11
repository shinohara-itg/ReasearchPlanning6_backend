from fastapi import APIRouter, HTTPException

from app.schemas.analysis_approach import (
    AnalysisApproachRequest,
    AnalysisApproachResponse,
)
from app.services.analysis_approach_service import generate_analysis_approach_draft

router = APIRouter(tags=["analysis-approach"])


@router.post(
    "/api/analysis-approach",
    response_model=AnalysisApproachResponse,
)
def create_analysis_approach(
    request: AnalysisApproachRequest,
) -> AnalysisApproachResponse:
    try:
        return generate_analysis_approach_draft(
            subq_list=request.subq_list,
            max_blocks=5,
            initial_selected=3,
            max_selectable=5,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"分析アプローチ生成中にエラーが発生しました: {exc}",
        ) from exc