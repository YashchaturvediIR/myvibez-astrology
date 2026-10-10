from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from fastapi import Header
import os
import hmac
import requests
import secrets
from sqlalchemy import or_, desc
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from app.services.persistence import SessionLocal, KundliRecord
from app.services.kundli_calculator import calculate_kundli
from app.models.kundli import KundliRequest, BirthDetails, Settings
from app.services.significator import calculate_significators, calculate_property_analysis
from app.services.childbirth import calculate_childbirth_analysis
from app.services.grah_nirdeshan import calculate_grah_nirdeshan
from app.services.predictive_timing import calculate_all_upcoming_events

router = APIRouter()

def require_admin(x_admin_key: str | None = Header(default=None)):
    expected = os.getenv("BRAHMVAKYA_ADMIN_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Set BRAHMVAKYA_ADMIN_KEY in the server environment before using saved records.")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail="Admin login required.")

def require_manychat(x_manychat_token: str | None = Header(default=None)):
    expected = os.getenv("MANYCHAT_WEBHOOK_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Set MANYCHAT_WEBHOOK_TOKEN in the server environment before enabling ManyChat intake.")
    if not x_manychat_token or not hmac.compare_digest(x_manychat_token, expected):
        raise HTTPException(status_code=401, detail="Invalid ManyChat webhook token.")

@router.post("/records/login")
def records_login(x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)
    return {"success": True}

class RecordCreate(BaseModel):
    customer_name: str | None = None
    instagram_username: str | None = None
    source: str = "manual"
    query_type: str = "kundli"
    birth_details: dict
    kundli: dict | None = None
    analyses: dict[str, Any] = Field(default_factory=dict)
    result_text: str | None = None

def _record_dict(r: KundliRecord, include_json=True):
    item = {
        "id": r.id, "record_code": r.record_code,
        "customer_name": r.customer_name, "instagram_username": r.instagram_username,
        "source": r.source, "query_type": r.query_type,
        "dob": r.dob, "birth_time": r.birth_time, "birth_place": r.birth_place,
        "latitude": r.latitude, "longitude": r.longitude, "timezone": r.timezone,
        "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "result_text": r.result_text,
    }
    if include_json:
        item["kundli"] = r.kundli_json
        item["analyses"] = r.analyses_json
    return item

def _build_result(kundli: dict, query_type: str):
    analyses = {}
    errors = {}
    jobs = {
        "grah_nirdeshan": lambda: calculate_grah_nirdeshan(kundli),
        "significators": lambda: calculate_significators(kundli),
        "property": lambda: calculate_property_analysis(kundli),
        "childbirth": lambda: calculate_childbirth_analysis(kundli),
        "upcoming_events": lambda: calculate_all_upcoming_events(kundli),
    }
    # Save all requested calculations automatically; each analysis is isolated so
    # one failure does not discard the chart or the other successful calculations.
    for name, fn in jobs.items():
        try:
            analyses[name] = fn()
        except Exception as exc:
            errors[name] = str(exc)
    if errors:
        analyses["_calculation_errors"] = errors

    moon = kundli.get("planets", {}).get("Moon", {})
    asc = kundli.get("ascendant", {})
    reply = (
        f"Your Brahmvakya Kundli is ready.\n"
        f"Janma Rashi: {moon.get('sign', 'unavailable')}\n"
        f"Lagna: {asc.get('sign', 'unavailable')}\n"
        f"Janma Nakshatra: {moon.get('nakshatra', 'unavailable')}\n"
        f"Record ID: pending"
    )
    query = query_type.strip().lower().replace("-", "_").replace(" ", "_")
    if query in ("rashi", "moon_sign", "janma_rashi"):
        reply = f"Your Janma Rashi is {moon.get('sign', 'unavailable')}.\nJanma Nakshatra: {moon.get('nakshatra', 'unavailable')}."
    elif query in ("nakshatra", "janma_nakshatra"):
        reply = f"Your Janma Nakshatra is {moon.get('nakshatra', 'unavailable')} (Rashi: {moon.get('sign', 'unavailable')})."
    elif query in ("lagna", "ascendant"):
        reply = f"Your Lagna (Ascendant) is {asc.get('sign', 'unavailable')}."
    return analyses, reply

def _resolve_birth_details(birth: dict) -> dict:
    """Resolve coordinates/timezone from the typed birthplace using Geoapify when needed."""
    b = dict(birth)
    if b.get("latitude") is not None and b.get("longitude") is not None and b.get("timezone"):
        return b
    place = str(b.get("place") or "").strip()
    api_key = os.getenv("GEOAPIFY_API_KEY", "")
    if not place:
        raise HTTPException(status_code=422, detail="birth_place/place is required.")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Automatic birthplace resolution requires GEOAPIFY_API_KEY in Render environment variables."
        )
    try:
        response = requests.get(
            "https://api.geoapify.com/v1/geocode/search",
            params={"text": place, "format": "json", "limit": 1, "apiKey": api_key},
            timeout=12,
        )
        response.raise_for_status()
        items = response.json().get("results", [])
        if not items:
            raise HTTPException(status_code=422, detail=f"Could not find birthplace: {place}")
        item = items[0]
        b["latitude"] = float(item["lat"])
        b["longitude"] = float(item["lon"])
        if not b.get("timezone"):
            from timezonefinder import TimezoneFinder
            b["timezone"] = TimezoneFinder().timezone_at(lat=b["latitude"], lng=b["longitude"])
        if not b.get("timezone"):
            raise HTTPException(status_code=422, detail="Could not determine timezone for this birthplace.")
        b["place"] = item.get("formatted") or place
        return b
    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Birthplace geocoding service is temporarily unavailable.") from exc

