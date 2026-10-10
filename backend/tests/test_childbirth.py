from app.services.childbirth import calculate_childbirth_analysis
from test_property import sample_kundli


def test_childbirth_analysis_shape():
    result = calculate_childbirth_analysis(sample_kundli())
    assert "rule_1_core_promise" in result
    assert "rule_2_delivery_nature" in result
    assert "rule_3_rahu_influence" in result
    assert "rule_4_timing" in result
    assert "final_promise" in result


def test_childbirth_rule1_uses_navamsa_5th_lord():
    result = calculate_childbirth_analysis(sample_kundli())
    r1 = result["rule_1_core_promise"]
    assert r1["navamsha_5th_lord"] in sample_kundli()["planets"]
    assert set(r1["childbirth_houses_found"]).issubset({2, 5, 11})


def test_childbirth_timing_requires_all_three_period_levels():
    result = calculate_childbirth_analysis(sample_kundli())
    for w in result["rule_4_timing"]["favorable_timing_windows"]:
        assert w["md_qualifying_houses"]
        assert w["ad_qualifying_houses"]
        assert w["pd_qualifying_houses"]
