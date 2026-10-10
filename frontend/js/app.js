// Use the local FastAPI server during development and same-origin APIs on Render.
const API_BASE_URL =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : window.location.origin;
const API = `${API_BASE_URL}/api`;
const placeInput = document.getElementById("place");
const suggestions = document.getElementById("suggestions");
const selectedPlace = document.getElementById("selectedPlace");
const calculate = document.getElementById("calculate");
const statusEl = document.getElementById("status");
let selected = null;
let timer = null;
let latestKundli = null;
let latestUpcomingEvents = null;

function setStatus(msg, cls="") {
  statusEl.textContent = msg;
  statusEl.className = cls;
}

placeInput.addEventListener("input", () => {
  selected = null;
  calculate.disabled = true;
  selectedPlace.textContent = "";
  clearTimeout(timer);
  const q = placeInput.value.trim();
  if (q.length < 2) { suggestions.innerHTML = ""; return; }
  timer = setTimeout(async () => {
    try {
      const r = await fetch(`${API}/places/search?q=${encodeURIComponent(q)}`);
      if (!r.ok) throw new Error("Place search failed");
      const data = await r.json();
      suggestions.innerHTML = "";
      data.results.forEach(item => {
        const div = document.createElement("div");
        div.textContent = item.display_name;
        div.onclick = async () => {
          try {
            const tzr = await fetch(`${API}/places/timezone?latitude=${item.latitude}&longitude=${item.longitude}`);
            if (!tzr.ok) throw new Error("Timezone lookup failed");
            const tz = await tzr.json();
            selected = {...item, timezone: tz.timezone};
            placeInput.value = item.display_name;
            selectedPlace.textContent = `Selected: ${item.display_name} • ${tz.timezone}`;
            selectedPlace.className = "selected";
            suggestions.innerHTML = "";
            calculate.disabled = false;
          } catch (e) {
            setStatus(e.message, "error");
          }
        };
        suggestions.appendChild(div);
      });
    } catch (e) {
      setStatus(e.message, "error");
    }
  }, 350);
});

