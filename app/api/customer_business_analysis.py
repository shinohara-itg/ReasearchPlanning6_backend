from fastapi import APIRouter, HTTPException

from app.schemas.customer_business_analysis import (
    CustomerBusinessAnalysisRequest,
    CustomerBusinessAnalysisResponse,
)
from app.services.customer_business_analysis_service import (
    generate_customer_business_analysis,
)

router = APIRouter()


@router.post(
    "/customer-business-analysis",
    response_model=CustomerBusinessAnalysisResponse,
)
def customer_business_analysis(req: CustomerBusinessAnalysisRequest):
    try:
        return generate_customer_business_analysis(req)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"顧客事業分析の生成に失敗しました: {str(e)}",
        )