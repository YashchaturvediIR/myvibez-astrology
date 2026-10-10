NAKSHATRAS = [
    ("Ashwini", "Ketu"), ("Bharani", "Venus"), ("Krittika", "Sun"),
    ("Rohini", "Moon"), ("Mrigashira", "Mars"), ("Ardra", "Rahu"),
    ("Punarvasu", "Jupiter"), ("Pushya", "Saturn"), ("Ashlesha", "Mercury"),
    ("Magha", "Ketu"), ("Purva Phalguni", "Venus"), ("Uttara Phalguni", "Sun"),
    ("Hasta", "Moon"), ("Chitra", "Mars"), ("Swati", "Rahu"),
    ("Vishakha", "Jupiter"), ("Anuradha", "Saturn"), ("Jyeshtha", "Mercury"),
    ("Mula", "Ketu"), ("Purva Ashadha", "Venus"), ("Uttara Ashadha", "Sun"),
    ("Shravana", "Moon"), ("Dhanishtha", "Mars"), ("Shatabhisha", "Rahu"),
    ("Purva Bhadrapada", "Jupiter"), ("Uttara Bhadrapada", "Saturn"), ("Revati", "Mercury"),
]
NAK_SPAN = 360.0 / 27.0
PADA_SPAN = NAK_SPAN / 4.0

def nakshatra_from_longitude(longitude: float) -> dict:
    lon = longitude % 360.0
    idx = min(26, int((lon + 1e-10) // NAK_SPAN))
    within = lon - idx * NAK_SPAN
    pada = min(4, int((within + 1e-12) // PADA_SPAN) + 1)
    name, lord = NAKSHATRAS[idx]
    return {
        "name": name,
        "index": idx + 1,
        "lord": lord,
        "pada": pada,
        "degree_in_nakshatra": within,
    }
