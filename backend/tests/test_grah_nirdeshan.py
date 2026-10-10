from app.services.grah_nirdeshan import calculate_grah_nirdeshan


def sample_kundli():
    # Taurus Lagna: 1=Taurus, 2=Gemini, ..., 12=Aries.
    signs = ["Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces", "Aries"]
    houses = {str(i + 1): {"sign": signs[i]} for i in range(12)}
    planets = {
        "Sun": {"house": 4, "sign": "Leo", "nakshatra_lord": "Mars"},
        "Moon": {"house": 3, "sign": "Cancer", "nakshatra_lord": "Jupiter"},
        "Mars": {"house": 7, "sign": "Scorpio", "nakshatra_lord": "Rahu"},
        "Mercury": {"house": 2, "sign": "Gemini", "nakshatra_lord": "Sun"},
        "Jupiter": {"house": 8, "sign": "Sagittarius", "nakshatra_lord": "Venus"},
        "Venus": {"house": 1, "sign": "Taurus", "nakshatra_lord": "Moon"},
        "Saturn": {"house": 10, "sign": "Aquarius", "nakshatra_lord": "Saturn"},
        "Rahu": {"house": 8, "sign": "Sagittarius", "nakshatra_lord": "Jupiter"},
        "Ketu": {"house": 2, "sign": "Gemini", "nakshatra_lord": "Mercury"},
    }
    return {"houses": houses, "planets": planets}


def test_grah_nirdeshan_non_node_uses_star_and_planet_houses():
    result = calculate_grah_nirdeshan(sample_kundli())
    sun = next(x for x in result["rows"] if x["planet"] == "Sun")
    # Sun: star lord Mars = 7th placement + Mars-owned 7th/12th;
    # Sun itself = 4th placement + Leo-owned 4th.
    assert sun["signified_bhavas"] == [4, 7, 12]


def test_grah_nirdeshan_nodes_add_rashi_lord_and_conjoined_planet():
    result = calculate_grah_nirdeshan(sample_kundli())
    rahu = next(x for x in result["rows"] if x["planet"] == "Rahu")
    # Rahu in Sagittarius: Jupiter is rashi lord, occupying 8 and owning 8/11.
    # Jupiter is also in Rahu's same D-1 house, so its placement/ownership are added.
    assert rahu["node_special_rule"]["rashi_lord"] == "Jupiter"
    assert "Jupiter" in rahu["node_special_rule"]["conjoined_planets_same_d1_house"]
    assert rahu["signified_bhavas"] == [8, 11]


def test_no_cusp_or_aspect_significations_are_added():
    result = calculate_grah_nirdeshan(sample_kundli())
    mercury = next(x for x in result["rows"] if x["planet"] == "Mercury")
    assert "level_5_aspects" not in mercury
    assert mercury["signified_bhavas"] == [2, 4, 5]
