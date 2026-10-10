# Personal Kundli — Phase 2.2

Deterministic Vedic/KP-style Kundli + Vimshottari Dasha + Marriage + House Purchase analysis.

## Phase 1 — Vimshottari Dasha

The Kundli calculation now includes a complete deterministic Vimshottari Dasha calculation directly in the Phase-1 `/api/kundli` response. It uses the exact project formula supplied by the owner:

1. Moon's exact sidereal longitude determines Janma Nakshatra, Pada and Nakshatra Lord.
2. Nakshatra span is exactly 800 arcminutes (13°20′).
3. Initial Mahadasha balance = `planet MD years × remaining Nakshatra arcminutes / 800`.
4. Antardasha = `MD duration × AD planet years / 120`.
5. Pratyantardasha = `AD duration × PD planet years / 120`.
6. Date conversion uses a **360-day Savana year**, consistently.
7. Intermediate duration values are not rounded; only the final calendar datetime is limited to Python datetime microsecond precision.

The response contains: 
- Moon calculation with completed/remaining Nakshatra arcminutes and the exact initial balance calculation.
- Mahadasha table.
- Antardasha table.
- Pratyantardasha table.
- Formula strings and numerical expressions.
- Mathematical verification for the 120-year planetary cycle, AD/PD totals, and gaps/overlaps.

The displayed 120-year birth horizon starts at birth and ends exactly 120 Savana years later. If the final Mahadasha crosses that horizon, its displayed row is truncated at the horizon; the full nine-planet Vimshottari cycle is separately verified as exactly 120 years.

## Marriage timing

Marriage timing consumes the same canonical Phase-1 Vimshottari periods, so the marriage window cannot use a different dasha convention from the Kundli. The existing marriage gate requires MD + AD + PD to each signify at least one of houses 2, 7 or 11.

## Property Rule 1 — corrected

Rule 1 traces the **Navamsha (D-9) 4th Lord in the Janam Kundali (D-1)** through the complete five-tier hierarchy:

1. D1 house occupied by the Navamsha 4th Lord's Nakshatra/Star Lord.
2. D1 houses owned by that Star Lord.
3. D1 house occupied by the Navamsha 4th Lord.
4. D1 houses owned by the Navamsha 4th Lord (both signs).
5. D1 houses directly aspected by the Navamsha 4th Lord using the configured aspect rules.

Rule 1 passes if any level contains house 2, 4, 11 or 12.

## Property Rule 4 timing

Property acquisition candidates now require **MD, AD and PD all simultaneously** to signify/rule at least one of houses 2, 4, 11 or 12. These dates come from the same Phase-1 360-day Savana Vimshottari calculation.

## Run

```cmd
cd /d D:\Astro\marriage\backend
venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
uvicorn app.main:app --reload
```

In another terminal:

```cmd
cd /d D:\Astro\astro\frontend
python -m http.server 5500
```

Open `http://127.0.0.1:5500` (the frontend automatically targets FastAPI at `127.0.0.1:8000` locally).

Swagger: `http://127.0.0.1:8000/docs`

## Childbirth Astrology
The app now includes a deterministic `/api/childbirth-analysis` engine implementing the supplied rules:
- D9 5th Lord traced through the D1 five-level significator hierarchy; childbirth promise checks houses 2/5/11.
- Delivery nature checks whether the D9 5th Lord is a D1 house-8 significator.
- Rahu check: Rahu in D1 house 4, D9 5th Lord in Ardra/Swati/Shatabhisha, or conjunction with Rahu.
- Timing checks MD, AD and PD, each signifying at least one of houses 2/5/11, using the canonical Phase-1 360-day Savana Vimshottari dates.

## Phase 5 — Forward-Only Multi-Event Timing

The app can now find the earliest future Dasha window for Childbirth, Marriage, Property / Real Estate, Job / Promotion, Foreign Travel / Relocation, and Litigation / Disease.

