"""
Deterministic Bhava-Navamsha / KP significator + marriage timing engine.

IMPORTANT: This module intentionally follows ONLY the algorithm supplied by the
project owner. It does not apply generic Jyotish rules or AI interpretation.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.services.dasha import calculate_vimshottari_dasha

SIGN_LORDS = {
    "Aries": ["Mars"], "Taurus": ["Venus"], "Gemini": ["Mercury"],
    "Cancer": ["Moon"], "Leo": ["Sun"], "Virgo": ["Mercury"],
    "Libra": ["Venus"], "Scorpio": ["Mars"], "Sagittarius": ["Jupiter"],
    "Capricorn": ["Saturn"], "Aquarius": ["Saturn"], "Pisces": ["Jupiter"],
}
OWN_SIGNS = {
    "Sun": ["Leo"], "Moon": ["Cancer"], "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"], "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"], "Saturn": ["Capricorn", "Aquarius"],
    "Rahu": [], "Ketu": [],
}
NAKSHATRA_LORDS = {
    "Ashwini": "Ketu", "Bharani": "Venus", "Krittika": "Sun", "Rohini": "Moon",
    "Mrigashira": "Mars", "Ardra": "Rahu", "Punarvasu": "Jupiter", "Pushya": "Saturn",
    "Ashlesha": "Mercury", "Magha": "Ketu", "Purva Phalguni": "Venus",
    "Uttara Phalguni": "Sun", "Hasta": "Moon", "Chitra": "Mars", "Swati": "Rahu",
    "Vishakha": "Jupiter", "Anuradha": "Saturn", "Jyeshtha": "Mercury",
    "Mula": "Ketu", "Purva Ashadha": "Venus", "Uttara Ashadha": "Sun",
    "Shravana": "Moon", "Dhanishtha": "Mars", "Shatabhisha": "Rahu",
    "Purva Bhadrapada": "Jupiter", "Uttara Bhadrapada": "Saturn", "Revati": "Mercury",
}
ASPECT_OFFSETS = {
    "Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7],
    "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10],
    "Rahu": [7], "Ketu": [7],
}
DASHA_SEQUENCE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
               "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
MARRIAGE_HOUSES = {2, 7, 11}
NAK_SPAN = 360.0 / 27.0


def _unique(values):
    out, seen = [], set()
    for value in values:
        if value is not None and value not in seen:
            seen.add(value); out.append(value)
    return out


def _houses_for_sign(sign, sign_to_houses):
    return list(sign_to_houses.get(sign, []))


def _aspect_houses(planet, occupied_house):
    return [((occupied_house - 1 + offset - 1) % 12) + 1
            for offset in ASPECT_OFFSETS.get(planet, [7])]


def _build_indexes(kundli):
    planets = kundli["planets"]
    sign_to_houses = {sign: [] for sign in SIGN_LORDS}
    for house_num, house_data in kundli["houses"].items():
        sign_to_houses.setdefault(house_data["sign"], []).append(int(house_num))
    return planets, sign_to_houses


def _base_levels(planet, planets, sign_to_houses):
    p = planets[planet]
    own_house = int(p["house"])
    own_sign_houses = []
    for sign in OWN_SIGNS.get(planet, []):
        own_sign_houses.extend(_houses_for_sign(sign, sign_to_houses))

    nak_lord = p.get("nakshatra_lord") or NAKSHATRA_LORDS.get(p.get("nakshatra"))
    nak_lord_house = int(planets[nak_lord]["house"]) if nak_lord in planets else None
    nak_lord_sign_houses = []
    for sign in OWN_SIGNS.get(nak_lord, []):
        nak_lord_sign_houses.extend(_houses_for_sign(sign, sign_to_houses))

    return {
        "level_1_star_lord_placement": [nak_lord_house] if nak_lord_house else [],
        "level_2_star_lord_ownership": _unique(nak_lord_sign_houses),
        "level_3_planet_placement": [own_house],
        "level_4_planet_ownership": _unique(own_sign_houses),
        "level_5_aspects": _unique(_aspect_houses(planet, own_house)),
        "nakshatra_lord": nak_lord,
        "sign_lord": SIGN_LORDS.get(p["sign"], [None])[0],
        "occupied_house": [own_house],
    }


def _navamsha_sign(sign_index, degree_in_sign):
    # Movable signs start navamsha from themselves; fixed from 9th; dual from 5th.
    # 0-based sign index: Aries=0 ... Pisces=11.
    modality = (sign_index - 1) % 3
    start_offset = {0: 0, 1: 8, 2: 4}[modality]
    nav_index = min(8, int((degree_in_sign / (30.0 / 9.0))))
    return ((sign_index - 1 + start_offset + nav_index) % 12) + 1


def _navamsha_info(kundli):
    asc = kundli.get("ascendant")
    if not asc:
        # Backward-compatible path for isolated significator unit tests.
        house1 = kundli.get("houses", {}).get("1")
        if not house1:
            raise ValueError("Kundli JSON requires ascendant or house 1 for Navamsha calculation.")
        asc = {"sign_index": house1["sign_index"], "degree_in_sign": 0.0}
    nav_sign_index = _navamsha_sign(int(asc["sign_index"]), float(asc["degree_in_sign"]))
    signs = list(SIGN_LORDS.keys())
    nav_sign = signs[nav_sign_index - 1]
    seventh_index = ((nav_sign_index - 1 + 6) % 12) + 1
    seventh_sign = signs[seventh_index - 1]
    seventh_lord = SIGN_LORDS[seventh_sign][0]
    return {
        "navamsha_lagna_sign": nav_sign,
        "navamsha_lagna_sign_index": nav_sign_index,
        "navamsha_7th_sign": seventh_sign,
        "navamsha_7th_lord": seventh_lord,
        "rule": "Navamsha 7th Lord must signify house 2, 7 or 11 in the Lagna Kundali.",
    }


def _resolve_significators(kundli):
    planets, sign_to_houses = _build_indexes(kundli)
    rows = {}
    for planet in planets:
        c = _base_levels(planet, planets, sign_to_houses)
        base = _unique(
            c["level_1_star_lord_placement"] + c["level_2_star_lord_ownership"] +
            c["level_3_planet_placement"] + c["level_4_planet_ownership"] + c["level_5_aspects"]
        )
        rows[planet] = {
            "planet": planet,
            **c,
            # Compatibility aliases retained from the original Phase-2 schema.
            "own_sign_houses": c["level_4_planet_ownership"],
            "nakshatra_lord_house": c["level_1_star_lord_placement"],
            "nakshatra_lord_own_sign_houses": c["level_2_star_lord_ownership"],
            "aspect_houses": c["level_5_aspects"],
            "node_inherited_houses": [],
            "conjoined_planet_houses": [],
            "significator_houses": base,
        }

    # Resolve node proxies and Rule 7 to a stable closure. This matters when a
    # dispositor/conjoined planet is itself in a node's nakshatra.
    for _ in range(20):
        changed = False
        for node in ("Rahu", "Ketu"):
            if node not in rows:
                continue
            dispositor = rows[node]["sign_lord"]
            inherited = list(rows[dispositor]["significator_houses"]) if dispositor in rows else []
            node_house = int(planets[node]["house"])
            conjoined = []
            for other, data in planets.items():
                if other != node and int(data["house"]) == node_house:
                    conjoined.extend(rows[other]["significator_houses"])
            new_inherited = _unique(inherited)
            new_conjoined = _unique(conjoined)
            new_total = _unique(rows[node]["significator_houses"] + new_inherited + new_conjoined)
            if (new_inherited != rows[node]["node_inherited_houses"] or
                    new_conjoined != rows[node]["conjoined_planet_houses"] or
                    new_total != rows[node]["significator_houses"]):
                rows[node]["node_inherited_houses"] = new_inherited
                rows[node]["conjoined_planet_houses"] = new_conjoined
                rows[node]["significator_houses"] = new_total
                changed = True

        for planet, row in rows.items():
            if planet in ("Rahu", "Ketu"):
                continue
            if row["nakshatra_lord"] in ("Rahu", "Ketu"):
                node = row["nakshatra_lord"]
                inherited = list(rows[node]["significator_houses"])
                new_total = _unique(row["significator_houses"] + inherited)
                if inherited != row["node_inherited_houses"] or new_total != row["significator_houses"]:
                    row["node_inherited_houses"] = inherited
                    row["significator_houses"] = new_total
                    changed = True
        if not changed:
            break

    for row in rows.values():
        qualified = sorted(MARRIAGE_HOUSES.intersection(row["significator_houses"]))
        row["marriage_houses"] = qualified
        row["qualification"] = "Qualified" if qualified else "Not Qualified"
    return rows


def _parse_birth_datetime(kundli):
    b = kundli["birth_details"]
    tz = b.get("timezone", "UTC")
    return datetime.fromisoformat(f'{b["date"]}T{b["time"]}').replace(tzinfo=ZoneInfo(tz))


def _moon_nakshatra_position(kundli):
    moon = kundli["planets"]["Moon"]
    # Prefer longitude because it is the source of truth; fall back to degree + sign index.
    lon = float(moon.get("longitude", 0.0)) % 360.0
    idx = min(26, int(lon // NAK_SPAN))
    fraction_elapsed = (lon - idx * NAK_SPAN) / NAK_SPAN
    return idx, fraction_elapsed


def _parse_iso_datetime(value):
    return datetime.fromisoformat(value)


def _dasha_periods(kundli):
    """Compatibility view of the canonical Phase-1 Vimshottari calculator.

    Marriage/property timing consumes exactly the same 360-day Savana-year
    dasha dates that are exposed in the Phase-1 Kundli JSON.
    """
    data = calculate_vimshottari_dasha(kundli)
    md_rows = data["mahadasha"]
    ad_rows = data["antardasha"]
    pd_rows = data["pratyantardasha"]
    periods = []

    for md in md_rows:
        md_start = _parse_iso_datetime(md["start"])
        md_end = _parse_iso_datetime(md["end"])
        md_item = {
            "md": md["planet"],
            "md_start": md_start,
            "md_end": md_end,
            "md_years": float(md["duration"]),
            "pds": [],
        }
        md_ads = []
        for ad in ad_rows:
            ad_start = _parse_iso_datetime(ad["start"])
            ad_end = _parse_iso_datetime(ad["end"])
            if ad_start >= md_start and ad_end <= md_end:
                md_ads.append(ad)
        for ad in md_ads:
            ad_start = _parse_iso_datetime(ad["start"])
            ad_end = _parse_iso_datetime(ad["end"])
            p = {
                "md": md["planet"],
                "md_start": md_start,
                "md_end": md_end,
                "ad": ad["antardasha"],
                "ad_start": ad_start,
                "ad_end": ad_end,
                "md_years": float(md["duration"]),
                "ad_years": float(ad["duration"]),
                "pds": [],
            }
            for pd in pd_rows:
                pd_start = _parse_iso_datetime(pd["start"])
                pd_end = _parse_iso_datetime(pd["end"])
                if pd_start >= ad_start and pd_end <= ad_end:
                    p["pds"].append({
                        "lord": pd["pratyantardasha"],
                        "start": pd_start,
                        "end": pd_end,
                    })
            periods.append(p)
    return periods


def _iso(dt):
    return dt.isoformat(timespec="microseconds")


def _find_earliest_marriage_trigger(rows, dasha_periods):
    qualified = {p: bool(MARRIAGE_HOUSES.intersection(r["significator_houses"])) for p, r in rows.items()}
    for period in dasha_periods:
        if not qualified.get(period["md"], False) or not qualified.get(period["ad"], False):
            continue
        for pd in period["pds"]:
            if qualified.get(pd["lord"], False):
                return {
                    "md": period["md"], "md_start": _iso(period["md_start"]), "md_end": _iso(period["md_end"]),
                    "ad": period["ad"], "ad_start": _iso(period["ad_start"]), "ad_end": _iso(period["ad_end"]),
                    "pd": pd["lord"], "pd_start": _iso(pd["start"]), "pd_end": _iso(pd["end"]),
                    "reason": "Earliest chronological PD where MD, AD and PD each signify at least one of houses 2, 7 or 11.",
                }
    return None


def calculate_significators(kundli):
    rows = _resolve_significators(kundli)
    nav = _navamsha_info(kundli)
    nav_lord_qualified_houses = sorted(MARRIAGE_HOUSES.intersection(rows[nav["navamsha_7th_lord"]]["significator_houses"]))
    nav["qualified"] = bool(nav_lord_qualified_houses)
    nav["7th_lord_significator_houses"] = rows[nav["navamsha_7th_lord"]]["significator_houses"]
    nav["marriage_houses_found"] = nav_lord_qualified_houses

    dasha_available = "birth_details" in kundli and "Moon" in kundli.get("planets", {}) and "longitude" in kundli["planets"]["Moon"]
    dasha_periods = _dasha_periods(kundli) if dasha_available else []
    trigger = _find_earliest_marriage_trigger(rows, dasha_periods) if nav["qualified"] and dasha_available else None

    # Return only the dasha data useful for verification; the full 120-year nested list is large.
    dasha_gate = {
        "marriage_houses": sorted(MARRIAGE_HOUSES),
        "first_qualifying_window": trigger,
        "vimshottari_method": "Canonical Phase-1 Vimshottari Dasha using Moon Nakshatra starting lord, exact initial balance, AD/PD proportional 120-year cycle, and a 360-day Savana year.",
        "chronological_rule": "Stop at the first PD where MD, AD and PD each qualify for at least one of houses 2, 7, 11.",
        "available": dasha_available,
    }
    if trigger:
        dasha_gate["verification"] = {
            "MD": {"lord": trigger["md"], "qualified_houses": rows[trigger["md"]]["marriage_houses"]},
            "AD": {"lord": trigger["ad"], "qualified_houses": rows[trigger["ad"]]["marriage_houses"]},
            "PD": {"lord": trigger["pd"], "qualified_houses": rows[trigger["pd"]]["marriage_houses"]},
        }

    return {
        "method": "Deterministic Bhava-Navamsha + KP Marriage Algorithm",
        "marriage_houses": sorted(MARRIAGE_HOUSES),
        "navamsha_7th_lord_verification": nav,
        "significators": rows,
        "dasha_gate": dasha_gate,
        "final_exact_window": trigger,
    }

# ----------------------------- PROPERTY / HOUSE PURCHASE -----------------------------
PROPERTY_HOUSES = {2, 4, 11, 12}
PROPERTY_CONNECTION_PLANETS = {"Saturn", "Mars"}
RAHU_NAKSHATRAS = {"Ardra", "Swati", "Shatabhisha"}


def _navamsha_lagna_and_4th_lord(kundli):
    info = _navamsha_info(kundli)
    nav_lagna_index = info["navamsha_lagna_sign_index"]
    signs = list(SIGN_LORDS.keys())
    fourth_index = ((nav_lagna_index - 1 + 3) % 12) + 1
    fourth_sign = signs[fourth_index - 1]
    fourth_lord = SIGN_LORDS[fourth_sign][0]
    return {
        "navamsha_lagna_sign": info["navamsha_lagna_sign"],
        "navamsha_lagna_sign_index": nav_lagna_index,
        "navamsha_4th_house_sign": fourth_sign,
        "navamsha_4th_lord": fourth_lord,
    }


def _property_rule1(kundli, rows):
    nav = _navamsha_lagna_and_4th_lord(kundli)
    lord = nav["navamsha_4th_lord"]
    row = rows[lord]
    # Rule 1 uses the complete five-tier D1 significator hierarchy.
    # Levels 1-4 are inherited from the Navamsha 4th Lord's D1 significator row.
    # Level 5 is the set of D1 houses directly aspected by that planet.
    # We keep the five levels separate so the UI/JSON can show exactly why a
    # property house was found.
    levels = {
        "level_1_star_lord_placement": row["level_1_star_lord_placement"],
        "level_2_star_lord_ownership": row["level_2_star_lord_ownership"],
        "level_3_planet_placement": row["level_3_planet_placement"],
        "level_4_planet_ownership": row["level_4_planet_ownership"],
        "level_5_aspects": row["level_5_aspects"],
    }
    rule1_houses = _unique(sum(levels.values(), []))
    found_by_level = {
        name: sorted(PROPERTY_HOUSES.intersection(houses))
        for name, houses in levels.items()
    }
    found = sorted(set().union(*[set(v) for v in found_by_level.values()]))
    return {
        **nav,
        "navamsha_4th_lord": lord,
        "nakshatra_lord": row["nakshatra_lord"],
        "levels": levels,
        "navamsha_4th_lord_levels_1_to_5": {
            "level_1": levels["level_1_star_lord_placement"],
            "level_2": levels["level_2_star_lord_ownership"],
            "level_3": levels["level_3_planet_placement"],
            "level_4": levels["level_4_planet_ownership"],
            "level_5": levels["level_5_aspects"],
        },
        "property_houses_found_by_level": found_by_level,
        "considered_houses": rule1_houses,
        "property_houses_found": found,
        "passed": bool(found),
        "explanation": "Rule 1 passes when the Navamsha 4th Lord, traced in the Janam Kundali, signifies at least one of houses 2, 4, 11 or 12 through any of Levels 1-5.",
    }


def _direct_aspect_pair(planet_a, planet_b, planets):
    a_house = int(planets[planet_a]["house"])
    b_house = int(planets[planet_b]["house"])
    return b_house in _aspect_houses(planet_a, a_house), a_house in _aspect_houses(planet_b, b_house)


def _property_rule2(kundli):
    planets = kundli["planets"]
    sign_to_houses = _build_indexes(kundli)[1]
    nav = _navamsha_lagna_and_4th_lord(kundli)
    nav4 = nav["navamsha_4th_lord"]
    lagna4_sign = kundli["houses"]["4"]["sign"]
    lagna4_lord = SIGN_LORDS[lagna4_sign][0]
    subjects = [
        ("Navamsha 4th Lord", nav4, "planet"),
        ("Lagna 4th Lord", lagna4_lord, "planet"),
        ("4th House", None, "house"),
    ]
    checks = []
    any_connection = False
    mars_signs = {"Aries", "Scorpio"}
    saturn_signs = {"Capricorn", "Aquarius"}

    for subject_name, subject_planet, subject_type in subjects:
        for target in ("Saturn", "Mars"):
            evidence = []
            if subject_type == "planet":
                sp = planets[subject_planet]
                # Subject is placed in target-owned rashi.
                target_signs = saturn_signs if target == "Saturn" else mars_signs
                if sp["sign"] in target_signs:
                    evidence.append({"type": "rashi", "detail": f"{subject_planet} is in {sp['sign']}, a {target}-owned sign."})
                # Subject is in a Nakshatra ruled by target.
                if sp.get("nakshatra_lord") == target:
                    evidence.append({"type": "nakshatra", "detail": f"{subject_planet} is in {target}'s Nakshatra ({sp.get('nakshatra')})."})
                # Target is in subject's Nakshatra (mutual star connection).
                tp = planets[target]
                if tp.get("nakshatra_lord") == subject_planet:
                    evidence.append({"type": "nakshatra", "detail": f"{target} is in {subject_planet}'s Nakshatra ({tp.get('nakshatra')})."})
                # Direct Janma Kundali Drishti, both directions.
                a_to_b, b_to_a = _direct_aspect_pair(subject_planet, target, planets)
                if a_to_b:
                    evidence.append({"type": "drishti", "detail": f"{subject_planet} directly aspects {target} in the Janam Kundali."})
                if b_to_a:
                    evidence.append({"type": "drishti", "detail": f"{target} directly aspects {subject_planet} in the Janam Kundali."})
                # Parivartana / mutual exchange: each planet occupies the other's sign.
                subject_sign_lord = SIGN_LORDS.get(sp["sign"], [None])[0]
                target_sign = tp["sign"]
                target_sign_lord = SIGN_LORDS.get(target_sign, [None])[0]
                if subject_sign_lord == target and target_sign_lord == subject_planet:
                    evidence.append({"type": "parivartana", "detail": f"{subject_planet} and {target} mutually exchange signs."})
            else:
                # The 4th house itself is connected if Saturn/Mars aspects house 4,
                # or if the 4th house sign is one of that planet's own signs.
                house4_sign = kundli["houses"]["4"]["sign"]
                target_signs = saturn_signs if target == "Saturn" else mars_signs
                if house4_sign in target_signs:
                    evidence.append({"type": "rashi", "detail": f"4th house is {house4_sign}, a {target}-owned sign."})
                tp = planets[target]
                if 4 in _aspect_houses(target, int(tp["house"])):
                    evidence.append({"type": "drishti", "detail": f"{target} directly aspects the 4th house in the Janam Kundali."})
                # 4th house's sign lord in target's sign gives an exchange-style house connection.
                h4_lord = SIGN_LORDS[house4_sign][0]
                if h4_lord in planets:
                    hp = planets[h4_lord]
                    if SIGN_LORDS.get(hp["sign"], [None])[0] == target and SIGN_LORDS.get(tp["sign"], [None])[0] == h4_lord:
                        evidence.append({"type": "parivartana", "detail": f"4th-house lord {h4_lord} and {target} are in mutual exchange."})
            if evidence:
                any_connection = True
            checks.append({"subject": subject_name, "subject_planet": subject_planet, "target": target, "connections": evidence, "connected": bool(evidence)})

    return {
        "passed": any_connection,
        "allowed_connections": ["Nakshatra placement", "Janam Kundali direct Drishti", "Rashi placement", "Parivartana / mutual exchange"],
        "navamsha_4th_lord": nav4,
        "lagna_4th_house_sign": lagna4_sign,
        "lagna_4th_lord": lagna4_lord,
        "checks": checks,
        "explanation": "Rule 2 passes if the Navamsha 4th Lord, Lagna 4th Lord, or the 4th house has at least one allowed Saturn/Mars connection.",
    }


def _property_rahu_check(kundli):
    planets = kundli["planets"]
    nav = _navamsha_lagna_and_4th_lord(kundli)
    nav4 = nav["navamsha_4th_lord"]
    p = planets[nav4]
    reasons = []
    if int(planets["Rahu"]["house"]) == 4:
        reasons.append("Rahu is in the 4th house of the Janam Kundali.")
    if p.get("nakshatra") in RAHU_NAKSHATRAS or p.get("nakshatra_lord") == "Rahu":
        reasons.append(f"Navamsha 4th Lord {nav4} is in Rahu's Nakshatra ({p.get('nakshatra')}).")
    if int(planets[nav4]["house"]) == int(planets["Rahu"]["house"]):
        reasons.append(f"Navamsha 4th Lord {nav4} is conjunct Rahu in house {p['house']}.")
    return {
        "affliction_present": bool(reasons),
        "reasons": reasons,
        "navamsha_4th_lord": nav4,
        "rahu_nakshatras": sorted(RAHU_NAKSHATRAS),
        "property_quality_conclusion": "Fresh/new construction strictly advised under this rule." if reasons else "No Rahu affliction under the specified rule.",
    }


def _property_dasha_analysis(kundli, rows):
    periods = _dasha_periods(kundli)
    qualifying_planets = {}
    for planet, row in rows.items():
        houses = set(row["significator_houses"])
        q = sorted(PROPERTY_HOUSES.intersection(houses))
        if q:
            qualifying_planets[planet] = q
    # Also include house rulers explicitly, even if the engine's significator set does not.
    signs = list(SIGN_LORDS.keys())
    house_rulers = {}
    for h in sorted(PROPERTY_HOUSES):
        sign = kundli["houses"][str(h)]["sign"]
        lord = SIGN_LORDS[sign][0]
        house_rulers[str(h)] = lord
        qualifying_planets.setdefault(lord, sorted(set(qualifying_planets.get(lord, []) + [h])))

    candidates = []
    for p in periods:
        md_q = sorted(PROPERTY_HOUSES.intersection(rows[p["md"]]["significator_houses"]))
        ad_q = sorted(PROPERTY_HOUSES.intersection(rows[p["ad"]]["significator_houses"]))
        for pd in p["pds"]:
            pd_q = sorted(PROPERTY_HOUSES.intersection(rows[pd["lord"]]["significator_houses"]))
            if md_q and ad_q and pd_q:
                candidates.append({
                    "md": p["md"], "md_start": _iso(p["md_start"]), "md_end": _iso(p["md_end"]), "md_houses": md_q,
                    "ad": p["ad"], "ad_start": _iso(p["ad_start"]), "ad_end": _iso(p["ad_end"]), "ad_houses": ad_q,
                    "pd": pd["lord"], "pd_start": _iso(pd["start"]), "pd_end": _iso(pd["end"]), "pd_houses": pd_q,
                    "qualifying_levels": [x for x, ok in (("MD", bool(md_q)), ("AD", bool(ad_q)), ("PD", bool(pd_q))) if ok],
                })
    return {
        "property_houses": sorted(PROPERTY_HOUSES),
        "house_rulers": house_rulers,
        "qualifying_planets": qualifying_planets,
        "method": "Property acquisition candidates require MD, AD and PD to all simultaneously signify or rule at least one of houses 2, 4, 11 or 12. Dates come from the canonical Phase-1 Vimshottari calculator using a 360-day Savana year; no outside timing rule is applied.",
        "candidates": candidates,
        "earliest_candidate": candidates[0] if candidates else None,
    }


def calculate_property_analysis(kundli):
    rows = _resolve_significators(kundli)
    rule1 = _property_rule1(kundli, rows)
    rule2 = _property_rule2(kundli)
    rahu = _property_rahu_check(kundli)
    dasha = _property_dasha_analysis(kundli, rows)
    promise = bool(rule1["passed"] and rule2["passed"])
    return {
        "method": "Deterministic House Purchase Astrology Algorithm",
        "property_houses": sorted(PROPERTY_HOUSES),
        "rule_1_navamsa_4th_lord_verification": rule1,
        "rule_2_saturn_mars_connection_verification": rule2,
        "rahu_influence_check": rahu,
        "final_promise_verdict": {
            "khud_ka_makaan_hoga": "Yes" if promise else "No",
            "passed": promise,
            "basis": "Rules 1 AND 2 must both pass; Rule 3 affects property quality and Rule 4 affects timing."},
        "timing_of_event": dasha,
        "significators": rows,
    }
