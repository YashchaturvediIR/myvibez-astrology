
import os

import requests
from fastapi import APIRouter, HTTPException, Query
from zoneinfo import ZoneInfo

router = APIRouter()


@router.get("/places/search")
def search_places(q: str = Query(min_length=2, max_length=100)):
    api_key = os.getenv("GEOAPIFY_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEOAPIFY_API_KEY is not configured on the server.",
        )

    try:
        response = requests.get(
            "https://api.geoapify.com/v1/geocode/autocomplete",
            params={
                "text": q,
                "format": "json",
                "limit": 6,
                "apiKey": api_key,
            },
            timeout=15,
        )
        response.raise_for_status()
        raw = response.json().get("results", [])

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Place search provider failed. Please try again.",
        )

    results = []

    for item in raw:
        if item.get("lat") is None or item.get("lon") is None:
            continue

        results.append({
            "display_name": item.get("formatted", ""),
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
            "country": item.get("country", ""),
        })

    return {"results": results}


@router.get("/places/timezone")
def place_timezone(latitude: float, longitude: float):
    try:
        from timezonefinder import TimezoneFinder

        tz = TimezoneFinder().timezone_at(
            lat=latitude,
            lng=longitude,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Timezone lookup failed: {exc}",
        )

    if not tz:
        raise HTTPException(
            status_code=400,
            detail="Could not determine timezone for selected place.",
        )

    try:
        ZoneInfo(tz)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Timezone data unavailable: {tz}",
        )

    return {"timezone": tz}
