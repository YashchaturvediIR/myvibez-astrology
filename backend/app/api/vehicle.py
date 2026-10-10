from fastapi import APIRouter, HTTPException
from app.services.vehicle import calculate_vehicle_analysis

router = APIRouter()

@router.post("/vehicle-analysis")
def vehicle_analysis(payload: dict):
    try:
        kundli = payload.get("kundli", payload)
        query_datetime = payload.get("query_datetime")
        return {"success": True, "result": calculate_vehicle_analysis(kundli, query_datetime)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
