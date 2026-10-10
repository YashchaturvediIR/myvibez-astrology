"""Forward-only multi-event KP timing engine.

Uses the canonical Phase-1 Vimshottari periods and the Phase-4 Grah Nirdeshan
significations. No past interval is returned and no period is forced to match.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.grah_nirdeshan import calculate_grah_nirdeshan
from app.services.significator import SIGN_LORDS, _navamsha_info, _dasha_periods

EVENTS = {
    "childbirth": {"label": "Childbirth", "houses": {2, 5, 11}, "primary": 5},
    "marriage": {"label": "Marriage", "houses": {2, 7, 11}, "primary": 7},
    "property": {"label": "Property / Real Estate", "houses": {4, 11, 12}, "primary": 4},
    "job": {"label": "Job / Promotion", "houses": {2, 6, 10, 11}, "primary": 10},
    "foreign": {"label": "Foreign Travel / Relocation", "houses": {3, 9, 12}, "primary": 9},
    "litigation_disease": {"label": "Litigation / Disease", "houses": {6, 8, 12}, "primary": 8},
}


def _now(kundli, query_datetime=None):
    tz = ZoneInfo(kundli["birth_details"]["timezone"])
    if query_datetime:
        # Accept both ISO-8601 offsets (e.g. +05:30) and UTC Z suffix.
        # JavaScript Date.toISOString() always emits the latter.
        iso_value = query_datetime.strip()
        if iso_value.endswith(("Z", "z")):
            iso_value = iso_value[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    return datetime.now(tz)


def _navamsha_primary_lord(kundli, primary_house):
    info = _navamsha_info(kundli)
    lagna = info["navamsha_lagna_sign_index"]
    signs = list(SIGN_LORDS.keys())
    sign_index = ((lagna - 1 + primary_house - 1) % 12) + 1
    sign = signs[sign_index - 1]
    lord = SIGN_LORDS[sign][0]
    return {"navamsha_lagna_sign": info["navamsha_lagna_sign"],
            "house": primary_house, "sign": sign, "lord": lord}


def _iso(dt):
    return dt.isoformat(timespec="microseconds")


def _period_matches(period, now, houses_by_planet, target):
    # End > T0 includes the currently running period; intersection with T0 is
    # used so the returned valid window starts at T0 when the match is active.
    if period["md_end"] <= now:
        return False
    md = period["md"]
    ad = period["ad"]
    for pd in period["pds"]:
        if pd["end"] <= now:
            continue
        md_houses = set(houses_by_planet.get(md, []))
        if not (md_houses & target):
            continue
        union = (md_houses |
                 set(houses_by_planet.get(ad, [])) |
                 set(houses_by_planet.get(pd["lord"], [])))
        if target <= union:
            start = max(pd["start"], now) if pd["start"] < now else pd["start"]
            return {
                "md": md, "ad": ad, "pd": pd["lord"],
                "start": start, "end": pd["end"],
                "md_start": period["md_start"], "md_end": period["md_end"],
                "ad_start": period["ad_start"], "ad_end": period["ad_end"],
                "coverage": sorted(union),
            }
    return None


def calculate_event_timing(kundli, topic, query_datetime=None):
    key = topic.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {"child": "childbirth", "vivah": "marriage", "house": "property",
               "real_estate": "property", "job_promotion": "job", "foreign_travel": "foreign",
               "relocation": "foreign", "litigation": "litigation_disease", "disease": "litigation_disease"}
    key = aliases.get(key, key)
    if key not in EVENTS:
        raise ValueError(f"Unsupported event topic: {topic}. Use one of: {', '.join(EVENTS)}")

    event = EVENTS[key]
    target = set(event["houses"])
    now = _now(kundli, query_datetime)
    grah = calculate_grah_nirdeshan(kundli)
    houses_by_planet = grah["table"]
    nav = _navamsha_primary_lord(kundli, event["primary"])
    np = nav["lord"]
    np_houses = sorted(set(houses_by_planet.get(np, [])))
    promise_houses = sorted(target.intersection(np_houses))

    result = {
        "query_category": event["label"],
        "target_houses": sorted(target),
        "primary_house": event["primary"],
        "query_reference_datetime": _iso(now),
        "query_reference_date": now.strftime("%d/%m/%Y"),
        "promise_status": "CONFIRMED" if promise_houses else "NOT CONFIRMED",
        "navamsha_key_lord": np,
        "navamsha_primary_house": nav,
        "navamsha_key_lord_signified_bhavas": np_houses,
        "promise_houses_found": promise_houses,
        "timing": None,
    }
    if not promise_houses:
        result["reason"] = "Event not promised via Navamsha lord; timing search terminated."
        result["timing"] = {
            "status": "NOT SEARCHED",
            "reason": result["reason"]
        }
        return result

    match = None
    for period in _dasha_periods(kundli):
        match = _period_matches(period, now, houses_by_planet, target)
        if match:
            break

    if not match:
        result["timing"] = {
            "status": "NO MATCHING DASHA FOUND",
            "reason": f"No upcoming joint Dasha sequence from {result['query_reference_date']} onward satisfies complete activation of houses {sorted(target)}."
        }
        return result

    md_h = sorted(set(houses_by_planet.get(match["md"], [])))
    ad_h = sorted(set(houses_by_planet.get(match["ad"], [])))
    pd_h = sorted(set(houses_by_planet.get(match["pd"], [])))
    result["timing"] = {
        "status": "MATCH FOUND",
        "dasha_combination": f"{match['md']} / {match['ad']} / {match['pd']}",
        "md": match["md"], "ad": match["ad"], "pd": match["pd"],
        "valid_start": _iso(match["start"]), "valid_end": _iso(match["end"]),
        "md_start": _iso(match["md_start"]), "md_end": _iso(match["md_end"]),
        "ad_start": _iso(match["ad_start"]), "ad_end": _iso(match["ad_end"]),
        "house_activation": {
            "md": {"planet": match["md"], "signified_houses": md_h},
            "ad": {"planet": match["ad"], "signified_houses": ad_h},
            "pd": {"planet": match["pd"], "signified_houses": pd_h},
            "target_set_coverage": sorted(target),
            "union": match["coverage"],
        },
    }
    return result


def calculate_all_upcoming_events(kundli, query_datetime=None):
    return {key: calculate_event_timing(kundli, key, query_datetime) for key in EVENTS}
