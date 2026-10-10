from fastapi import APIRouter, HTTPException
from app.services.grah_nirdeshan import calculate_grah_nirdeshan

router = APIRouter()


@router.post("/grah-nirdeshan")
def grah_nirdeshan(kundli: dict):
    """Generate the exact D-1 Grah Nirdeshan / signified-bhavas table."""
    try:
        return {"success": True, "result": calculate_grah_nirdeshan(kundli)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Grah Nirdeshan calculation failed: {exc}")
