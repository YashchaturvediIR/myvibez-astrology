from fastapi import APIRouter, HTTPException
from app.services.predictive_timing import calculate_event_timing, calculate_all_upcoming_events

router = APIRouter()

@router.post("/predictive-timing")
def predictive_timing(payload: dict):
    try:
        kundli = payload.get("kundli", payload)
        topic = payload.get("topic", "")
        query_datetime = payload.get("query_datetime")
        if not topic:
            raise ValueError("topic is required")
        return {"success": True, "result": calculate_event_timing(kundli, topic, query_datetime)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/upcoming-events")
def upcoming_events(payload: dict):
    try:
        kundli = payload.get("kundli", payload)
        query_datetime = payload.get("query_datetime")
        return {"success": True, "result": calculate_all_upcoming_events(kundli, query_datetime)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
