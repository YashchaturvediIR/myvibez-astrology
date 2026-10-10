from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import swisseph as swe

from app.services.zodiac import sign_from_longitude, SIGNS
from app.services.nakshatra import nakshatra_from_longitude
from app.services.houses import whole_sign_house, whole_sign_houses
from app.services.dasha import calculate_vimshottari_dasha

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}
NODE_FLAGS = {"mean": swe.MEAN_NODE, "true": swe.TRUE_NODE}

def _parse_birth(birth):
    try:
        local = datetime.fromisoformat(f"{birth.date}T{birth.time}").replace(
            tzinfo=ZoneInfo(birth.timezone)
        )
    except Exception as exc:
        raise ValueError(f"Invalid date/time/timezone: {exc}")
    return local, local.astimezone(timezone.utc)

def _jd_from_utc(dt):
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute / 60 + dt.second / 3600)

def _planet_record(name, lon, house):
    s = sign_from_longitude(lon)
    n = nakshatra_from_longitude(lon)
    return {
        "longitude": lon,
        "sign": s["name"],
        "sign_index": s["index"],
        "degree_in_sign": s["degree_in_sign"],
        "house": house,
        "retrograde": False,
        "nakshatra": n["name"],
        "nakshatra_index": n["index"],
        "nakshatra_lord": n["lord"],
        "pada": n["pada"],
        "degree_in_nakshatra": n["degree_in_nakshatra"],
    }

def calculate_kundli(request):
    birth = request.birth_details
    settings = request.settings
    local, utc = _parse_birth(birth)

    if settings.zodiac != "sidereal":
        raise ValueError("Only sidereal zodiac is currently supported.")
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = _jd_from_utc(utc)

    # Calculate sidereal ascendant using Swiss Ephemeris houses.
    cusps, ascmc = swe.houses_ex(
        jd, birth.latitude, birth.longitude, b'P', swe.FLG_SIDEREAL
    )
    asc_lon = ascmc[0] % 360.0
    asc_sign = sign_from_longitude(asc_lon)

    # Whole-sign houses are assigned from the ascendant sign.
    houses = whole_sign_houses(asc_sign["index"])
    for h, data in houses.items():
        data["sign"] = SIGNS[data["sign_index"] - 1]
        data["start_longitude"] = (data["sign_index"] - 1) * 30.0
        data["end_longitude"] = data["sign_index"] * 30.0

    planets = {}
    for name, body in PLANETS.items():
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        xx, retflag = swe.calc_ut(jd, body, flags)
        lon = xx[0] % 360.0
        s = sign_from_longitude(lon)
        house = whole_sign_house(s["index"], asc_sign["index"])
        rec = _planet_record(name, lon, house)
        rec["retrograde"] = xx[3] < 0
        planets[name] = rec

    node_body = NODE_FLAGS[settings.node_type]
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    xx, retflag = swe.calc_ut(jd, node_body, flags)
    rahu_lon = xx[0] % 360.0
    ketu_lon = (rahu_lon + 180.0) % 360.0
    for name, lon in [("Rahu", rahu_lon), ("Ketu", ketu_lon)]:
        s = sign_from_longitude(lon)
        house = whole_sign_house(s["index"], asc_sign["index"])
        rec = _planet_record(name, lon, house)
        rec["retrograde"] = True
        planets[name] = rec

    ayan = swe.get_ayanamsa_ut(jd)

    return {
        "birth_details": {
            "date": birth.date,
            "time": birth.time,
            "place": birth.place,
            "latitude": birth.latitude,
            "longitude": birth.longitude,
            "timezone": birth.timezone,
            "utc_datetime": utc.isoformat().replace("+00:00", "Z"),
        },
        "settings": {
            "zodiac": settings.zodiac,
            "ayanamsha": settings.ayanamsha,
            "ayanamsha_value": ayan,
            "node_type": settings.node_type,
            "house_system": settings.house_system,
        },
        "ascendant": {
            "longitude": asc_lon,
            "sign": asc_sign["name"],
            "sign_index": asc_sign["index"],
            "degree_in_sign": asc_sign["degree_in_sign"],
            "house": 1,
        },
        "houses": houses,
        "planets": planets,
        "vimshottari_dasha": calculate_vimshottari_dasha({
            "birth_details": {
                "date": birth.date,
                "time": birth.time,
                "timezone": birth.timezone,
            },
            "planets": planets,
        }),
    }
