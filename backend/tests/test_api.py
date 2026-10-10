from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_kundli():
    payload = {
        "birth_details": {
            "date": "2007-10-05",
            "time": "10:30:00",
            "place": "Delhi, India",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "timezone": "Asia/Kolkata"
        },
        "settings": {
            "zodiac": "sidereal",
            "ayanamsha": "Lahiri",
            "node_type": "mean",
            "house_system": "whole_sign"
        }
    }
    r = client.post("/api/kundli", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "planets" in data["kundli"]
    assert "Sun" in data["kundli"]["planets"]
    assert "vimshottari_dasha" in data["kundli"]
    assert data["kundli"]["vimshottari_dasha"]["year_convention"] == "360-day Savana year"