def _create_record(payload: RecordCreate):
    b = _resolve_birth_details(payload.birth_details)
    required = ("date", "time", "place", "latitude", "longitude", "timezone")
    missing = [key for key in required if b.get(key) is None or b.get(key) == ""]
    if missing:
        raise HTTPException(status_code=422, detail="Missing birth_details fields: " + ", ".join(missing))
    try:
        req = KundliRequest(
            birth_details=BirthDetails(
                date=str(b["date"]), time=str(b["time"]), place=str(b["place"]),
                latitude=float(b["latitude"]), longitude=float(b["longitude"]), timezone=str(b["timezone"])
            ),
            settings=Settings(**(b.get("settings") or {}))
        )
        kundli = payload.kundli or calculate_kundli(req)
        analyses = dict(payload.analyses or {})
        auto_analyses, reply = _build_result(kundli, payload.query_type)
        analyses.update(auto_analyses)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not calculate/save Kundli: {exc}") from exc

    db = SessionLocal()
    try:
        row = KundliRecord(
            record_code="PENDING",
            customer_name=payload.customer_name,
            instagram_username=payload.instagram_username,
            source=payload.source,
            query_type=payload.query_type,
            dob=str(b["date"]), birth_time=str(b["time"]), birth_place=str(b["place"]),
            latitude=float(b["latitude"]), longitude=float(b["longitude"]), timezone=str(b["timezone"]),
            status="completed", kundli_json=kundli, analyses_json=analyses, result_text=reply
        )
        db.add(row)
        db.flush()
        row.record_code = f"BV-{datetime.now().strftime('%Y%m')}-{row.id:06d}"
        row.result_text = reply.replace("Record ID: pending", f"Record ID: {row.record_code}")
        db.commit()
        db.refresh(row)
        return _record_dict(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Could not save Kundli record: {exc}") from exc
    finally:
        db.close()

@router.post("/records")
def create_record(payload: RecordCreate, _: None = Depends(require_admin)):
    return {"success": True, "record": _create_record(payload)}

@router.get("/records")
def list_records(_: None = Depends(require_admin), q: str = Query(default="", max_length=200), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    db = SessionLocal()
    try:
        query = db.query(KundliRecord)
        if q.strip():
            term = f"%{q.strip()}%"
            query = query.filter(or_(
                KundliRecord.customer_name.ilike(term),
                KundliRecord.instagram_username.ilike(term),
                KundliRecord.birth_place.ilike(term),
                KundliRecord.dob.ilike(term),
                KundliRecord.record_code.ilike(term),
            ))
        rows = query.order_by(desc(KundliRecord.created_at)).offset(offset).limit(limit).all()
        return {"success": True, "records": [_record_dict(r, include_json=False) for r in rows]}
    finally:
        db.close()

@router.get("/records/{record_id}")
def get_record(record_id: str, _: None = Depends(require_admin)):
    db = SessionLocal()
    try:
        row = db.query(KundliRecord).filter(
            or_(KundliRecord.record_code == record_id, KundliRecord.id == (int(record_id) if record_id.isdigit() else -1))
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Saved Kundli not found.")
        return {"success": True, "record": _record_dict(row)}
    finally:
        db.close()

@router.get("/reports/{record_code}.pdf")
def download_report(record_code: str, token: str = Query(...)):
    """Public, unguessable token link for the customer's generated PDF report."""
    db = SessionLocal()
    try:
        row = db.query(KundliRecord).filter(KundliRecord.record_code == record_code).first()
        if not row or not hmac.compare_digest(row.report_token, token):
            raise HTTPException(status_code=404, detail="Report not found.")
        kundli = row.kundli_json
        planets = kundli.get("planets", {})
        styles = getSampleStyleSheet()
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Brahmvakya Kundli {record_code}")
        story = [
            Paragraph("Brahmvakya — Kundli Report", styles["Title"]),
            Paragraph(f"Record: {record_code}", styles["Normal"]),
            Paragraph(f"Name: {row.customer_name or 'Customer'}", styles["Normal"]),
            Paragraph(f"Date of birth: {row.dob} | Time: {row.birth_time}", styles["Normal"]),
            Paragraph(f"Birth place: {row.birth_place} ({row.timezone})", styles["Normal"]),
            Spacer(1, 12),
            Paragraph("Chart Summary", styles["Heading2"]),
            Paragraph(f"Lagna: {kundli.get('ascendant', {}).get('sign', '—')}", styles["Normal"]),
            Paragraph(f"Janma Rashi: {planets.get('Moon', {}).get('sign', '—')}", styles["Normal"]),
            Paragraph(f"Janma Nakshatra: {planets.get('Moon', {}).get('nakshatra', '—')}", styles["Normal"]),
            Spacer(1, 10),
            Paragraph("Planetary Positions", styles["Heading2"]),
        ]
        rows = [["Planet", "Sign", "Degree", "House", "Nakshatra", "Star Lord"]]
        for name, p in planets.items():
            rows.append([name, str(p.get("sign", "—")), f"{float(p.get('degree_in_sign', 0)):.4f}°",
                         str(p.get("house", "—")), str(p.get("nakshatra", "—")), str(p.get("nakshatra_lord", "—"))])
        table = Table(rows, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243247")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f5f8")]),
        ]))
        story.extend([table, Spacer(1, 12), Paragraph("Vimshottari Dasha", styles["Heading2"])])
        dasha = kundli.get("vimshottari_dasha", {})
        for heading, key in [("Mahadasha", "mahadasha"), ("Antardasha", "antardasha"), ("Pratyantardasha", "pratyantardasha")]:
            story.append(Paragraph(heading, styles["Heading3"]))
            periods = dasha.get(key, [])
            if not periods:
                story.append(Paragraph("No periods available.", styles["Normal"]))
                continue
            if key == "mahadasha":
                drows = [["Planet", "Start", "End"]]
                drows += [[str(x.get("planet","")), str(x.get("start",""))[:10], str(x.get("end",""))[:10]] for x in periods]
            elif key == "antardasha":
                drows = [["MD", "AD", "Start", "End"]]
                drows += [[str(x.get("mahadasha","")), str(x.get("antardasha","")), str(x.get("start",""))[:10], str(x.get("end",""))[:10]] for x in periods]
            else:
                drows = [["MD", "AD", "PD", "Start", "End"]]
                drows += [[str(x.get("mahadasha","")), str(x.get("antardasha","")), str(x.get("pratyantardasha","")), str(x.get("start",""))[:10], str(x.get("end",""))[:10]] for x in periods]
            dtable = Table(drows, repeatRows=1, hAlign="LEFT")
            dtable.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#243247")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
                ("FONTSIZE", (0,0), (-1,-1), 7),
            ]))
            story.append(dtable)
            story.append(Spacer(1, 8))
        story.extend([Spacer(1, 8), Paragraph("Saved analysis results", styles["Heading2"])])
        for name, value in (row.analyses_json or {}).items():
            if name.startswith("_"):
                continue
            story.append(Paragraph(name.replace("_", " ").title(), styles["Heading3"]))
            summary = str(value)
            if len(summary) > 3500:
                summary = summary[:3500] + " ..."
            story.append(Paragraph(summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]))
            story.append(Spacer(1, 5))
        doc.build(story)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf", headers={
            "Content-Disposition": f'inline; filename="{record_code}-kundli.pdf"'
        })
    finally:
        db.close()

