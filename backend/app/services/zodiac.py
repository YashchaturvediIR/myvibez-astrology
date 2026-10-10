SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def sign_from_longitude(longitude: float) -> dict:
    lon = longitude % 360.0
    idx = int(lon / 30.0)
    return {
        "name": SIGNS[idx],
        "index": idx + 1,
        "degree_in_sign": lon - idx * 30.0,
    }
