from app.services.significator import calculate_significators

def sample_kundli():
    signs = ["Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius",
             "Pisces","Aries","Taurus","Gemini","Cancer","Leo"]
    houses = {str(i+1): {"sign": signs[i], "sign_index": i+1} for i in range(12)}
    planets = {
        "Sun": {"house": 4, "sign": "Sagittarius", "nakshatra": "Mula", "nakshatra_lord": "Ketu"},
        "Moon": {"house": 7, "sign": "Pisces", "nakshatra": "Uttara Bhadrapada", "nakshatra_lord": "Saturn"},
        "Mars": {"house": 5, "sign": "Capricorn", "nakshatra": "Uttara Ashadha", "nakshatra_lord": "Sun"},
        "Mercury": {"house": 3, "sign": "Scorpio", "nakshatra": "Jyeshtha", "nakshatra_lord": "Mercury"},
        "Jupiter": {"house": 9, "sign": "Taurus", "nakshatra": "Rohini", "nakshatra_lord": "Moon"},
        "Venus": {"house": 3, "sign": "Scorpio", "nakshatra": "Anuradha", "nakshatra_lord": "Saturn"},
        "Saturn": {"house": 2, "sign": "Libra", "nakshatra": "Swati", "nakshatra_lord": "Rahu"},
        "Rahu": {"house": 3, "sign": "Scorpio", "nakshatra": "Vishakha", "nakshatra_lord": "Jupiter"},
        "Ketu": {"house": 9, "sign": "Taurus", "nakshatra": "Krittika", "nakshatra_lord": "Sun"},
    }
    return {"houses": houses, "planets": planets}

def test_significator_basic_rules():
    result = calculate_significators(sample_kundli())["significators"]
    # Sun: occupied H4; own sign Leo is H12; star lord Ketu occupies H9;
    # Ketu has no own sign; Sun's 7th aspect from H4 is H10.
    assert result["Sun"]["occupied_house"] == [4]
    assert result["Sun"]["own_sign_houses"] == [12]
    assert result["Sun"]["nakshatra_lord_house"] == [9]
    assert result["Sun"]["aspect_houses"] == [10]
    # New hierarchy order: Level 1, 2, 3, 4, 5.
    assert result["Sun"]["significator_houses"][:4] == [9, 4, 12, 10]
    # Sun is in Ketu's nakshatra, so Rule 7 adds Ketu's final houses.
    assert set(result["Ketu"]["significator_houses"]).issubset(
        set(result["Sun"]["significator_houses"])
    )

def test_aspects():
    result = calculate_significators(sample_kundli())["significators"]
    # Mars from H5 aspects H8, H11, H12.
    assert result["Mars"]["aspect_houses"] == [8, 11, 12]
    # Jupiter from H9 aspects H1, H3, H5.
    assert result["Jupiter"]["aspect_houses"] == [1, 3, 5]
    # Saturn from H2 aspects H4, H8, H11.
    assert result["Saturn"]["aspect_houses"] == [4, 8, 11]

def test_node_sign_lord_inheritance():
    result = calculate_significators(sample_kundli())["significators"]
    # Rahu is in Scorpio; Scorpio's lord is Mars.
    assert result["Rahu"]["sign_lord"] == "Mars"
    for h in result["Mars"]["significator_houses"]:
        assert h in result["Rahu"]["node_inherited_houses"]
