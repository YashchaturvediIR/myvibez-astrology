from fastapi import APIRouter, HTTPException
from app.models.kundli import KundliRequest
from app.services.kundli_calculator import calculate_kundli

router = APIRouter()

@router.post("/kundli")
def kundli(request: KundliRequest):
    try:
        return {"success": True, "kundli": calculate_kundli(request)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Kundli calculation failed.")
