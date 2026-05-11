from fastapi import APIRouter

from app.schemas.tutorial import (
    TutorialPlanRequest,
    TutorialPlanResponse,
    TutorialRefreshRequest,
    TutorialRefreshResponse,
)
from app.services.tutorial_service import (
    build_tutorial_plan,
    refresh_tutorial_plan,
)

router = APIRouter(prefix="/api/tutorial", tags=["tutorial"])


@router.post("/plan", response_model=TutorialPlanResponse)
def tutorial_plan(request: TutorialPlanRequest) -> TutorialPlanResponse:
    return build_tutorial_plan(
        orien_outline_text=request.orien_outline_text,
        manual_text=request.manual_text,
        extracted_texts=request.extracted_texts,
    )


@router.post("/refresh", response_model=TutorialRefreshResponse)
def tutorial_refresh(request: TutorialRefreshRequest) -> TutorialRefreshResponse:
    return refresh_tutorial_plan(
        orien_outline_text=request.orien_outline_text,
        q1_selected_key=request.q1_selected_key,
        q2_selected_key=request.q2_selected_key,
    )