def _report_token(record_code: str) -> str:
    db = SessionLocal()
    try:
        row = db.query(KundliRecord).filter(KundliRecord.record_code == record_code).first()
        if not row:
            raise HTTPException(status_code=404, detail="Saved Kundli not found.")
        return row.report_token
    finally:
        db.close()

@router.post("/manychat/intake")
def manychat_intake(payload: dict, _: None = Depends(require_manychat)):
    """ManyChat External Request endpoint. Requires resolved coordinates/timezone."""
    birth = payload.get("birth_details") or {
        "date": payload.get("dob") or payload.get("date_of_birth"),
        "time": payload.get("birth_time") or payload.get("time"),
        "place": payload.get("birth_place") or payload.get("place"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "timezone": payload.get("timezone"),
    }
    create_payload = RecordCreate(
        customer_name=payload.get("customer_name") or payload.get("name"),
        instagram_username=payload.get("instagram_username") or payload.get("ig_username"),
        source="manychat",
        query_type=payload.get("query_type") or payload.get("request_type") or payload.get("query") or "kundli",
        birth_details=birth,
    )
    record = _create_record(create_payload)
    base_url = os.getenv("BRAHMVAKYA_PUBLIC_BASE_URL", "").rstrip("/")
    report_url = f"{base_url}/api/reports/{record['record_code']}.pdf?token={_report_token(record['record_code'])}" if base_url else ""
    reply = record["result_text"]
    if report_url:
        reply += f"\nDownload your Kundli report: {report_url}"
    return {
        "success": True,
        "record_id": record["record_code"],
        "status": "completed",
        "reply": reply,
        "report_url": report_url,
        "kundli_summary": {
            "lagna": record["kundli"].get("ascendant", {}).get("sign"),
            "rashi": record["kundli"].get("planets", {}).get("Moon", {}).get("sign"),
            "nakshatra": record["kundli"].get("planets", {}).get("Moon", {}).get("nakshatra"),
        },
    }
