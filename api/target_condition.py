from fastapi import APIRouter, HTTPException

from app.schemas.target_condition import (
    TargetConditionRequest,
    TargetConditionResponse,
)
from app.services.target_condition_service import generate_target_condition

router = APIRouter(prefix="/api/target-condition", tags=["target-condition"])


@router.post("", response_model=TargetConditionResponse)
def create_target_condition(req: TargetConditionRequest):
    try:
        return generate_target_condition(req)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"調査対象者条件の生成に失敗しました: {str(e)}",
        )