from app.services.vehicle import MOVABLE_SIGNS, DUAL_SIGNS, VEHICLE_HOUSES


def test_vehicle_constants():
    assert VEHICLE_HOUSES == {4, 11, 12}
    assert MOVABLE_SIGNS == {"Aries", "Cancer", "Libra", "Capricorn"}
    assert DUAL_SIGNS == {"Gemini", "Virgo", "Sagittarius", "Pisces"}


def test_vehicle_significations_include_drishti():
    from app.services.vehicle import _vehicle_significations
    kundli = {
        "houses": {str(i): {"sign": ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"][i-1]} for i in range(1,13)},
        "planets": {
            "Jupiter": {"house": 9, "sign": "Sagittarius", "nakshatra_lord": "Sun"},
            "Sun": {"house": 1, "sign": "Aries", "nakshatra_lord": "Sun"},
        }
    }
    sig = _vehicle_significations(kundli, "Jupiter")
    assert sig["level_5_drishti"] == [1, 3, 5]
    assert 1 in sig["all"]
