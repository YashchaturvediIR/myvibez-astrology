from decimal import Decimal
from datetime import datetime
from app.services.dasha import calculate_vimshottari_dasha


def sample_kundli():
    return {
        "birth_details": {
            "date": "2007-10-05",
            "time": "10:30:00",
            "timezone": "Asia/Kolkata",
        },
        "planets": {
            "Moon": {"longitude": 99.58496240331}
        },
    }


def test_initial_balance_uses_exact_800_arcminutes():
    d = calculate_vimshottari_dasha(sample_kundli())
    m = d["moon_calculation"]
    assert m["janma_nakshatra"] == "Pushya"
    assert m["nakshatra_lord"] == "Saturn"
    assert m["nakshatra_pada"] == 2
    expected = Decimal("19") * Decimal(m["remaining_arcminutes"]) / Decimal("800")
    assert abs(Decimal(m["initial_balance_years"]) - expected) < Decimal("0.000000000001")


def test_sequence_and_verification():
    d = calculate_vimshottari_dasha(sample_kundli())
    assert d["sequence"] == ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    v = d["verification"]
    assert v["full_planetary_cycle_equals_120"]
    assert v["birth_horizon_equals_120"]
    assert v["all_antardashas_equal_parent_mahadasha"]
    assert v["all_pratyantardashas_equal_parent_antardasha"]
    assert v["no_mahadasha_gaps_or_overlaps"]
    assert v["no_antardasha_gaps_or_overlaps"]
    assert v["no_pratyantardasha_gaps_or_overlaps"]
    assert v["initial_balance_formula_verified"]


def test_ad_pd_formula_for_first_period():
    d = calculate_vimshottari_dasha(sample_kundli())
    md = Decimal(d["mahadasha"][0]["duration"])
    ad = d["antardasha"][0]
    expected_ad = md * Decimal("19") / Decimal("120")
    assert abs(Decimal(ad["duration"]) - expected_ad) < Decimal("0.000000000001")

    ad_duration = Decimal(ad["duration"])
    pd = d["pratyantardasha"][0]
    expected_pd = ad_duration * Decimal("19") / Decimal("120")
    assert abs(Decimal(pd["duration"]) - expected_pd) < Decimal("0.000000000001")
