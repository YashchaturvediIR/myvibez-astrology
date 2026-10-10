"""
Deterministic Vimshottari Dasha calculator.

The implementation follows the exact formula supplied for this project:
- Moon's sidereal longitude determines Janma Nakshatra and starting lord.
- Initial Mahadasha balance uses the remaining Nakshatra arc / 800 arcminutes.
- Antardasha = MD duration * AD lord years / 120.
- Pratyantardasha = AD duration * PD lord years / 120.
- This module uses a 360-day Savana year consistently for all date conversion.

Calculations are kept as Decimal values until the final conversion to Python
calendar datetimes, whose maximum resolution is one microsecond.
"""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from datetime import timezone

from app.services.nakshatra import NAKSHATRAS

DASHA_SEQUENCE = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"
]
DASHA_YEARS = {
    "Ketu": Decimal("7"), "Venus": Decimal("20"), "Sun": Decimal("6"),
    "Moon": Decimal("10"), "Mars": Decimal("7"), "Rahu": Decimal("18"),
    "Jupiter": Decimal("16"), "Saturn": Decimal("19"), "Mercury": Decimal("17"),
}
TOTAL_DASHA_YEARS = Decimal("120")
SAVANA_DAYS_PER_YEAR = Decimal("360")
NAKSHATRA_ARCMINUTES = Decimal("800")
PADA_ARCMINUTES = Decimal("200")


def _birth_datetime(kundli):
    b = kundli["birth_details"]
    return datetime.fromisoformat(f'{b["date"]}T{b["time"]}').replace(
        tzinfo=ZoneInfo(b["timezone"])
    )


def _add_savana_years(dt, years: Decimal):
    """Add exact Savana elapsed days in UTC, then return in the birth timezone."""
    return (dt.astimezone(timezone.utc) + _decimal_days_to_timedelta(years * SAVANA_DAYS_PER_YEAR)).astimezone(dt.tzinfo)


