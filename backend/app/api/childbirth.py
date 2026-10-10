from fastapi import APIRouter, HTTPException
from app.services.childbirth import calculate_childbirth_analysis

router = APIRouter()

@router.post("/childbirth-analysis")
def childbirth_analysis(kundli: dict):
    """Consume Phase-1 Kundli JSON and run the deterministic childbirth rules."""
    try:
        return {"success": True, "result": calculate_childbirth_analysis(kundli)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Childbirth analysis failed: {exc}")
