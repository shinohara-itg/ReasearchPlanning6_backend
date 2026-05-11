from fastapi import APIRouter, HTTPException

from app.schemas.proposal_review import (
    ProposalReviewRequest,
    ProposalReviewResponse,
)
from app.services.proposal_review_service import generate_proposal_review

router = APIRouter()


@router.post("/proposal-review", response_model=ProposalReviewResponse)
def proposal_review(req: ProposalReviewRequest):
    try:
        result = generate_proposal_review(req)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))