calculate.onclick = async () => {
  if (!selected) return;
  const dob = document.getElementById("dob").value;
  const time = document.getElementById("time").value;
  if (!dob || !time) {
    setStatus("Enter date and time of birth.", "error");
    return;
  }
  setStatus("Calculating Kundli...", "");
  try {
    const payload = {
      birth_details: {
        date: dob,
        time: time.length === 5 ? `${time}:00` : time,
        place: selected.display_name,
        latitude: selected.latitude,
        longitude: selected.longitude,
        timezone: selected.timezone
      },
      settings: {
        zodiac: "sidereal",
        ayanamsha: "Lahiri",
        node_type: "mean",
        house_system: "whole_sign"
      }
    };
    const r = await fetch(`${API}/kundli`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Kundli calculation failed");
    render(data.kundli);
    setStatus("Kundli calculated. Saving record and scanning upcoming events...", "");
    try {
      const adminKey = sessionStorage.getItem("brahmvakyaAdminKey") || "";
      if (!adminKey) throw new Error("Unlock Saved Kundlis with your admin key before calculating, so records can be saved.");
      const saved = await fetch(`${API}/records`, {
        method: "POST",
        headers: {"Content-Type":"application/json", "X-Admin-Key": adminKey},
        body: JSON.stringify({
          source: "manual",
          query_type: "kundli",
          birth_details: payload.birth_details,
          kundli: data.kundli
        })
      });
      const savedData = await saved.json();
      if (!saved.ok) throw new Error(savedData.detail || "Record save failed");
      setStatus(`Kundli calculated and saved as ${savedData.record.record_code}. Scanning upcoming events...`, "");
      await loadSavedRecords();
    } catch (saveError) {
      setStatus(`Kundli calculated, but saving failed: ${saveError.message}`, "error");
    }
    await fetchUpcomingEvents(true);
    if (!statusEl.className.includes("error")) {
      setStatus("Kundli, saved record and upcoming event timing completed.", "ok");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
};

document.getElementById("calcGrahNirdeshan").onclick = async () => {
  if (!latestKundli) return;
  setStatus("Generating Grah Nirdeshan table...", "");
  try {
    const r = await fetch(`${API}/grah-nirdeshan`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(latestKundli)
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Grah Nirdeshan calculation failed");
    renderGrahNirdeshan(data.result);
    setStatus("Grah Nirdeshan table generated successfully.", "ok");
  } catch (e) {
    setStatus(e.message, "error");
  }
};

function renderGrahNirdeshan(result) {
  const tbody = document.querySelector("#grahNirdeshanTable tbody");
  tbody.innerHTML = "";
  result.rows.forEach(row => {
    const tr = document.createElement("tr");
    [row.planet, row.signified_bhavas.join(", ") || "—"].forEach(v => {
      const td = document.createElement("td");
      td.textContent = v;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  document.getElementById("grahNirdeshanJson").textContent = JSON.stringify(result, null, 2);
}

document.getElementById("calcSig").onclick = async () => {
  if (!latestKundli) return;
  setStatus("Generating significator table...", "");
  try {
    const r = await fetch(`${API}/significators`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(latestKundli)
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Significator calculation failed");
    renderSignificators(data.result);
    setStatus("Significator table generated successfully.", "ok");
  } catch (e) {
    setStatus(e.message, "error");
  }
};

function renderSignificators(result) {
  const tbody = document.querySelector("#sigTable tbody");
  tbody.innerHTML = "";
  for (const row of Object.values(result.significators)) {
    const vals = [
      row.planet,
      row.level_1_star_lord_placement.join(", ") || "—",
      row.level_2_star_lord_ownership.join(", ") || "—",
      row.level_3_planet_placement.join(", ") || "—",
      row.level_4_planet_ownership.join(", ") || "—",
      row.level_5_aspects.join(", ") || "—",
      row.nakshatra_lord || "—",
      row.significator_houses.join(", ") || "—",
      row.marriage_houses.length ? `Qualified: ${row.marriage_houses.join(", ")}` : "Not Qualified"
    ];
    const tr = document.createElement("tr");
    vals.forEach(v => { const td=document.createElement("td"); td.textContent=v; tr.appendChild(td); });
    tbody.appendChild(tr);
  }

  const nav = result.navamsha_7th_lord_verification;
  const gate = result.dasha_gate;
  const trigger = result.final_exact_window;
  let html = `<h3>1. Navamsha 7th Lord Verification</h3>
    <p><b>Navamsha Lagna:</b> ${nav.navamsha_lagna_sign} • <b>7th sign:</b> ${nav.navamsha_7th_sign} • <b>7th lord:</b> ${nav.navamsha_7th_lord}</p>
    <p><b>7th lord's Lagna significator houses:</b> ${nav["7th_lord_significator_houses"].join(", ") || "—"}</p>
    <p><b>Marriage houses found:</b> ${nav.marriage_houses_found.join(", ") || "None"} — <b>${nav.qualified ? "MARRIAGE PROMISED" : "NO MARRIAGE PROMISE — STOP"}</b></p>`;

  if (gate.verification) {
    html += `<h3>3. Dasha Trio Verification</h3>
      <p><b>MD ${gate.verification.MD.lord}</b> → houses ${gate.verification.MD.qualified_houses.join(", ")};
      <b>AD ${gate.verification.AD.lord}</b> → houses ${gate.verification.AD.qualified_houses.join(", ")};
      <b>PD ${gate.verification.PD.lord}</b> → houses ${gate.verification.PD.qualified_houses.join(", ")}.</p>`;
  }

  html += `<h3>4. Most Upcoming Marriage Window</h3>`;
  const futureMarriage = latestUpcomingEvents?.marriage?.timing;
  if (futureMarriage?.status === "MATCH FOUND") {
    html += `<p><b>Status:</b> MATCH FOUND<br>
      <b>Dasha Combination:</b> ${futureMarriage.dasha_combination}<br>
      <b>Valid Period:</b> <b>${shortDate(futureMarriage.valid_start)}</b> → <b>${shortDate(futureMarriage.valid_end)}</b></p>`;
  } else if (futureMarriage?.status === "NO MATCHING DASHA FOUND") {
    html += `<p><b>Status:</b> NO MATCHING DASHA FOUND<br>${futureMarriage.reason}</p>`;
  } else {
    html += `<p>Forward timing will be shown after the current/upcoming Dasha scan.</p>`;
  }
  document.getElementById("marriageSummary").innerHTML = html;
  document.getElementById("sigJson").textContent = JSON.stringify(result, null, 2);
}

function render(k) {
  latestKundli = k;
  renderDasha(k.vimshottari_dasha);
  document.getElementById("result").classList.remove("hidden");
  document.getElementById("summary").textContent =
    `${k.birth_details.date} ${k.birth_details.time} • ${k.birth_details.place} • ${k.birth_details.timezone}`;
  document.getElementById("ascendant").textContent =
    `${k.ascendant.sign} • ${k.ascendant.degree_in_sign.toFixed(6)}° • longitude ${k.ascendant.longitude.toFixed(6)}°`;
  const tbody = document.querySelector("#planetTable tbody");
  tbody.innerHTML = "";
  for (const [name,p] of Object.entries(k.planets)) {
    const tr = document.createElement("tr");
    [name,p.sign,`${p.degree_in_sign.toFixed(6)}°`,p.house,p.nakshatra,p.nakshatra_lord,p.pada,p.retrograde ? "Yes":"No"]
      .forEach(v => { const td=document.createElement("td"); td.textContent=v; tr.appendChild(td); });
    tbody.appendChild(tr);
  }
  document.getElementById("json").textContent = JSON.stringify(k, null, 2);
  document.getElementById("copyJson").onclick = () =>
    navigator.clipboard.writeText(JSON.stringify(k, null, 2));
}

function renderDasha(dasha) {
  if (!dasha) return;
  const moon = dasha.moon_calculation;
  const v = dasha.verification;
  document.getElementById("dashaSummary").innerHTML = `
    <p><b>Year convention:</b> ${dasha.year_convention} • <b>Cycle:</b> ${dasha.total_cycle_years} years</p>
    <p><b>Moon sidereal longitude:</b> ${moon.sidereal_longitude}° • <b>Janma Nakshatra:</b> ${moon.janma_nakshatra} • <b>Pada:</b> ${moon.nakshatra_pada} • <b>Nakshatra Lord:</b> ${moon.nakshatra_lord}</p>
    <p><b>Completed:</b> ${moon.completed_arcminutes}′ / 800′ • <b>Remaining:</b> ${moon.remaining_arcminutes}′ / 800′</p>
    <p><b>Initial MD balance:</b> ${moon.first_mahadasha_years} × ${moon.remaining_arcminutes} / 800 = <b>${moon.initial_balance_years} years</b> = ${moon.initial_balance_days} days</p>
    <p><b>Date conversion:</b> ${dasha.formulas.date_conversion}</p>`;

  const mdBody = document.querySelector("#mdTable tbody");
  mdBody.innerHTML = "";
  dasha.mahadasha.forEach(x => {
    const tr = document.createElement("tr");
    [x.planet, shortDate(x.start), shortDate(x.end), x.duration, x.duration_days].forEach(v => { const td=document.createElement("td"); td.textContent=v; tr.appendChild(td); });
    mdBody.appendChild(tr);
  });

  const adBody = document.querySelector("#adTable tbody");
  adBody.innerHTML = "";
  dasha.antardasha.forEach(x => {
    const tr = document.createElement("tr");
    [x.mahadasha, x.antardasha, shortDate(x.start), shortDate(x.end), x.duration, x.duration_days].forEach(v => { const td=document.createElement("td"); td.textContent=v; tr.appendChild(td); });
    adBody.appendChild(tr);
  });

  const pdBody = document.querySelector("#pdTable tbody");
  pdBody.innerHTML = "";
  dasha.pratyantardasha.forEach(x => {
    const tr = document.createElement("tr");
    [x.mahadasha, x.antardasha, x.pratyantardasha, shortDate(x.start), shortDate(x.end), x.duration, x.duration_days].forEach(v => { const td=document.createElement("td"); td.textContent=v; tr.appendChild(td); });
    pdBody.appendChild(tr);
  });

  document.getElementById("dashaVerification").textContent = JSON.stringify({
    formulas: dasha.formulas,
    numerical_calculation: dasha.numerical_calculation,
    verification: {
      full_planetary_cycle_years: v.full_planetary_cycle_years,
      full_planetary_cycle_equals_120: v.full_planetary_cycle_equals_120,
      birth_horizon_equals_120: v.birth_horizon_equals_120,
      all_antardashas_equal_parent_mahadasha: v.all_antardashas_equal_parent_mahadasha,
      all_pratyantardashas_equal_parent_antardasha: v.all_pratyantardashas_equal_parent_antardasha,
      no_mahadasha_gaps_or_overlaps: v.no_mahadasha_gaps_or_overlaps,
      no_antardasha_gaps_or_overlaps: v.no_antardasha_gaps_or_overlaps,
      no_pratyantardasha_gaps_or_overlaps: v.no_pratyantardasha_gaps_or_overlaps,
      initial_balance_formula_verified: v.initial_balance_formula_verified
    }
  }, null, 2);
}

document.getElementById("calcProperty").onclick = async () => {
  if (!latestKundli) return;
  setStatus("Analyzing house purchase rules...", "");
  try {
    const r = await fetch(`${API}/property-analysis`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(latestKundli)
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Property analysis failed");
    renderProperty(data.result);
    setStatus("House purchase analysis generated successfully.", "ok");
  } catch (e) {
    setStatus(e.message, "error");
  }
};

function renderProperty(result) {
  const rule1 = result.rule_1_navamsa_4th_lord_verification;
  const rule2 = result.rule_2_saturn_mars_connection_verification;
  const rahu = result.rahu_influence_check;
  const verdict = result.final_promise_verdict;
  const timing = result.timing_of_event;

  let html = `<h3>Rule 1 Verification</h3>
    <p><b>Navamsha Lagna:</b> ${rule1.navamsha_lagna_sign} • <b>4th house sign:</b> ${rule1.navamsha_4th_house_sign} • <b>4th Lord:</b> ${rule1.navamsha_4th_lord}</p>
    <p><b>Star Lord (न):</b> ${rule1.nakshatra_lord || "—"}</p>
    <p><b>Level 1 — Star Lord placement:</b> ${rule1.levels.level_1_star_lord_placement.join(", ") || "—"}<br>
    <b>Level 2 — Star Lord ownership:</b> ${rule1.levels.level_2_star_lord_ownership.join(", ") || "—"}<br>
    <b>Level 3 — Navamsha 4th Lord placement:</b> ${rule1.levels.level_3_planet_placement.join(", ") || "—"}<br>
    <b>Level 4 — Navamsha 4th Lord ownership:</b> ${rule1.levels.level_4_planet_ownership.join(", ") || "—"}<br>
    <b>Level 5 — D1 Drishti:</b> ${rule1.levels.level_5_aspects.join(", ") || "—"}</p>
    <p><b>2/4/11/12 found:</b> ${rule1.property_houses_found.join(", ") || "None"} — <b>${rule1.passed ? "PASS" : "FAIL"}</b></p>`;

  html += `<h3>Rule 2 Verification</h3><p><b>Lagna 4th sign:</b> ${rule2.lagna_4th_house_sign} • <b>Lagna 4th Lord:</b> ${rule2.lagna_4th_lord} • <b>Navamsha 4th Lord:</b> ${rule2.navamsha_4th_lord}</p>`;
  rule2.checks.filter(x => x.connected).forEach(x => {
    html += `<p><b>${x.subject} ↔ ${x.target}</b>: ${x.connections.map(c => c.detail).join("; ")}</p>`;
  });
  if (!rule2.passed) html += `<p><b>No allowed Saturn/Mars connection found.</b></p>`;
  html += `<p><b>Rule 2:</b> ${rule2.passed ? "PASS" : "FAIL"}</p>`;

  html += `<h3>Rahu Influence Check</h3><p>${rahu.affliction_present ? "<b>Rahu affliction PRESENT.</b> " + rahu.reasons.join(" ") : "<b>No Rahu affliction under the specified rule.</b>"}</p>`;
  html += `<h3>Final Promise Verdict</h3><p><b>Khud ka makaan hoga: ${verdict.khud_ka_makaan_hoga}</b><br>${verdict.basis}</p>`;

  html += `<h3>Most Upcoming Property Window</h3>`;
  const futureProperty = latestUpcomingEvents?.property?.timing;
  if (futureProperty?.status === "MATCH FOUND") {
    html += `<p><b>Status:</b> MATCH FOUND<br><b>Dasha Combination:</b> ${futureProperty.dasha_combination}<br>
      <b>Valid Period:</b> <b>${shortDate(futureProperty.valid_start)}</b> → <b>${shortDate(futureProperty.valid_end)}</b></p>`;
  } else if (futureProperty?.status === "NO MATCHING DASHA FOUND") {
    html += `<p><b>Status:</b> NO MATCHING DASHA FOUND<br>${futureProperty.reason}</p>`;
  } else {
    html += `<p>Forward timing will be shown after the current/upcoming Dasha scan.</p>`;
  }
  html += `<p><b>Legacy timing table:</b> retained in JSON for audit only; the displayed event date above is always forward-scanned from today.</p>`;
  document.getElementById("propertySummary").innerHTML = html;

  const tbody = document.querySelector("#propertyTable tbody");
  tbody.innerHTML = "";
  for (const row of Object.values(result.significators)) {
    const houses = [...new Set(row.significator_houses.filter(h => [2,4,11,12].includes(h)))].sort((a,b)=>a-b);
    const vals = [row.planet, row.level_1_star_lord_placement.join(", ") || "—", row.level_2_star_lord_ownership.join(", ") || "—", row.level_3_planet_placement.join(", ") || "—", row.level_4_planet_ownership.join(", ") || "—", row.level_5_aspects.join(", ") || "—", houses.join(", ") || "—", houses.length ? "Qualified" : "Not Qualified"];
    const tr = document.createElement("tr");
    vals.forEach(v => { const td=document.createElement("td"); td.textContent=v; tr.appendChild(td); });
    tbody.appendChild(tr);
  }
  document.getElementById("propertyJson").textContent = JSON.stringify(result, null, 2);
}

document.getElementById("calcChildbirth").onclick = async () => {
  if (!latestKundli) return;
  setStatus("Analyzing childbirth rules...", "");
  try {
    const r = await fetch(`${API}/childbirth-analysis`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(latestKundli)
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Childbirth analysis failed");
    renderChildbirth(data.result);
    setStatus("Childbirth analysis generated successfully.", "ok");
  } catch (e) {
    setStatus(e.message, "error");
  }
};

function renderChildbirth(result) {
  const r1 = result.rule_1_core_promise;
  const r2 = result.rule_2_delivery_nature;
  const r3 = result.rule_3_rahu_influence;
  const timing = result.rule_4_timing;

  let html = `<h3>1. Core Promise</h3>
    <p><b>D9 5th house sign:</b> ${r1.navamsha_5th_house_sign} • <b>D9 5th Lord:</b> ${r1.navamsha_5th_lord}</p>
    <p><b>D1 significator houses of NP:</b> ${r1.d1_significator_houses.join(", ") || "—"}<br>
    <b>2/5/11 found:</b> ${r1.childbirth_houses_found.join(", ") || "None"}<br>
    <b>Verdict:</b> ${r1.verdict}</p>
    <p><b>Five-level trace:</b><br>
    L1 Star Lord placement: ${r1.five_level_trace.level_1_star_lord_placement.join(", ") || "—"}<br>
    L2 Star Lord ownership: ${r1.five_level_trace.level_2_star_lord_ownership.join(", ") || "—"}<br>
    L3 Planet placement: ${r1.five_level_trace.level_3_planet_placement.join(", ") || "—"}<br>
    L4 Planet ownership: ${r1.five_level_trace.level_4_planet_ownership.join(", ") || "—"}<br>
    L5 Aspects: ${r1.five_level_trace.level_5_aspects.join(", ") || "—"}<br>
    Nakshatra Lord: ${r1.five_level_trace.nakshatra_lord || "—"}</p>`;

  html += `<h3>2. Delivery Nature (Cesarean Risk)</h3>
    <p><b>Entity tested:</b> ${r2.entity_tested}<br><b>House 8 found:</b> ${r2.house_8_found ? "YES" : "NO"}<br>
    <b>Verdict:</b> ${r2.verdict}<br>${r2.proof}</p>`;

  html += `<h3>Rahu Influence</h3><p>
    Rahu in D1 4th: <b>${r3.rahu_in_4th ? "YES" : "NO"}</b> •
    D9 5th Lord in Rahu star: <b>${r3.d9_5th_lord_in_rahu_star ? "YES" : "NO"}</b> •
    D9 5th Lord conjunct Rahu: <b>${r3.d9_5th_lord_conjunct_rahu ? "YES" : "NO"}</b><br>
    <b>${r3.quality_verdict}</b></p>`;

  html += `<h3>3. Favorable Timing Windows</h3>
    <p><b>Rule:</b> ${timing.rule}</p>`;
  if (timing.active_period) {
    const a = timing.active_period;
    html += `<p><b>Current active period:</b> MD ${a.md} → AD ${a.ad} → PD ${a.pd}<br>${a.pd_start} → ${a.pd_end}</p>`;
  } else {
    html += `<p><b>Current active period:</b> Not found within the generated dasha horizon.</p>`;
  }
  const futureChild = latestUpcomingEvents?.childbirth?.timing;
  html += `<h3>Most Upcoming Childbirth Window</h3>`;
  if (futureChild?.status === "MATCH FOUND") {
    html += `<p><b>Status:</b> MATCH FOUND<br><b>Dasha Combination:</b> ${futureChild.dasha_combination}<br>
      <b>Valid Period:</b> <b>${shortDate(futureChild.valid_start)}</b> → <b>${shortDate(futureChild.valid_end)}</b></p>`;
  } else if (futureChild?.status === "NO MATCHING DASHA FOUND") {
    html += `<p><b>Status:</b> NO MATCHING DASHA FOUND<br>${futureChild.reason}</p>`;
  } else {
    html += `<p>Forward timing will be shown after the current/upcoming Dasha scan.</p>`;
  }
  html += `<p><b>Historical timing rows:</b> ${timing.favorable_timing_windows.length} (kept in JSON for audit; displayed prediction above is forward-only).</p>`;

  document.getElementById("childbirthSummary").innerHTML = html;
  document.getElementById("childbirthJson").textContent = JSON.stringify(result, null, 2);
}

async function fetchUpcomingEvents(silent=false) {
  if (!latestKundli) {
    if (!silent) setStatus("Please calculate the Kundli first.", "error");
    return null;
  }

  const button = document.getElementById("calcUpcomingEvents");
  const tbody = document.querySelector("#upcomingEventsTable tbody");
  if (!silent) {
    setStatus("Scanning forward from today for the earliest matching event windows...", "");
    button.disabled = true;
    tbody.innerHTML = `<tr><td colspan="6">Calculating upcoming dates from the current date/time…</td></tr>`;
  }

  try {
    // Send the browser's exact current timestamp. The backend converts it to
    // the birth-place timezone and uses it as T0 for the forward-only scan.
    const t0 = new Date().toISOString();
    const r = await fetch(`${API}/upcoming-events`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({kundli: latestKundli, query_datetime: t0})
    });

    const text = await r.text();
    let data;
    try { data = JSON.parse(text); }
    catch (_) { throw new Error(`Server returned a non-JSON response (HTTP ${r.status}). Is the updated FastAPI backend running?`); }

    if (!r.ok) throw new Error(data.detail || `Upcoming event timing failed (HTTP ${r.status})`);
    if (!data.result) throw new Error("Backend returned no upcoming-event result.");

    latestUpcomingEvents = data.result;
    renderUpcomingEvents(data.result);

    if (!silent) setStatus("Upcoming event timing generated successfully from today.", "ok");
    return data.result;
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6">Unable to calculate upcoming dates: ${String(e.message).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}</td></tr>`;
    if (!silent) setStatus(e.message, "error");
    throw e;
  } finally {
    if (!silent) button.disabled = false;
  }
}

document.getElementById("calcUpcomingEvents").onclick = async () => {
  try {
    await fetchUpcomingEvents(false);
  } catch (e) {
    // fetchUpcomingEvents already displays the exact error in the page/status bar.
  }
};


function shortDate(value) {
  if (!value) return "—";

  const text = String(value).trim();
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})/);

  if (match) {
    return `${match[3]}-${match[2]}-${match[1]}`;
  }

  if (/^\d{2}-\d{2}-\d{4}$/.test(text)) {
    return text;
  }

  return text;
}


function renderUpcomingEvents(result) {
  const labels = {
    childbirth: "Childbirth",
    marriage: "Marriage",
    property: "Property / Real Estate",
    job: "Job / Promotion",
    foreign: "Foreign Travel / Relocation",
    litigation_disease: "Litigation / Disease"
  };
  const tbody = document.querySelector("#upcomingEventsTable tbody");
  tbody.innerHTML = "";
  const detail = document.getElementById("upcomingEventsDetails");
  detail.innerHTML = "";

  Object.entries(result).forEach(([key, x]) => {
    const t = x.timing || {};
    const tr = document.createElement("tr");
    const values = [
      labels[key] || x.query_category,
      x.target_houses.join(", "),
      x.promise_status,
      x.navamsha_key_lord,
      t.status === "MATCH FOUND" ? t.dasha_combination : t.status,
      t.status === "MATCH FOUND" ? `${shortDate(t.valid_start)} → ${shortDate(t.valid_end)}` : "—"
    ];
    values.forEach(v => { const td=document.createElement("td"); td.textContent=v; tr.appendChild(td); });
    tbody.appendChild(tr);

    let html = `<div class="marriageSummary"><h3>${labels[key] || x.query_category}</h3>
      <p><b>Query Reference Date (T0):</b> ${x.query_reference_date}<br>
      <b>Target Houses:</b> ${x.target_houses.join(", ")} • <b>Primary House:</b> ${x.primary_house}<br>
      <b>Promise:</b> ${x.promise_status} • <b>Navamsha Key Lord:</b> ${x.navamsha_key_lord}<br>
      <b>Signified Bhavas:</b> ${x.navamsha_key_lord_signified_bhavas.join(", ") || "—"}</p>`;
    if (t.status === "MATCH FOUND") {
      const a = t.house_activation;
      html += `<p><b>Status:</b> MATCH FOUND<br>
        <b>Dasha Combination:</b> ${t.dasha_combination}<br>
        <b>Valid Period:</b> ${shortDate(t.valid_start)} → ${shortDate(t.valid_end)}</p>
        <p><b>House Activation:</b><br>
        MD (${a.md.planet}): ${a.md.signified_houses.join(", ") || "—"}<br>
        AD (${a.ad.planet}): ${a.ad.signified_houses.join(", ") || "—"}<br>
        PD (${a.pd.planet}): ${a.pd.signified_houses.join(", ") || "—"}<br>
        Target Set Coverage: ${a.target_set_coverage.join(", ")}</p>`;
    } else {
      html += `<p><b>Status:</b> NO MATCHING DASHA FOUND<br>${x.reason || t.reason || "No qualifying future joint Dasha sequence."}</p>`;
    }
    html += `</div>`;
    detail.insertAdjacentHTML("beforeend", html);
  });
  document.getElementById("upcomingEventsJson").textContent = JSON.stringify(result, null, 2);

  // If an analysis card is already visible, refresh its future-window heading immediately.
  const m = result.marriage?.timing;
  const ps = document.getElementById("marriageSummary");
  if (m && ps && ps.innerHTML) {
    const box = ps.querySelector("h3:last-of-type");
    if (box && box.textContent.includes("Most Upcoming Marriage")) {
      const next = box.nextElementSibling;
      if (next) next.innerHTML = `<b>Status:</b> ${m.status}${m.status === "MATCH FOUND" ? `<br><b>Dasha:</b> ${m.dasha_combination}<br><b>Valid Period:</b> ${shortDate(m.valid_start)} → ${shortDate(m.valid_end)}` : `<br>${m.reason || "No future matching Dasha found."}`}`;
    }
  }
}


/* Saved Kundli history */
const recordsTableBody = document.querySelector("#recordsTable tbody");
const recordsStatus = document.getElementById("recordsStatus");
let recordsSearchTimer = null;

async function loadSavedRecords() {
  if (!recordsTableBody) return;
  const q = document.getElementById("recordSearch")?.value?.trim() || "";
  recordsStatus.textContent = "Loading saved records...";
  try {
    const adminKey = sessionStorage.getItem("brahmvakyaAdminKey") || "";
    if (!adminKey) { recordsStatus.textContent = "Unlock saved records with your admin key."; return; }
    const response = await fetch(`${API}/records?q=${encodeURIComponent(q)}&limit=100`, {
      headers: {"X-Admin-Key": adminKey}
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not load saved records");
    recordsTableBody.innerHTML = "";
    data.records.forEach(record => {
      const tr = document.createElement("tr");
      const values = [
        record.record_code,
        [record.customer_name, record.instagram_username].filter(Boolean).join(" / ") || "Manual entry",
        record.dob,
        record.birth_place,
        record.query_type,
        record.created_at ? new Date(record.created_at).toLocaleString() : "—"
      ];
      values.forEach(value => {
        const td = document.createElement("td");
        td.textContent = value ?? "—";
        tr.appendChild(td);
      });
      const action = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = "Open";
      button.addEventListener("click", () => openSavedRecord(record.record_code));
      action.appendChild(button);
      tr.appendChild(action);
      recordsTableBody.appendChild(tr);
    });
    recordsStatus.textContent = `${data.records.length} saved record(s) shown.`;
  } catch (error) {
    recordsStatus.textContent = `Saved history unavailable: ${error.message}`;
  }
}

async function openSavedRecord(recordId) {
  recordsStatus.textContent = `Opening ${recordId}...`;
  try {
    const adminKey = sessionStorage.getItem("brahmvakyaAdminKey") || "";
    const response = await fetch(`${API}/records/${encodeURIComponent(recordId)}`, {
      headers: {"X-Admin-Key": adminKey}
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not open saved record");
    const record = data.record;
    latestUpcomingEvents = record.analyses?.upcoming_events || null;
    render(record.kundli);
    if (record.analyses?.grah_nirdeshan) renderGrahNirdeshan(record.analyses.grah_nirdeshan);
    if (record.analyses?.significators) renderSignificators(record.analyses.significators);
    if (record.analyses?.property) renderProperty(record.analyses.property);
    if (record.analyses?.childbirth) renderChildbirth(record.analyses.childbirth);
    recordsStatus.textContent = `Loaded ${record.record_code}. Saved calculation results were restored.`;
    setStatus(`Loaded saved Kundli ${record.record_code}.`, "ok");
    window.scrollTo({top: 0, behavior: "smooth"});
  } catch (error) {
    recordsStatus.textContent = `Could not open record: ${error.message}`;
  }
}

document.getElementById("loginRecords")?.addEventListener("click", async () => {
  const key = document.getElementById("adminKey").value;
  const adminStatus = document.getElementById("adminStatus");
  adminStatus.textContent = "Checking key...";
  try {
    const response = await fetch(`${API}/records/login`, {
      method: "POST",
      headers: {"X-Admin-Key": key}
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Login failed");
    sessionStorage.setItem("brahmvakyaAdminKey", key);
    document.getElementById("adminKey").value = "";
    adminStatus.textContent = "Saved records unlocked for this browser session.";
    await loadSavedRecords();
  } catch (error) {
    sessionStorage.removeItem("brahmvakyaAdminKey");
    adminStatus.textContent = error.message;
  }
});
document.getElementById("refreshRecords")?.addEventListener("click", loadSavedRecords);
document.getElementById("recordSearch")?.addEventListener("input", () => {
  clearTimeout(recordsSearchTimer);
  recordsSearchTimer = setTimeout(loadSavedRecords, 300);
});
document.addEventListener("DOMContentLoaded", loadSavedRecords);
