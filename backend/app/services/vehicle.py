"""Deterministic Vehicle Purchasing Astrology engine.

Implements only the five user-specified vehicle rules. Timing is forward-only
from the query runtime and uses the canonical Phase-1 Vimshottari periods and
Phase-4 Grah Nirdeshan significations.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.grah_nirdeshan import calculate_grah_nirdeshan
from app.services.significator import SIGN_LORDS, _navamsha_info, _dasha_periods, OWN_SIGNS

VEHICLE_HOUSES = {4, 11, 12}
MOVABLE_SIGNS = {"Aries", "Cancer", "Libra", "Capricorn"}
DUAL_SIGNS = {"Gemini", "Virgo", "Sagittarius", "Pisces"}
VENUS_SIGNS = {"Taurus", "Libra"}


def _now(kundli, query_datetime=None):
    tz = ZoneInfo(kundli["birth_details"]["timezone"])
    if query_datetime:
        value = query_datetime.strip()
        if value.endswith(("Z", "z")):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    return datetime.now(tz)


def _navamsha_4th_lord(kundli):
    info = _navamsha_info(kundli)
    lagna = info["navamsha_lagna_sign_index"]
    signs = list(SIGN_LORDS.keys())
    fourth_index = ((lagna - 1 + 3) % 12) + 1
    fourth_sign = signs[fourth_index - 1]
    lord = SIGN_LORDS[fourth_sign][0]
    return {
        "navamsha_lagna_sign": info["navamsha_lagna_sign"],
        "navamsha_4th_house_sign": fourth_sign,
        "navamsha_4th_lord": lord,
    }


def _iso(dt):
    return dt.isoformat(timespec="microseconds")


ASPECT_OFFSETS = {
    "Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7],
    "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10],
    "Rahu": [7], "Ketu": [7],
}

def _d1_sign_to_houses(kundli):
    result = {sign: [] for sign in SIGN_LORDS}
    for house_num, house_data in kundli["houses"].items():
        result.setdefault(house_data["sign"], []).append(int(house_num))
    return result

def _owned_houses(planet, sign_to_houses):
    houses = []
    for sign in OWN_SIGNS.get(planet, []):
        houses.extend(sign_to_houses.get(sign, []))
    return houses

def _aspect_houses_from_house(planet, house):
    offsets = ASPECT_OFFSETS.get(planet, [7])
    return [((house - 1 + offset - 1) % 12) + 1 for offset in offsets]

def _vehicle_significations(kundli, planet):
    """Vehicle-specific 5-tier significations, including Level-5 Drishti.

    The global Grah Nirdeshan table intentionally follows its own supplied
    specification and does not add aspects. Vehicle Rule 1/2, however,
    requires the Navamsha 4th Lord and dasha planets to be evaluated as
    significators including Drishti, so this calculation is kept local to
    vehicle analysis.
    """
    planets = kundli["planets"]
    p = planets[planet]
    sign_to_houses = _d1_sign_to_houses(kundli)
    star = p.get("nakshatra_lord")
    if not star or star not in planets:
        raise ValueError(f"Nakshatra Lord (न) is missing/invalid for {planet}.")

    level1 = [int(planets[star]["house"])]
    level2 = _owned_houses(star, sign_to_houses)
    level3 = [int(p["house"])]
    level4 = _owned_houses(planet, sign_to_houses)
    level5 = _aspect_houses_from_house(planet, int(p["house"]))
    all_houses = sorted(set(level1 + level2 + level3 + level4 + level5))
    return {
        "all": all_houses,
        "level_1_star_lord_placement": sorted(set(level1)),
        "level_2_star_lord_ownership": sorted(set(level2)),
        "level_3_planet_placement": sorted(set(level3)),
        "level_4_planet_ownership": sorted(set(level4)),
        "level_5_drishti": sorted(set(level5)),
    }

def _vehicle_promise(kundli, table, nav):
    np = nav["navamsha_4th_lord"]
    details = _vehicle_significations(kundli, np)
    np_houses = details["all"]
    found = sorted(VEHICLE_HOUSES.intersection(np_houses))
    return {
        "navamsha_4th_lord": np,
        "signified_bhavas": np_houses,
        "vehicle_houses_found": found,
        "passed": bool(found),
        "levels": details,
        "drishti_included": True,
        "drishti_rule": "Level 5 adds the houses directly aspected by the planet (7th for Sun/Moon/Mercury/Venus, 4/7/8 Mars, 5/7/9 Jupiter, 3/7/10 Saturn).",
    }


def _venus_rule(kundli, nav):
    planets = kundli["planets"]
    np = nav["navamsha_4th_lord"]
    npp = planets[np]
    venus = planets["Venus"]
    evidence = []

    if np == "Venus":
        evidence.append("Navamsha 4th Lord is Venus itself.")
    if npp.get("sign") in VENUS_SIGNS:
        evidence.append(f"{np} is in {npp['sign']}, a Venus-owned Rashi.")
    if npp.get("nakshatra_lord") == "Venus":
        evidence.append(f"{np} is in Venus's Nakshatra ({npp.get('nakshatra')}).")
    # Up-Nakshatra/Sub-lord is honored when present in the Phase-1 payload.
    if npp.get("nakshatra_sub_lord") == "Venus" or npp.get("sub_lord") == "Venus":
        evidence.append(f"{np} is in Venus's Up-Nakshatra/Sub-lord.")

    np_house = int(npp["house"])
    venus_house = int(venus["house"])
    if np_house == venus_house:
        evidence.append(f"{np} is conjunct Venus in D-1 house {np_house}.")
    # Venus's 7th aspect to NP or NP's 7th aspect to Venus.
    if ((venus_house - 1 + 6) % 12) + 1 == np_house:
        evidence.append("Venus casts its 7th Drishti on the Navamsha 4th Lord.")
    if ((np_house - 1 + 6) % 12) + 1 == venus_house:
        evidence.append(f"{np} casts its 7th Drishti on Venus.")

    venus_star_lord = venus.get("nakshatra_lord")
    venus_star_placed_movable = bool(venus_star_lord and planets.get(venus_star_lord, {}).get("sign") in MOVABLE_SIGNS)
    return {
        "navamsha_4th_lord": np,
        "connection_evidence": evidence,
        "connection_found": bool(evidence),
        "venus_nakshatra_lord": venus_star_lord,
        "venus_nakshatra_lord_sign": planets.get(venus_star_lord, {}).get("sign") if venus_star_lord else None,
        "venus_nakshatra_lord_in_movable_sign": venus_star_placed_movable,
        "passed": bool(evidence) and venus_star_placed_movable,
        "required_condition": "Venus's Nakshatra Swami must be placed in a Char (Movable) Rashi.",
    }


def _vehicle_type(kundli, nav):
    sign = kundli["planets"][nav["navamsha_4th_lord"]]["sign"]
    if sign in MOVABLE_SIGNS:
        vehicle = "4-wheeler"
    elif sign in DUAL_SIGNS:
        vehicle = "2-wheeler"
    else:
        vehicle = "Not specified by supplied rule"
    return {"navamsha_4th_lord": nav["navamsha_4th_lord"], "d1_rashi": sign, "vehicle_type": vehicle}


def _dasha_match(period, now, kundli, table):
    if period["md_end"] <= now:
        return None
    md, ad = period["md"], period["ad"]
    md_h = set(_vehicle_significations(kundli, md)["all"]); ad_h = set(_vehicle_significations(kundli, ad)["all"])
    if not (md_h & VEHICLE_HOUSES) or not (ad_h & VEHICLE_HOUSES):
        return None
    # Table alone is enough for house coverage; synergy is checked by caller.
    for pd in period["pds"]:
        if pd["end"] <= now:
            continue
        pd_lord = pd["lord"]
        pd_h = set(_vehicle_significations(kundli, pd_lord)["all"])
        if not (pd_h & VEHICLE_HOUSES):
            continue
        if not VEHICLE_HOUSES <= (md_h | ad_h | pd_h):
            continue
        yield pd


def calculate_vehicle_analysis(kundli, query_datetime=None):
    if "planets" not in kundli or "houses" not in kundli:
        raise ValueError("Invalid Kundli JSON: planets and houses are required.")
    grah = calculate_grah_nirdeshan(kundli)
    table = grah["table"]
    nav = _navamsha_4th_lord(kundli)
    promise = _vehicle_promise(kundli, table, nav)
    venus = _venus_rule(kundli, nav)
    vehicle_type = _vehicle_type(kundli, nav)
    now = _now(kundli, query_datetime)
    planets = kundli["planets"]

    dasha_matches = []
    for period in _dasha_periods(kundli):
        for pd in _dasha_match(period, now, kundli, table) or []:
            md, ad, pdl = period["md"], period["ad"], pd["lord"]
            md_ad_synergy = planets[md].get("nakshatra_lord") == ad and planets[ad].get("sign") == planets[md].get("sign")
            reverse_synergy = planets[ad].get("nakshatra_lord") == md and planets[md].get("sign") == planets[ad].get("sign")
            if not (md_ad_synergy or reverse_synergy):
                continue
            start = max(pd["start"], now) if pd["start"] < now else pd["start"]
            md_sig = _vehicle_significations(kundli, md)
            ad_sig = _vehicle_significations(kundli, ad)
            pd_sig = _vehicle_significations(kundli, pdl)
            union = sorted(set(md_sig["all"]) | set(ad_sig["all"]) | set(pd_sig["all"]))
            dasha_matches.append({
                "md": md, "ad": ad, "pd": pdl,
                "start": _iso(start), "end": _iso(pd["end"]),
                "md_start": _iso(period["md_start"]), "md_end": _iso(period["md_end"]),
                "ad_start": _iso(period["ad_start"]), "ad_end": _iso(period["ad_end"]),
                "house_activation": {
                    "md": md_sig["all"], "ad": ad_sig["all"], "pd": pd_sig["all"],
                    "target_houses": sorted(VEHICLE_HOUSES), "union": union,
                },
                "synergy": {
                    "forward": md_ad_synergy,
                    "reverse": reverse_synergy,
                    "md_nakshatra_lord": planets[md].get("nakshatra_lord"),
                    "ad_nakshatra_lord": planets[ad].get("nakshatra_lord"),
                    "md_rashi": planets[md].get("sign"),
                    "ad_rashi": planets[ad].get("sign"),
                },
            })
            break
        if dasha_matches:
            break

    result = {
        "method": "Deterministic Vehicle Purchasing Astrology — supplied rules only",
        "query_reference_datetime": _iso(now),
        "target_houses": sorted(VEHICLE_HOUSES),
        "rule_1_navamsha_4th_lord": {**nav, **promise},
        "rule_3_venus_connection": venus,
        "rule_5_vehicle_type": vehicle_type,
        "rule_2_dasha_combined_significators": {
            "target_houses": sorted(VEHICLE_HOUSES),
            "matches": dasha_matches,
            "earliest_match": dasha_matches[0] if dasha_matches else None,
            "status": "MATCH FOUND" if dasha_matches else "NO MATCHING DASHA FOUND",
        },
        "rule_4_dasha_antardasha_synergy": "Applied as MD-in-AD-Nakshatra + AD-in-MD-Rashi, or the reverse, to every timing candidate.",
        "final_vehicle_promise": "YES" if promise["passed"] and venus["passed"] else "NO",
        "rule_status": {
            "rule_1": promise["passed"],
            "rule_2_timing": bool(dasha_matches),
            "rule_3_venus": venus["passed"],
        },
    }
    return result
