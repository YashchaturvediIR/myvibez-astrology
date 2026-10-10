from app.services.zodiac import sign_from_longitude
from app.services.nakshatra import nakshatra_from_longitude

def test_zodiac():
    assert sign_from_longitude(0)["name"] == "Aries"
    assert sign_from_longitude(30)["name"] == "Taurus"

def test_nakshatra():
    assert nakshatra_from_longitude(0)["name"] == "Ashwini"
    assert nakshatra_from_longitude(13.3333333333)["name"] == "Bharani"

def test_nakshatra_lord():
    assert nakshatra_from_longitude(13.3333333334)["lord"] == "Venus"
