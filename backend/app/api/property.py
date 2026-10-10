from fastapi import APIRouter, HTTPException
from app.services.significator import calculate_property_analysis

router = APIRouter()

@router.post("/property-analysis")
def property_analysis(kundli: dict):
    """Consume Phase-1 Kundli JSON and run the deterministic house-purchase algorithm."""
    try:
        if "planets" not in kundli or "houses" not in kundli or "ascendant" not in kundli:
            raise ValueError("Invalid Kundli JSON: planets, houses and ascendant are required.")
        return {"success": True, "result": calculate_property_analysis(kundli)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Property analysis failed: {exc}")
