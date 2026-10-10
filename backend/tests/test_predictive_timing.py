from datetime import datetime
from app.services.predictive_timing import calculate_event_timing


def sample_kundli():
    # Minimal deterministic fixture: Taurus D1, with synthetic houses/planet data.
    signs = ["Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces","Aries"]
    houses = {str(i+1): {"sign": s, "sign_index": i+1} for i, s in enumerate(signs)}
    planets = {}
    placements = {
        "Sun": ("Leo",4,"Sun"), "Moon": ("Cancer",3,"Moon"), "Mars": ("Aries",12,"Mars"),
        "Mercury": ("Gemini",2,"Mercury"), "Jupiter": ("Sagittarius",8,"Jupiter"),
        "Venus": ("Taurus",1,"Venus"), "Saturn": ("Capricorn",9,"Saturn"),
        "Rahu": ("Scorpio",7,"Mars"), "Ketu": ("Taurus",1,"Venus")
    }
    for p,(sign,house,naklord) in placements.items():
        planets[p] = {"sign": sign, "house": house, "nakshatra_lord": naklord, "nakshatra": "Ashwini", "longitude": (house-1)*30+1, "degree_in_sign": 1.0}
    return {
        "birth_details": {"date":"1990-01-01","time":"00:00:00","timezone":"Asia/Kolkata"},
        "ascendant": {"sign":"Taurus","sign_index":2,"degree_in_sign":10.0},
        "houses": houses, "planets": planets
    }


def test_unknown_topic_rejected():
    try:
        calculate_event_timing(sample_kundli(), "unknown", "2026-09-10T00:00:00+05:30")
        assert False
    except ValueError:
        assert True


def test_forward_scan_returns_reference_date_and_never_past_match():
    r = calculate_event_timing(sample_kundli(), "marriage", "2026-09-10T00:00:00+05:30")
    assert r["query_reference_date"] == "10/09/2026"
    if r["timing"]["status"] == "MATCH FOUND":
        assert datetime.fromisoformat(r["timing"]["valid_end"]) > datetime.fromisoformat("2026-09-10T00:00:00+05:30")


def test_query_datetime_accepts_javascript_z_timestamp():
    result = calculate_event_timing(
        sample_kundli(), "marriage", "2026-09-10T16:45:11.251Z"
    )
    assert result["query_reference_datetime"].endswith("+05:30")
