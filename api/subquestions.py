from fastapi import APIRouter, HTTPException

from app.schemas.subquestions import SubQuestionsRequest, SubQuestionsResponse
from app.services.subquestions_service import generate_subquestions_draft

router = APIRouter(prefix="/api", tags=["subquestions"])


@router.post("/subquestions", response_model=SubQuestionsResponse)
def create_subquestions(request: SubQuestionsRequest) -> SubQuestionsResponse:
    try:
        return generate_subquestions_draft(
            orien_outline_text=request.orien_outline_text,
            selected_axis_text=request.selected_axis_text,
            main_question=request.main_question,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate subquestions: {e}")