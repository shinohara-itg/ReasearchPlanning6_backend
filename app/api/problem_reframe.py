from fastapi import APIRouter, HTTPException

from app.schemas.problem_reframe import (
    ProblemReframeRequest,
    ProblemReframeResponse,
)
from app.services.problem_reframe_service import generate_problem_reframe_premise


router = APIRouter(
    prefix="/api/problem-reframe",
    tags=["problem-reframe"],
)


@router.post("", response_model=ProblemReframeResponse)
def problem_reframe(request: ProblemReframeRequest):
    try:
        result = generate_problem_reframe_premise(
            orien_outline_text=request.orien_outline_text,
            extracted_texts=request.extracted_texts,
            manual_text=request.manual_text or "",
        )
        return ProblemReframeResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"課題変換（前提整理）の生成中にエラーが発生しました: {e}",
        ) from e