Rules: the query timestamp T0 is supplied by the browser at runtime; periods with end <= T0 are excluded; the Navamsha primary-house lord must first promise at least one target house through Grah Nirdeshan; MD must signify at least one target house; and the union of MD + AD + PD Grah Nirdeshan houses must cover the complete target set. The scan stops at the first matching PD. If no future match exists, the engine returns `NO MATCHING DASHA FOUND`.

API endpoints:
- `POST /api/predictive-timing` with `{ "topic": "marriage", "kundli": {...}, "query_datetime": "..." }`
- `POST /api/upcoming-events` with `{ "kundli": {...}, "query_datetime": "..." }`

Target mappings:
- Childbirth: 2, 5, 11 (primary 5)
- Marriage: 2, 7, 11 (primary 7)
- Property / Real Estate: 4, 11, 12 (primary 4)
- Job / Promotion: 2, 6, 10, 11 (primary 10)
- Foreign Travel / Relocation: 3, 9, 12 (primary 9)
- Litigation / Disease: 6, 8, 12 (primary 8)


## Persistent Kundli Records + ManyChat Intake (new)

### What is included
- PostgreSQL-ready storage using `DATABASE_URL` (SQLite is used only as a local development fallback).
- Automatic record creation after manual Kundli calculation in the web UI.
- Searchable Saved Kundlis table and one-click record restore.
- Records store the full Kundli JSON and snapshots of Grah Nirdeshan, significators, property, childbirth and upcoming-event calculations.
- `POST /api/manychat/intake` for ManyChat External Request intake.
- Admin-key protection for saved-record endpoints and separate ManyChat webhook-token protection.

### Required Render environment variables
Create a Render PostgreSQL database and set the database's **Internal Database URL** as:
- `DATABASE_URL`

Set these secrets in the web service environment:
- `BRAHMVAKYA_ADMIN_KEY`: a long, random secret used by the private Saved Kundlis dashboard.
- `MANYCHAT_WEBHOOK_TOKEN`: a different long, random secret configured as the `X-ManyChat-Token` header in ManyChat.
- `BRAHMVAKYA_PUBLIC_BASE_URL`: your public site URL, e.g. `https://myvibez-astrology.onrender.com` (used to generate the report link returned to ManyChat).
- `GEOAPIFY_API_KEY`: Geoapify geocoding key, required if ManyChat sends only a birthplace name instead of coordinates/timezone.

Do not commit either secret to GitHub. When `DATABASE_URL` is missing, the app uses a local SQLite file; local SQLite is not a durable production database on ephemeral hosting.

### ManyChat endpoint contract
POST `https://YOUR-DOMAIN/api/manychat/intake`
Header: `X-ManyChat-Token: YOUR_MANYCHAT_WEBHOOK_TOKEN`
Header: `Content-Type: application/json`

Example JSON:
```json
{
  "name": "Customer name",
  "instagram_username": "@customer",
  "request_type": "kundli",
  "dob": "2001-08-15",
  "birth_time": "10:35:00",
  "birth_place": "Jaipur, Rajasthan, India"

}
```

ManyChat can send just the birthplace text. The backend resolves it through Geoapify using `GEOAPIFY_API_KEY`, then determines the IANA timezone with timezonefinder. Do not use the public Nominatim service for this high-volume intake flow.

The response includes `record_id`, `reply`, `report_url`, and `kundli_summary`. Map the ManyChat External Request response field `reply` into a Dynamic Block / message text to send the response, or map `report_url` into a message with a link button. The tokenized PDF endpoint returns the saved planetary positions, Dasha tables and stored analysis snapshots. The full data remains stored in PostgreSQL.

### Local development
Install new requirements:
```bash
pip install -r backend/requirements.txt
```
Set `BRAHMVAKYA_ADMIN_KEY` and `MANYCHAT_WEBHOOK_TOKEN` in the local environment before using record APIs. The database tables are created on app startup.
