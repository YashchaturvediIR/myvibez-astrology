from fastapi import APIRouter, HTTPException
from app.services.significator import calculate_significators

router = APIRouter()

@router.post("/significators")
def significators(kundli: dict):
    """Consume Phase-1 Kundli JSON and produce the Phase-2 significator table."""
    try:
        if "planets" not in kundli or "houses" not in kundli:
            raise ValueError("Invalid Kundli JSON: planets and houses are required.")
        return {"success": True, "result": calculate_significators(kundli)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Significator calculation failed: {exc}")
