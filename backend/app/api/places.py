from fastapi import APIRouter, HTTPException, Query
import requests
from zoneinfo import ZoneInfo

router = APIRouter()

@router.get("/places/search")
def search_places(q: str = Query(min_length=2, max_length=100)):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": q,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 6,
            },
            headers={"User-Agent": "PersonalKundliApp/1.0"},
            timeout=10,
        )
        r.raise_for_status()
        raw = r.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Place search failed: {exc}")

    results = []
    for item in raw:
        lat = float(item["lat"])
        lon = float(item["lon"])
        address = item.get("address", {})
        country = address.get("country", "")
        display = item.get("display_name", "")
        # Nominatim does not reliably return timezone. Frontend selection
        # therefore sends the selected coordinates to this endpoint for lookup.
        results.append({
            "display_name": display,
            "latitude": lat,
            "longitude": lon,
            "country": country,
        })
    return {"results": results}

@router.get("/places/timezone")
def place_timezone(latitude: float, longitude: float):
    # Use timezonefinder to resolve coordinates locally.
    try:
        from timezonefinder import TimezoneFinder
        tz = TimezoneFinder().timezone_at(lat=latitude, lng=longitude)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Timezone lookup failed: {exc}")
    if not tz:
        raise HTTPException(status_code=400, detail="Could not determine timezone for selected place.")
    try:
        ZoneInfo(tz)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Timezone data unavailable: {tz}")
    return {"timezone": tz}
