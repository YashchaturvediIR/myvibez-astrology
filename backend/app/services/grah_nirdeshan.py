"""Exact D-1 Grah Nirdeshan (signified bhavas) table.

Rules intentionally limited to:
1) D-1 whole-sign Lagna chart for planet house placement and Parashari lordships.
2) Phase-1 planetary coordinate table's nakshatra_lord for Star Lord.
3) For Rahu/Ketu, add the D-1 rashi lord's occupied/owned houses and planets
   conjoined in the same D-1 house.

No Bhava Chalit, cusp degrees, cusp sub-lords, or aspect-based significations
are used here.
"""

from app.services.significator import SIGN_LORDS, OWN_SIGNS

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def _unique_sorted(values):
    return sorted({int(v) for v in values if v is not None})


def _sign_to_houses(kundli):
    result = {sign: [] for sign in SIGN_LORDS}
    for house_num, house_data in kundli["houses"].items():
        result.setdefault(house_data["sign"], []).append(int(house_num))
    return result


def _owned_houses(planet, sign_to_houses):
    houses = []
    for sign in OWN_SIGNS.get(planet, []):
        houses.extend(sign_to_houses.get(sign, []))
    return houses


def _planet_house(planets, planet):
    return int(planets[planet]["house"])


def calculate_grah_nirdeshan(kundli):
    if "planets" not in kundli or "houses" not in kundli:
        raise ValueError("Invalid Kundli JSON: planets and houses are required.")

    planets = kundli["planets"]
    sign_to_houses = _sign_to_houses(kundli)
    rows = []

    for planet in PLANET_ORDER:
        if planet not in planets:
            continue

        p = planets[planet]
        star_lord = p.get("nakshatra_lord")
        if not star_lord:
            raise ValueError(f"Nakshatra Lord (न) is missing for {planet}.")
        if star_lord not in planets:
            raise ValueError(f"Nakshatra Lord {star_lord} for {planet} is not present in planetary data.")

        # Step 2: Star Lord's occupied + owned houses in D-1.
        star_placement = [_planet_house(planets, star_lord)]
        star_ownership = _owned_houses(star_lord, sign_to_houses)

        # Step 3: Planet's occupied + owned houses in D-1.
        planet_placement = [_planet_house(planets, planet)]
        planet_ownership = _owned_houses(planet, sign_to_houses)

        houses = star_placement + star_ownership + planet_placement + planet_ownership

        node_details = None
        if planet in ("Rahu", "Ketu"):
            # Step 4: dispositor (Lord of the Rashi occupied by the node).
            sign = p["sign"]
            rashi_lord = SIGN_LORDS[sign][0]
            dispositor_placement = [_planet_house(planets, rashi_lord)]
            dispositor_ownership = _owned_houses(rashi_lord, sign_to_houses)
            houses.extend(dispositor_placement)
            houses.extend(dispositor_ownership)

            # The supplied rule says "closely conjoined" but gives no degree
            # threshold. In this D-1 whole-sign model, conjunction is therefore
            # represented by planets sharing the node's D-1 house. No cusp data
            # or Bhava Chalit data is introduced.
            node_house = _planet_house(planets, planet)
            conjoined = [other for other in PLANET_ORDER if other != planet
                          and other in planets and _planet_house(planets, other) == node_house]
            conjoined_houses = []
            for other in conjoined:
                conjoined_houses.extend([_planet_house(planets, other)])
                conjoined_houses.extend(_owned_houses(other, sign_to_houses))
            houses.extend(conjoined_houses)

            node_details = {
                "rashi": sign,
                "rashi_lord": rashi_lord,
                "rashi_lord_placement": _unique_sorted(dispositor_placement),
                "rashi_lord_ownership": _unique_sorted(dispositor_ownership),
                "conjoined_planets_same_d1_house": conjoined,
            }

        rows.append({
            "planet": planet,
            "nakshatra_lord": star_lord,
            "star_lord_placement": _unique_sorted(star_placement),
            "star_lord_ownership": _unique_sorted(star_ownership),
            "planet_placement": _unique_sorted(planet_placement),
            "planet_ownership": _unique_sorted(planet_ownership),
            "node_special_rule": node_details,
            "signified_bhavas": _unique_sorted(houses),
        })

    return {
        "table_title": "ग्रह निर्देशन",
        "method": "D-1 Parashari whole-sign house placement + D-1 house lordship + planetary table Nakshatra Lord (न); node rashi-lord/conjunction rule for Rahu/Ketu.",
        "excluded": ["Bhava Chalit", "Cusp degrees", "Cusp Sub-lords"],
        "rows": rows,
        "table": {row["planet"]: row["signified_bhavas"] for row in rows},
    }
