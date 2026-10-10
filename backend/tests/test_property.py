from app.services.significator import calculate_property_analysis

def sample_kundli():
    return {
        "birth_details": {"date":"2012-12-21","time":"00:00:00","place":"Firozabad, India","latitude":27.1592,"longitude":78.3957,"timezone":"Asia/Kolkata"},
        "settings": {"zodiac":"sidereal","ayanamsha":"Lahiri","node_type":"mean","house_system":"whole_sign"},
        "ascendant": {"longitude":151.7,"sign":"Virgo","sign_index":6,"degree_in_sign":1.7,"house":1},
        "houses": {str(i): {"sign": ["Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces","Aries","Taurus","Gemini","Cancer","Leo"][i-1], "sign_index": ((6+i-2)%12)+1} for i in range(1,13)},
        "planets": {
            "Sun":{"longitude":245.25,"sign":"Sagittarius","sign_index":9,"degree_in_sign":5.25,"house":4,"nakshatra":"Mula","nakshatra_lord":"Ketu","pada":2,"retrograde":False},
            "Moon":{"longitude":341.55,"sign":"Pisces","sign_index":12,"degree_in_sign":11.55,"house":7,"nakshatra":"Uttara Bhadrapada","nakshatra_lord":"Saturn","pada":3,"retrograde":False},
            "Mars":{"longitude":271.84,"sign":"Capricorn","sign_index":10,"degree_in_sign":1.84,"house":5,"nakshatra":"Uttara Ashadha","nakshatra_lord":"Sun","pada":2,"retrograde":False},
            "Mercury":{"longitude":229.63,"sign":"Scorpio","sign_index":8,"degree_in_sign":19.63,"house":3,"nakshatra":"Jyeshtha","nakshatra_lord":"Mercury","pada":1,"retrograde":False},
            "Jupiter":{"longitude":44.94,"sign":"Taurus","sign_index":2,"degree_in_sign":14.94,"house":9,"nakshatra":"Rohini","nakshatra_lord":"Moon","pada":2,"retrograde":True},
            "Venus":{"longitude":221.67,"sign":"Scorpio","sign_index":8,"degree_in_sign":11.67,"house":3,"nakshatra":"Anuradha","nakshatra_lord":"Saturn","pada":3,"retrograde":False},
            "Saturn":{"longitude":194.55,"sign":"Libra","sign_index":7,"degree_in_sign":14.55,"house":2,"nakshatra":"Swati","nakshatra_lord":"Rahu","pada":3,"retrograde":False},
            "Rahu":{"longitude":210.15,"sign":"Scorpio","sign_index":8,"degree_in_sign":0.15,"house":3,"nakshatra":"Vishakha","nakshatra_lord":"Jupiter","pada":4,"retrograde":True},
            "Ketu":{"longitude":30.15,"sign":"Taurus","sign_index":2,"degree_in_sign":0.15,"house":9,"nakshatra":"Krittika","nakshatra_lord":"Sun","pada":2,"retrograde":True},
        }
    }

def test_property_analysis_shape():
    result = calculate_property_analysis(sample_kundli())
    assert "rule_1_navamsa_4th_lord_verification" in result
    assert "rule_2_saturn_mars_connection_verification" in result
    assert "rahu_influence_check" in result
    assert "final_promise_verdict" in result
    assert "timing_of_event" in result

def test_property_houses():
    result = calculate_property_analysis(sample_kundli())
    assert result["property_houses"] == [2,4,11,12]

def test_property_rule1_includes_level5_aspects():
    k = sample_kundli()
    # In this fixture Navamsha 4th lord is Mars. Mars is in D1 house 5 and
    # aspects houses 8, 11 and 12. House 11/12 must therefore be available
    # to Rule 1 through Level 5.
    result = calculate_property_analysis(k)
    rule1 = result["rule_1_navamsa_4th_lord_verification"]
    assert 11 in rule1["levels"]["level_5_aspects"]
    assert 12 in rule1["levels"]["level_5_aspects"]
    assert 11 in rule1["property_houses_found"]
    assert 12 in rule1["property_houses_found"]
