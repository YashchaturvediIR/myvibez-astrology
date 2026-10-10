"""Deterministic Childbirth Promise/Timing/Delivery analysis.

This module intentionally implements only the rules supplied for the project.
It reuses the Phase-2 D1 five-level significator hierarchy and the canonical
Phase-1 360-day Savana-year Vimshottari Dasha calculator.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.significator import (
    SIGN_LORDS,
    _navamsha_info,
    _resolve_significators,
    _dasha_periods,
)

CHILDBIRTH_HOUSES = {2, 5, 11}
DELIVERY_SURGERY_HOUSE = 8
RAHU_NAKSHATRAS = {"Ardra", "Swati", "Shatabhisha"}


def _navamsha_5th_lord(kundli):
    info = _navamsha_info(kundli)
    nav_lagna_index = info["navamsha_lagna_sign_index"]
    signs = list(SIGN_LORDS.keys())
    fifth_index = ((nav_lagna_index - 1 + 4) % 12) + 1
    fifth_sign = signs[fifth_index - 1]
    fifth_lord = SIGN_LORDS[fifth_sign][0]
    return {
        "navamsha_lagna_sign": info["navamsha_lagna_sign"],
        "navamsha_lagna_sign_index": nav_lagna_index,
        "navamsha_5th_house_sign": fifth_sign,
        "navamsha_5th_lord": fifth_lord,
    }


def _parse_iso(value):
    return datetime.fromisoformat(value)


def _active_periods(kundli):
    periods = _dasha_periods(kundli)
    now = datetime.now(ZoneInfo(kundli["birth_details"]["timezone"]))
    active = None
    upcoming = []
    for p in periods:
        if p["md_start"] <= now < p["md_end"]:
            for pd in p["pds"]:
                if pd["start"] <= now < pd["end"]:
                    active = {
                        "md": p["md"], "md_start": p["md_start"].isoformat(timespec="microseconds"),
                        "md_end": p["md_end"].isoformat(timespec="microseconds"),
                        "ad": p["ad"], "ad_start": p["ad_start"].isoformat(timespec="microseconds"),
                        "ad_end": p["ad_end"].isoformat(timespec="microseconds"),
                        "pd": pd["lord"], "pd_start": pd["start"].isoformat(timespec="microseconds"),
                        "pd_end": pd["end"].isoformat(timespec="microseconds"),
                    }
                    break
        for pd in p["pds"]:
            if pd["end"] <= now:
                continue
            if pd["start"] >= now:
                upcoming.append((p, pd))
    return active, upcoming


def calculate_childbirth_analysis(kundli):
    if "planets" not in kundli or "houses" not in kundli or "ascendant" not in kundli:
        raise ValueError("Invalid Kundli JSON: planets, houses and ascendant are required.")
    if "birth_details" not in kundli or "timezone" not in kundli["birth_details"]:
        raise ValueError("Birth details with timezone are required for childbirth timing.")
    if "Moon" not in kundli["planets"] or "longitude" not in kundli["planets"]["Moon"]:
        raise ValueError("Moon longitude is required for Vimshottari timing.")

    rows = _resolve_significators(kundli)
    nav = _navamsha_5th_lord(kundli)
    np = nav["navamsha_5th_lord"]
    np_row = rows[np]

    # Rule 1: NP must signify at least one of houses 2, 5, 11.
    promise_houses = sorted(CHILDBIRTH_HOUSES.intersection(np_row["significator_houses"]))
    rule1 = {
        "navamsha_5th_house_sign": nav["navamsha_5th_house_sign"],
        "navamsha_5th_lord": np,
        "d1_significator_houses": np_row["significator_houses"],
        "childbirth_houses_found": promise_houses,
        "passed": bool(promise_houses),
        "verdict": "Childbirth Promised: YES" if promise_houses else "Childbirth Promised: WEAK / DELAY",
        "five_level_trace": {
            "level_1_star_lord_placement": np_row["level_1_star_lord_placement"],
            "level_2_star_lord_ownership": np_row["level_2_star_lord_ownership"],
            "level_3_planet_placement": np_row["level_3_planet_placement"],
            "level_4_planet_ownership": np_row["level_4_planet_ownership"],
            "level_5_aspects": np_row["level_5_aspects"],
            "nakshatra_lord": np_row["nakshatra_lord"],
        },
    }

    # Rule 2: under the supplied deterministic rule, a D1 House-8 connection
    # means the NP's D1 significator set contains house 8.
    house8 = 8 in np_row["significator_houses"]
    rule2 = {
        "entity_tested": np,
        "d1_significator_houses": np_row["significator_houses"],
        "house_8_found": house8,
        "passed": house8,
        "verdict": (
            "Delivery Type: High probability of Cesarean (C-Section) / Surgical intervention."
            if house8 else "Delivery Type: Favorable for Normal Delivery."
        ),
        "proof": "Navamsha 5th Lord is a D1 house-8 significator." if house8 else "Navamsha 5th Lord is not a D1 house-8 significator.",
    }

    # Rule 3: exact three Rahu checks requested.
    rahu = kundli["planets"].get("Rahu")
    rahu_in_4th = bool(rahu and int(rahu["house"]) == 4)
    np_planet = kundli["planets"][np]
    np_in_rahu_star = np_planet.get("nakshatra") in RAHU_NAKSHATRAS or np_planet.get("nakshatra_lord") == "Rahu"
    np_conj_rahu = bool(rahu and int(np_planet["house"]) == int(rahu["house"]))
    rahu_present = rahu_in_4th or np_in_rahu_star or np_conj_rahu
    rule3 = {
        "rahu_in_4th": rahu_in_4th,
        "d9_5th_lord": np,
        "d9_5th_lord_in_rahu_star": np_in_rahu_star,
        "d9_5th_lord_conjunct_rahu": np_conj_rahu,
        "affliction_present": rahu_present,
        "quality_verdict": (
            "Rahu influence present under the specified rule."
            if rahu_present else "No Rahu dosha present."
        ),
    }

    # Rule 4: each MD/AD/PD lord must qualify for at least one of 2/5/11.
    timing_rows = []
    for period in _dasha_periods(kundli):
        md_q = sorted(CHILDBIRTH_HOUSES.intersection(rows[period["md"]]["significator_houses"]))
        ad_q = sorted(CHILDBIRTH_HOUSES.intersection(rows[period["ad"]]["significator_houses"]))
        if not md_q or not ad_q:
            continue
        for pd in period["pds"]:
            pd_q = sorted(CHILDBIRTH_HOUSES.intersection(rows[pd["lord"]]["significator_houses"]))
            if not pd_q:
                continue
            timing_rows.append({
                "mahadasha": period["md"], "antardasha": period["ad"], "pratyantardasha": pd["lord"],
                "md_start": period["md_start"].isoformat(timespec="microseconds"),
                "md_end": period["md_end"].isoformat(timespec="microseconds"),
                "ad_start": period["ad_start"].isoformat(timespec="microseconds"),
                "ad_end": period["ad_end"].isoformat(timespec="microseconds"),
                "pd_start": pd["start"].isoformat(timespec="microseconds"),
                "pd_end": pd["end"].isoformat(timespec="microseconds"),
                "md_qualifying_houses": md_q,
                "ad_qualifying_houses": ad_q,
                "pd_qualifying_houses": pd_q,
                "trigger_window": "Trigger Window: Highly favorable period for conception/delivery.",
            })

    active, _ = _active_periods(kundli)
    timing = {
        "required_houses": sorted(CHILDBIRTH_HOUSES),
        "rule": "MD, AD and PD must each simultaneously signify at least one of houses 2, 5 or 11.",
        "active_period": active,
        "favorable_timing_windows": timing_rows,
        "earliest_favorable_window": timing_rows[0] if timing_rows else None,
        "vimshottari_method": "Canonical Phase-1 Vimshottari Dasha; 360-day Savana year; exact Moon-based initial balance.",
    }

    return {
        "method": "Deterministic KP & Vedic Childbirth Engine",
        "rule_1_core_promise": rule1,
        "rule_2_delivery_nature": rule2,
        "rule_3_rahu_influence": rule3,
        "rule_4_timing": timing,
        "final_promise": {
            "childbirth_promised": rule1["passed"],
            "verdict": rule1["verdict"],
        },
        "signification_table_2_5_8_11": {
            planet: {
                "significator_houses": row["significator_houses"],
                "houses_2_5_8_11": sorted({2, 5, 8, 11}.intersection(row["significator_houses"])),
            }
            for planet, row in rows.items()
        },
    }
