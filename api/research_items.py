from fastapi import APIRouter, HTTPException

from app.schemas.research_items import (
    ResearchItemsConfirmRequest,
    ResearchItemsConfirmResponse,
    ResearchItemsGenerateRequest,
    ResearchItemsGenerateResponse,
    ResearchItemsShortlistRequest,
    ResearchItemsShortlistResponse,
)
from app.services.research_items_service import (
    confirm_research_items,
    generate_research_items,
    shortlist_research_items,
)

router = APIRouter(prefix="/api/research-items", tags=["research-items"])


@router.post("/generate", response_model=ResearchItemsGenerateResponse)
def generate_research_items_api(request: ResearchItemsGenerateRequest):
    try:
        if not request.target_condition_text.strip():
            raise HTTPException(status_code=400, detail="target_condition_text は必須です。")

        if not request.analysis_blocks:
            raise HTTPException(status_code=400, detail="analysis_blocks が空です。")

        result = generate_research_items(
            orien_outline_text=request.orien_outline_text,
            kickoff_text=request.kickoff_text,
            subquestions_text=request.subquestions_text,
            target_condition_text=request.target_condition_text,
            analysis_blocks=request.analysis_blocks,
            selected_analysis_ids=request.selected_analysis_ids,
            min_analysis_questions=request.min_analysis_questions,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"調査項目生成に失敗しました: {str(e)}",
        )


@router.post("/shortlist", response_model=ResearchItemsShortlistResponse)
def shortlist_research_items_api(request: ResearchItemsShortlistRequest):
    try:
        if not request.analysis_items:
            raise HTTPException(status_code=400, detail="analysis_items が空です。")

        result = shortlist_research_items(
            analysis_items=request.analysis_items,
            desired_count=request.desired_count,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"調査項目絞り込みに失敗しました: {str(e)}",
        )


@router.post("/confirm", response_model=ResearchItemsConfirmResponse)
def confirm_research_items_api(request: ResearchItemsConfirmRequest):
    try:
        result = confirm_research_items(
            screening_items=request.screening_items,
            analysis_items=request.analysis_items,
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"調査項目確定に失敗しました: {str(e)}",
        )