def _decimal_days_to_timedelta(days: Decimal) -> timedelta:
    """Convert an exact Decimal day value to datetime's final microsecond resolution."""
    micros = (days * Decimal("86400000000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return timedelta(microseconds=int(micros))



def _iso(dt):
    # Six decimal places preserve Python datetime's full final precision.
    return dt.isoformat(timespec="microseconds")


def _moon_details(kundli):
    moon = kundli["planets"]["Moon"]
    lon = Decimal(str(float(moon["longitude"]))) % Decimal("360")
    total_arcminutes = lon * Decimal("60")
    nak_idx = min(26, int(total_arcminutes // NAKSHATRA_ARCMINUTES))
    completed = total_arcminutes - Decimal(nak_idx) * NAKSHATRA_ARCMINUTES
    remaining = NAKSHATRA_ARCMINUTES - completed
    pada = min(4, int(completed // PADA_ARCMINUTES) + 1)
    nak_name, nak_lord = NAKSHATRAS[nak_idx]
    elapsed_fraction = completed / NAKSHATRA_ARCMINUTES
    remaining_fraction = remaining / NAKSHATRA_ARCMINUTES
    first_years = DASHA_YEARS[nak_lord]
    balance_years = first_years * remaining_fraction

    return {
        "longitude": lon,
        "longitude_degrees": lon,
        "nakshatra_index": nak_idx + 1,
        "nakshatra": nak_name,
        "nakshatra_lord": nak_lord,
        "pada": pada,
        "nakshatra_span_arcminutes": NAKSHATRA_ARCMINUTES,
        "completed_arcminutes": completed,
        "remaining_arcminutes": remaining,
        "completed_fraction": elapsed_fraction,
        "remaining_fraction": remaining_fraction,
        "first_mahadasha_years": first_years,
        "initial_balance_years": balance_years,
    }


def _fmt_decimal(value: Decimal, places=12):
    # Formatting is presentation only; it never feeds another calculation.
    return f"{value:.{places}f}".rstrip("0").rstrip(".")


def _period_dict(lord, start, end, duration_years):
    return {
        "lord": lord,
        "start": _iso(start),
        "end": _iso(end),
        "duration_years": _fmt_decimal(duration_years),
        "duration_days": _fmt_decimal(duration_years * SAVANA_DAYS_PER_YEAR),
    }


def calculate_vimshottari_dasha(kundli):
    birth = _birth_datetime(kundli)
    moon = _moon_details(kundli)
    first_lord = moon["nakshatra_lord"]
    first_balance = moon["initial_balance_years"]
    first_index = DASHA_SEQUENCE.index(first_lord)

    # Generate enough Mahadashas to cover exactly 120 Savana years from birth.
    # The final MD is truncated at birth + 120 Savana years so the displayed
    # birth-horizon is exact, while the verification below separately confirms
    # that a complete Vimshottari cycle is 120 years.
    horizon = _add_savana_years(birth, TOTAL_DASHA_YEARS)
    md_items = []
    cursor = birth
    md_counter = 0
    while cursor < horizon:
        lord = DASHA_SEQUENCE[(first_index + md_counter) % 9]
        duration_years = first_balance if md_counter == 0 else DASHA_YEARS[lord]
        nominal_end = _add_savana_years(cursor, duration_years)
        end = min(nominal_end, horizon)
        actual_days = Decimal(str((end - cursor).total_seconds())) / Decimal("86400")
        actual_years = actual_days / SAVANA_DAYS_PER_YEAR
        md_items.append({
            "index": md_counter,
            "lord": lord,
            "start_dt": cursor,
            "end_dt": end,
            "duration_years": actual_years,
            "nominal_duration_years": duration_years,
            "truncated_at_120_year_horizon": nominal_end > horizon,
        })
        cursor = end
        md_counter += 1

    # Build AD and PD using the same Decimal duration hierarchy.
    mahadashas = []
    antardashas = []
    pratyantardashas = []

    for md in md_items:
        md_lord = md["lord"]
        md_duration = md["duration_years"]
        md_index = DASHA_SEQUENCE.index(md_lord)
        ad_cursor = md["start_dt"]
        md_ad_items = []

        for j in range(9):
            ad_lord = DASHA_SEQUENCE[(md_index + j) % 9]
            ad_duration = md_duration * DASHA_YEARS[ad_lord] / TOTAL_DASHA_YEARS
            nominal_ad_end = _add_savana_years(ad_cursor, ad_duration)
            ad_end = min(nominal_ad_end, md["end_dt"])
            actual_ad_days = Decimal(str((ad_end - ad_cursor).total_seconds())) / Decimal("86400")
            actual_ad_years = actual_ad_days / SAVANA_DAYS_PER_YEAR
            ad = {
                "md_index": md["index"],
                "md": md_lord,
                "ad_index": j,
                "lord": ad_lord,
                "start_dt": ad_cursor,
                "end_dt": ad_end,
                "duration_years": actual_ad_years,
                "nominal_duration_years": ad_duration,
                "truncated": nominal_ad_end > md["end_dt"],
            }
            md_ad_items.append(ad)
            antardashas.append(ad)
            ad_cursor = ad_end
            if ad_cursor >= md["end_dt"]:
                break

        # The AD loop must partition the MD. Build PDs for each AD.
        for ad in md_ad_items:
            ad_lord = ad["lord"]
            ad_duration = ad["duration_years"]
            ad_index = DASHA_SEQUENCE.index(ad_lord)
            pd_cursor = ad["start_dt"]
            for k in range(9):
                pd_lord = DASHA_SEQUENCE[(ad_index + k) % 9]
                pd_duration = ad_duration * DASHA_YEARS[pd_lord] / TOTAL_DASHA_YEARS
                nominal_pd_end = _add_savana_years(pd_cursor, pd_duration)
                pd_end = min(nominal_pd_end, ad["end_dt"])
                actual_pd_days = Decimal(str((pd_end - pd_cursor).total_seconds())) / Decimal("86400")
                actual_pd_years = actual_pd_days / SAVANA_DAYS_PER_YEAR
                pratyantardashas.append({
                    "md_index": md["index"],
                    "ad_index": ad["ad_index"],
                    "md": md_lord,
                    "ad": ad_lord,
                    "lord": pd_lord,
                    "start_dt": pd_cursor,
                    "end_dt": pd_end,
                    "duration_years": actual_pd_years,
                    "nominal_duration_years": pd_duration,
                    "truncated": nominal_pd_end > ad["end_dt"],
                })
                pd_cursor = pd_end
                if pd_cursor >= ad["end_dt"]:
                    break

        mahadashas.append(md)

    # Serialize tables. Include formulas so every displayed duration is auditable.
    md_table = []
    for md in mahadashas:
        md_table.append({
            "planet": md["lord"],
            "start": _iso(md["start_dt"]),
            "end": _iso(md["end_dt"]),
            "duration": _fmt_decimal(md["duration_years"]),
            "duration_days": _fmt_decimal(md["duration_years"] * SAVANA_DAYS_PER_YEAR),
            "truncated_at_120_year_horizon": md["truncated_at_120_year_horizon"],
        })

    ad_table = []
    for ad in antardashas:
        ad_table.append({
            "mahadasha": ad["md"],
            "antardasha": ad["lord"],
            "start": _iso(ad["start_dt"]),
            "end": _iso(ad["end_dt"]),
            "duration": _fmt_decimal(ad["duration_years"]),
            "duration_days": _fmt_decimal(ad["duration_years"] * SAVANA_DAYS_PER_YEAR),
        })

    pd_table = []
    for pd in pratyantardashas:
        pd_table.append({
            "mahadasha": pd["md"],
            "antardasha": pd["ad"],
            "pratyantardasha": pd["lord"],
            "start": _iso(pd["start_dt"]),
            "end": _iso(pd["end_dt"]),
            "duration": _fmt_decimal(pd["duration_years"]),
            "duration_days": _fmt_decimal(pd["duration_years"] * SAVANA_DAYS_PER_YEAR),
        })

    # Verification is performed from generated boundaries, not just formula text.
    md_sum = sum((x["duration_years"] for x in mahadashas), Decimal("0"))
    ad_checks = []
    for md in mahadashas:
        ads = [x for x in antardashas if x["md_index"] == md["index"]]
        ad_sum = sum((x["duration_years"] for x in ads), Decimal("0"))
        ad_checks.append({
            "mahadasha_index": md["index"],
            "mahadasha": md["lord"],
            "sum_antardasha_years": _fmt_decimal(ad_sum),
            "mahadasha_years": _fmt_decimal(md["duration_years"]),
            "matches": abs(ad_sum - md["duration_years"]) < Decimal("0.000001"),
        })

    pd_checks = []
    for ad in antardashas:
        pds = [x for x in pratyantardashas if x["md_index"] == ad["md_index"] and x["ad_index"] == ad["ad_index"]]
        pd_sum = sum((x["duration_years"] for x in pds), Decimal("0"))
        pd_checks.append({
            "mahadasha": ad["md"],
            "antardasha": ad["lord"],
            "sum_pratyantardasha_years": _fmt_decimal(pd_sum),
            "antardasha_years": _fmt_decimal(ad["duration_years"]),
            "matches": abs(pd_sum - ad["duration_years"]) < Decimal("0.000001"),
        })

    md_no_gaps = all(mahadashas[i]["end_dt"] == mahadashas[i + 1]["start_dt"] for i in range(len(mahadashas) - 1))
    ad_no_gaps = all(
        antardashas[i]["end_dt"] == antardashas[i + 1]["start_dt"]
        for i in range(len(antardashas) - 1)
        if antardashas[i]["md_index"] == antardashas[i + 1]["md_index"]
    )
    pd_no_gaps = all(
        pratyantardashas[i]["end_dt"] == pratyantardashas[i + 1]["start_dt"]
        for i in range(len(pratyantardashas) - 1)
        if (pratyantardashas[i]["md_index"], pratyantardashas[i]["ad_index"]) == (pratyantardashas[i + 1]["md_index"], pratyantardashas[i + 1]["ad_index"])
    )

    # Full 9-planet cycle verification, independent of birth balance.
    full_cycle_years = sum(DASHA_YEARS.values(), Decimal("0"))

    return {
        "system": "Vimshottari Dasha",
        "year_convention": "360-day Savana year",
        "savana_days_per_year": 360,
        "total_cycle_years": 120,
        "sequence": DASHA_SEQUENCE,
        "planetary_mahadasha_years": {k: _fmt_decimal(v) for k, v in DASHA_YEARS.items()},
        "birth_datetime": _iso(birth),
        "moon_calculation": {
            "sidereal_longitude": _fmt_decimal(moon["longitude"], 12),
            "sidereal_longitude_degrees": _fmt_decimal(moon["longitude"], 12),
            "janma_nakshatra": moon["nakshatra"],
            "nakshatra_pada": moon["pada"],
            "nakshatra_lord": moon["nakshatra_lord"],
            "nakshatra_span_arcminutes": 800,
            "completed_arcminutes": _fmt_decimal(moon["completed_arcminutes"], 12),
            "remaining_arcminutes": _fmt_decimal(moon["remaining_arcminutes"], 12),
            "completed_fraction": _fmt_decimal(moon["completed_fraction"], 15),
            "remaining_fraction": _fmt_decimal(moon["remaining_fraction"], 15),
            "first_mahadasha_years": _fmt_decimal(moon["first_mahadasha_years"], 12),
            "initial_balance_years": _fmt_decimal(moon["initial_balance_years"], 15),
            "initial_balance_days": _fmt_decimal(moon["initial_balance_years"] * SAVANA_DAYS_PER_YEAR, 12),
        },
        "formulas": {
            "initial_balance": "Remaining MD years = Planet MD years × Remaining Nakshatra arcminutes / 800",
            "antardasha": "AD duration = MD duration × AD planet years / 120",
            "pratyantardasha": "PD duration = AD duration × PD planet years / 120",
            "date_conversion": "Calendar duration = calculated Vimshottari years × 360 Savana days/year",
            "rounding_policy": "No intermediate duration rounding; only final datetime conversion is limited to Python datetime microsecond precision.",
        },
        "numerical_calculation": {
            "initial_balance_expression": (
                f"{_fmt_decimal(moon['first_mahadasha_years'], 12)} × "
                f"{_fmt_decimal(moon['remaining_arcminutes'], 12)} / 800 = "
                f"{_fmt_decimal(moon['initial_balance_years'], 15)} years"
            ),
            "initial_balance_days_expression": (
                f"{_fmt_decimal(moon['initial_balance_years'], 15)} × 360 = "
                f"{_fmt_decimal(moon['initial_balance_years'] * SAVANA_DAYS_PER_YEAR, 12)} days"
            ),
        },
        "mahadasha": md_table,
        "antardasha": ad_table,
        "pratyantardasha": pd_table,
        "verification": {
            "full_planetary_cycle_years": _fmt_decimal(full_cycle_years),
            "full_planetary_cycle_equals_120": full_cycle_years == TOTAL_DASHA_YEARS,
            "birth_to_120_savana_years": _fmt_decimal(md_sum),
            "birth_horizon_equals_120": abs(md_sum - TOTAL_DASHA_YEARS) < Decimal("0.000001"),
            "all_antardashas_equal_parent_mahadasha": all(x["matches"] for x in ad_checks),
            "all_pratyantardashas_equal_parent_antardasha": all(x["matches"] for x in pd_checks),
            "no_mahadasha_gaps_or_overlaps": md_no_gaps,
            "no_antardasha_gaps_or_overlaps": ad_no_gaps,
            "no_pratyantardasha_gaps_or_overlaps": pd_no_gaps,
            "initial_balance_formula_verified": moon["initial_balance_years"] == moon["first_mahadasha_years"] * moon["remaining_arcminutes"] / NAKSHATRA_ARCMINUTES,
            "antardasha_checks": ad_checks,
            "pratyantardasha_checks": pd_checks,
        },
    }
