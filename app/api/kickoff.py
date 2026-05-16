from fastapi import APIRouter, HTTPException

from app.schemas.kickoff import KickoffRequest, KickoffResponse
from app.services.kickoff_service import generate_kickoff_draft

router = APIRouter(prefix="/api", tags=["kickoff"])


@router.post("/kickoff", response_model=KickoffResponse)
def create_kickoff(request: KickoffRequest) -> KickoffResponse:
    try:
        return generate_kickoff_draft(
            orien_outline_text=request.orien_outline_text,
            selected_axis_text=request.selected_axis_text,
            customer_business_analysis=request.customer_business_analysis,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate kickoff draft: {e}")