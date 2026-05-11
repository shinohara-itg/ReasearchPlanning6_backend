from fastapi import APIRouter, HTTPException
from app.schemas.orien import OrienOutlineRequest, OrienOutlineResponse
from app.services.orien_service import generate_orien_outline

router = APIRouter()

@router.post("/orien/outline", response_model=OrienOutlineResponse)
def create_orien_outline(payload: OrienOutlineRequest):
    try:
        result = generate_orien_outline(
            extracted_texts=payload.extracted_texts,
            manual_text=payload.manual_text,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"オリエン整理生成中にエラーが発生しました: {e}")
    
