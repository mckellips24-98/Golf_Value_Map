/* =========================================================================
   Golf Value Map — app.js
   All logic lives here. Course data lives in data/courses.json.
   You should rarely need to edit this file when updating course data.
   ========================================================================= */

"use strict";

/* ------------------------------------------------------------------ */
/* 1. State & storage                                                  */
/* ------------------------------------------------------------------ */

const S = {
  courses: [],          // all courses from JSON
  meta: {},             // level/tier definitions etc.
  here: null,           // {lat, lng} once user shares location
  filters: { text: "", program: "all", radius: 0, chips: new Set() },
  compare: new Set(),   // course ids selected for comparison
  shareList: null,      // ids from a shared ?list= link, or null
  markers: {},          // courseId -> Leaflet marker
  layerOn: { mgc: true, pcc: true, both: true, fav: true },
};

// localStorage helpers (favorites, notes, savings survive on this device)
const store = {
  get(key, fallback) {
    try { return JSON.parse(localStorage.getItem("gvm_" + key)) ?? fallback; }
    catch { return fallback; }
  },
  set(key, val) { localStorage.setItem("gvm_" + key, JSON.stringify(val)); },
};
let FAVS = new Set(store.get("favs", []));
let NOTES = store.get("notes", {});
let LOG = store.get("log", []);

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ------------------------------------------------------------------ */
/* 2. Rules engine — restrictions, "playable now", value scoring       */
/* ------------------------------------------------------------------ */

// Program membership of a course
const inMGC = (c) => !!c.mgc;
const inPCC = (c) => !!c.pcc;
const inBoth = (c) => inMGC(c) && inPCC(c);
const programKey = (c) => (inBoth(c) ? "both" : inMGC(c) ? "mgc" : "pcc");

// Restriction score: 1 = low, 2 = moderate, 3 = high (best of both programs)
function restrictionScore(c) {
  const scores = [];
  if (c.mgc) scores.push({ A: 1, B: 2, C: 2, D: 3, E: 3, F: 3, G: 3 }[c.mgc.level] ?? 2);
  if (c.pcc) scores.push({ "1": 1, "2": 2, "3": 3, RESORT: 3 }[c.pcc.tier] ?? 2);
  return Math.min(...scores);
}
const RESTR_LABEL = { 1: "Low restriction", 2: "Moderate restriction", 3: "High restriction" };
const RESTR_CLASS = { 1: "badge-low", 2: "badge-mod", 3: "badge-high" };

// Weekend-friendly: at least one program allows some Sat/Sun play.
function weekendFriendly(c) {
  if (c.pcc) return true;                              // PCC allows weekends after blackout
  if (c.mgc) return !["D", "G"].includes(c.mgc.level); // MGC D & G are Mon-Thu only
  return false;
}
// Weekday-only: every program the course is in restricts to weekdays.
function weekdayOnly(c) {
  return !weekendFriendly(c);
}

// --- US federal holidays (both programs black these out) ---
function nthWeekday(year, month, weekday, n) { // month 0-11, weekday 0=Sun
  const d = new Date(year, month, 1);
  let count = 0;
  while (true) {
    if (d.getDay() === weekday && ++count === n) return new Date(d);
    d.setDate(d.getDate() + 1);
  }
}
function lastWeekday(year, month, weekday) {
  const d = new Date(year, month + 1, 0);
  while (d.getDay() !== weekday) d.setDate(d.getDate() - 1);
  return d;
}
function isFederalHoliday(date) {
  const y = date.getFullYear();
  const same = (a) => a.getMonth() === date.getMonth() && a.getDate() === date.getDate();
  const fixed = [[0, 1], [5, 19], [6, 4], [10, 11], [11, 25]]; // NY, Juneteenth, Jul4, Vets, Xmas
  if (fixed.some(([m, d]) => date.getMonth() === m && date.getDate() === d)) return true;
  return [
    nthWeekday(y, 0, 1, 3),   // MLK
    nthWeekday(y, 1, 1, 3),   // Presidents
    lastWeekday(y, 4, 1),     // Memorial
    nthWeekday(y, 8, 1, 1),   // Labor
    nthWeekday(y, 9, 1, 2),   // Columbus
    nthWeekday(y, 10, 4, 4),  // Thanksgiving
  ].some(same);
}
const isJuly3to5 = (d) => d.getMonth() === 6 && d.getDate() >= 3 && d.getDate() <= 5;

/* Playability of ONE program right now.
   Returns { status: "now" | "later" | "no", note } — a heuristic, not gospel. */
function mgcStatus(c, now) {
  const lvl = c.mgc.level, day = now.getDay(), hr = now.getHours() + now.getMinutes() / 60;
  const wd = day >= 1 && day <= 5, monThu = day >= 1 && day <= 4, wknd = day === 0 || day === 6;
  if (isFederalHoliday(now)) return { status: "no", note: "Card not valid on holidays" };
  if (lvl !== "D" && isJuly3to5(now)) return { status: "no", note: "Not valid July 3–5" };
  const after = (h, label) =>
    hr >= h ? { status: "now", note: "Valid now" }
            : { status: "later", note: `Valid after ${label} today` };
  switch (lvl) {
    case "A": return { status: "now", note: "Valid anytime today" };
    case "B": return wd ? { status: "now", note: "Valid all day (weekday)" } : after(13, "1 pm");
    case "C":
      if (monThu) return { status: "now", note: "Valid all day (Mon–Thu)" };
      return after(15, "3 pm");
    case "D": {
      const m = now.getMonth(); // valid Jan–May & Sep–Dec, Mon–Thu
      if (m >= 5 && m <= 7) return { status: "no", note: "Valid only before Jun 1 / after Sep 1" };
      return monThu ? { status: "now", note: "Valid today (shoulder season, Mon–Thu)" }
                    : { status: "no", note: "Mon–Thu only" };
    }
    case "E":
      if (monThu) return hr < 11 ? { status: "now", note: "Valid before 11 am" }
                                 : { status: "no", note: "Weekdays valid before 11 am only" };
      if (wknd) return after(13, "1 pm");
      return { status: "no", note: "Not valid Fridays" };
    case "F": return wd ? after(12, "12 pm") : after(14, "2 pm");
    case "G": return monThu ? { status: "now", note: "Discount rate valid today (Mon–Thu)" }
                            : { status: "no", note: "Mon–Thu only" };
    default:  return { status: "later", note: "Check restrictions" };
  }
}
function pccStatus(c, now) {
  const day = now.getDay(), hr = now.getHours() + now.getMinutes() / 60;
  const restricted = day === 0 || day === 6 || isFederalHoliday(now);
  if (!restricted) return { status: "now", note: "No PCC blackout today" };
  const end = c.pcc.tier === "1" ? 11 : 12;
  if (hr >= end) return { status: "now", note: `Blackout over (after ${end === 11 ? "11 am" : "12 pm"})` };
  return { status: "later", note: `Weekend/holiday blackout until ${end === 11 ? "11 am" : "12 pm"}` };
}
/* Best playability across the programs a course belongs to. */
function playability(c, now = new Date()) {
  const rank = { now: 0, later: 1, no: 2 };
  const opts = [];
  if (c.mgc) opts.push({ prog: "Golf Card", ...mgcStatus(c, now) });
  if (c.pcc) opts.push({ prog: "PCC", ...pccStatus(c, now) });
  opts.sort((a, b) => rank[a.status] - rank[b.status]);
  return opts[0];
}

// Distance (miles) between two lat/lng points
function miles(a, b) {
  const R = 3958.8, rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad, dLng = (b.lng - a.lng) * rad;
  const h = Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
const distTo = (c) => (S.here ? miles(S.here, c) : null);
const fmtDist = (d) => (d == null ? "" : d < 10 ? d.toFixed(1) + " mi" : Math.round(d) + " mi");

/* ------------------------------------------------------------------ */
/* 3. Map                                                              */
/* ------------------------------------------------------------------ */

const map = L.map("map", { zoomControl: true }).setView([45.6, -93.9], 6);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);
let youMarker = null;

// Leaflet measures the map container once, at creation. On mobile (and any time
// the layout isn't final yet) that measurement can come back too small, which
// leaves the tiles and pins drawn outside the visible area — you see a map but
// no course pins. Recomputing the size after the page finishes laying out fixes
// it. Harmless to call more than once.
function fixMapSize() { map.invalidateSize(); }
window.addEventListener("load", fixMapSize);
window.addEventListener("orientationchange", () => setTimeout(fixMapSize, 200));
window.addEventListener("resize", fixMapSize);
setTimeout(fixMapSize, 300);

function pinIcon(c) {
  const fav = FAVS.has(c.id) ? " pin-fav" : "";
  return L.divIcon({
    className: "",
    html: `<div class="pin pin-${programKey(c)}${fav}" style="position:relative"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 20],
  });
}
function buildMarkers() {
  S.courses.forEach((c) => {
    const m = L.marker([c.lat, c.lng], { icon: pinIcon(c) });
    m.bindPopup(
      `<div class="map-popup"><b>${esc(c.name)}</b><br>${esc(c.city)}, ${esc(c.state)}<br>
       <a href="#" onclick="openSheet('${c.id}');return false;">View details →</a></div>`);
    S.markers[c.id] = m;
  });
}
function markerVisible(c, visibleIds) {
  if (!visibleIds.has(c.id)) return false;
  const key = programKey(c);
  if (!S.layerOn[key]) return false;
  if (!S.layerOn.fav && FAVS.has(c.id)) return false;
  return true;
}
function refreshMarkers(visibleIds) {
  S.courses.forEach((c) => {
    const m = S.markers[c.id];
    const show = markerVisible(c, visibleIds);
    if (show && !map.hasLayer(m)) m.addTo(map);
    if (!show && map.hasLayer(m)) map.removeLayer(m);
    if (show) m.setIcon(pinIcon(c)); // refresh fav star
  });
}

/* ------------------------------------------------------------------ */
/* 4. Filtering                                                        */
/* ------------------------------------------------------------------ */

function filteredCourses() {
  const f = S.filters, now = new Date();
  return S.courses.filter((c) => {
    if (S.shareList && !S.shareList.includes(c.id)) return false;
    if (f.text) {
      const t = f.text.toLowerCase();
      if (!c.name.toLowerCase().includes(t) && !c.city.toLowerCase().includes(t)) return false;
    }
    if (f.program === "mgc" && !(inMGC(c) && !inPCC(c))) return false;
    if (f.program === "pcc" && !(inPCC(c) && !inMGC(c))) return false;
    if (f.program === "both" && !inBoth(c)) return false;
    if (f.program === "anymgc" && !inMGC(c)) return false;
    if (f.program === "anypcc" && !inPCC(c)) return false;
    if (f.radius > 0) {
      const d = distTo(c);
      if (d == null || d > f.radius) return false;
    }
    if (f.chips.has("fav") && !FAVS.has(c.id)) return false;
    if (f.chips.has("low") && restrictionScore(c) !== 1) return false;
    if (f.chips.has("weekend") && !weekendFriendly(c)) return false;
    if (f.chips.has("weekday") && !weekdayOnly(c)) return false;
    if (f.chips.has("rar") && !(c.mgc && c.mgc.rideARound)) return false;
    if (f.chips.has("today") && playability(c, now).status !== "now") return false;
    return true;
  });
}

/* ------------------------------------------------------------------ */
/* 5. Rendering                                                        */
/* ------------------------------------------------------------------ */

function programPills(c) {
  let h = "";
  if (inBoth(c)) h += `<span class="pill pill-both">BOTH PROGRAMS</span>`;
  else if (inMGC(c)) h += `<span class="pill pill-mgc">GOLF CARD</span>`;
  else h += `<span class="pill pill-pcc">PCC</span>`;
  if (inMGC(c)) h += `<span class="pill pill-mgc">Level ${esc(c.mgc.level)}</span>`;
  if (inPCC(c)) h += `<span class="pill pill-pcc">Tier ${esc(c.pcc.tier === "RESORT" ? "Resort" : c.pcc.tier)}</span>`;
  if (c.mgc && c.mgc.rideARound) h += `<span class="pill pill-rar">RIDE-A-ROUND</span>`;
  return h;
}
function playBadge(c) {
  const p = playability(c);
  if (p.status === "now") return `<span class="badge badge-now">Playable now*</span>`;
  if (p.status === "later") return `<span class="badge badge-later">Later today*</span>`;
  return `<span class="badge badge-no">Check restrictions</span>`;
}
function restrBadge(c) {
  const r = restrictionScore(c);
  return `<span class="badge ${RESTR_CLASS[r]}">${RESTR_LABEL[r]}</span>`;
}

function courseCard(c, label) {
  const d = distTo(c);
  return `
  <article class="card ${label ? "suggest-card" : ""}" data-id="${c.id}">
    ${label ? `<div class="best-label">${esc(label)}</div>` : ""}
    <div class="card-head">
      <div>
        <h3>${esc(c.name)}</h3>
        <p class="loc">${esc(c.city)}, ${esc(c.state)}</p>
      </div>
      <div style="text-align:right">
        <button class="fav-btn ${FAVS.has(c.id) ? "on" : ""}" data-fav="${c.id}"
                aria-label="Favorite">★</button>
        ${d != null ? `<div class="dist">${fmtDist(d)}</div>` : ""}
      </div>
    </div>
    <div class="pills">${programPills(c)}</div>
    <div class="pills">${restrBadge(c)} ${playBadge(c)}</div>
    <div class="card-actions">
      <button class="mini-btn" data-open="${c.id}">Details</button>
      <button class="mini-btn ${S.compare.has(c.id) ? "on" : ""}" data-cmp="${c.id}">
        ${S.compare.has(c.id) ? "✓ Comparing" : "+ Compare"}
      </button>
    </div>
  </article>`;
}

function renderList() {
  const list = filteredCourses();
  // Sort: distance if known, else name
  list.sort((a, b) => {
    if (S.here) return distTo(a) - distTo(b);
    return a.name.localeCompare(b.name);
  });
  $("#count-badge").textContent = list.length;
  $("#course-list").innerHTML = list.length
    ? list.map((c) => courseCard(c)).join("")
    : `<div class="empty">No courses match these filters.<br>Try widening the radius or clearing a chip.</div>`;
  refreshMarkers(new Set(list.map((c) => c.id)));
}

/* ----- Best today ----- */
function renderBest() {
  const wrap = $("#best-cards");
  if (!S.here) {
    wrap.innerHTML = `<div class="empty">Tap <strong>Locate me</strong> up top and I’ll pick out
      the closest Golf Card, PCC and double-program courses for you.</div>`;
    return;
  }
  const pool = S.courses.filter((c) => !S.shareList || S.shareList.includes(c.id));
  const byDist = [...pool].sort((a, b) => distTo(a) - distTo(b));
  const first = (fn) => byDist.find(fn);
  const picks = [
    ["Closest Golf Card course", first(inMGC)],
    ["Closest PCC course", first(inPCC)],
    ["Closest course in BOTH programs", first(inBoth)],
    ["Best low-restriction option nearby", first((c) => restrictionScore(c) === 1)],
    ["Best value playable right now", first((c) => playability(c).status === "now" && restrictionScore(c) <= 2)],
  ];
  const seen = new Set();
  wrap.innerHTML = picks
    .filter(([, c]) => c && !seen.has(c.id) && seen.add(c.id))
    .map(([label, c]) => courseCard(c, label))
    .join("");
}

/* Bonus feature #1: one-tap suggestion */
function suggestToday() {
  const box = $("#suggest-result");
  if (!S.here) {
    box.innerHTML = `<div class="empty">Share your location first (Locate me) so I can pick something close.</div>`;
    return;
  }
  const now = new Date();
  const cands = S.courses
    .map((c) => ({ c, d: distTo(c), p: playability(c, now), r: restrictionScore(c) }))
    .filter((x) => x.p.status !== "no" && x.d != null && x.d <= 60);
  if (!cands.length) {
    box.innerHTML = `<div class="empty">Nothing looks clearly playable within 60 miles right now — check individual course restrictions.</div>`;
    return;
  }
  // Score: playable now beats later, both-programs beats single, low restriction, then distance
  cands.sort((a, b) =>
    (a.p.status === "now" ? 0 : 1) - (b.p.status === "now" ? 0 : 1) ||
    (inBoth(b.c) ? 1 : 0) - (inBoth(a.c) ? 1 : 0) ||
    a.r - b.r || a.d - b.d);
  const top = cands[0].c;
  box.innerHTML = courseCard(top, "Today’s pick 🏌️");
}

/* ----- Compare (scorecard) ----- */
function renderCompare() {
  $("#cmp-badge").textContent = S.compare.size || "";
  const wrap = $("#compare-wrap");
  const picks = S.courses.filter((c) => S.compare.has(c.id));
  if (picks.length < 2) {
    wrap.innerHTML = `<div class="empty">Select at least 2 courses to compare (max 4).</div>`;
    return;
  }
  const row = (label, fn) =>
    `<tr><td>${label}</td>${picks.map((c) => `<td>${fn(c)}</td>`).join("")}</tr>`;
  wrap.innerHTML = `
  <div class="scorecard"><table>
    <thead><tr><th>Hole ⛳</th>${picks.map((c) => `<th>${esc(c.name)}</th>`).join("")}</tr></thead>
    <tbody>
      ${row("Location", (c) => `${esc(c.city)}, ${esc(c.state)}`)}
      ${row("Distance", (c) => fmtDist(distTo(c)) || "—")}
      ${row("Programs", (c) => programPills(c))}
      ${row("Golf Card offer", (c) => c.mgc ? esc(c.mgc.offer) : "—")}
      ${row("Golf Card times", (c) => c.mgc ? esc(c.mgc.levelText) : "—")}
      ${row("PCC terms", (c) => c.pcc ? esc(c.pcc.tierText) : "—")}
      ${row("Restrictions", (c) => restrBadge(c))}
      ${row("Playable today", (c) => playBadge(c))}
      ${row("Links", (c) => linkRowInline(c))}
    </tbody>
  </table></div>`;
}
function linkRowInline(c) {
  const dir = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(c.address || c.name + " " + c.city + " " + c.state)}`;
  let h = `<a href="${dir}" target="_blank" rel="noopener">Directions</a>`;
  if (c.website) h += ` · <a href="${esc(c.website)}" target="_blank" rel="noopener">Website</a>`;
  if (c.phone) h += ` · <a href="tel:${esc(c.phone)}">Call</a>`;
  return h;
}

/* ----- Savings tracker ----- */
function renderSavings() {
  const total = LOG.reduce((s, r) => s + (Number(r.saved) || 0), 0);
  $("#savings-total").textContent = "$" + total.toLocaleString();
  $("#savings-log").innerHTML = LOG.length
    ? LOG.map((r, i) => `
      <div class="card log-row">
        <div>
          <strong>${esc(r.course)}</strong>
          <div class="loc">${esc(r.date)} · ${esc(r.program)}${r.fee ? ` · normal fee $${esc(r.fee)}` : ""}</div>
        </div>
        <div style="display:flex;align-items:center;gap:6px">
          <span class="dist">saved $${esc(r.saved)}</span>
          <button class="del" data-del="${i}" aria-label="Delete entry">✕</button>
        </div>
      </div>`).join("")
    : `<div class="empty">No rounds logged yet. Every 2-for-1 you redeem is money back in your pocket — track it!</div>`;
}
function fillLogCourses() {
  $("#log-course").innerHTML = S.courses
    .map((c) => `<option>${esc(c.name)}</option>`).join("");
}

/* ----- Detail sheet ----- */
window.openSheet = function (id) {
  const c = S.courses.find((x) => x.id === id);
  if (!c) return;
  const p = playability(c);
  const dir = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(c.address || c.name + " " + c.city + " " + c.state)}`;
  let mgcBox = "";
  if (c.mgc) {
    const rates = c.mgc.reducedRate
      ? `<li>Card rate <b>$${c.mgc.reducedRate}</b> (regular $${c.mgc.regularRate})</li>` : "";
    mgcBox = `
    <div class="rule-box">
      <b>Minnesota Golf Card — Level ${esc(c.mgc.level)}</b>
      <div>${esc(c.mgc.offer)}</div>
      <ul class="restr-list">
        <li>${esc(c.mgc.levelText)}</li>
        ${rates}
        ${c.mgc.cartNotes.map((n) => `<li>${esc(n)}</li>`).join("")}
        ${c.mgc.rideARound ? "<li><b>Ride-a-Round:</b> one-time FREE round for up to 4 players (cart rental required), Mon–Fri only, before May 15 or after Sept 15</li>" : ""}
      </ul>
    </div>`;
  }
  let pccBox = "";
  if (c.pcc) {
    pccBox = `
    <div class="rule-box">
      <b>Public Country Club — Tier ${esc(c.pcc.tier === "RESORT" ? "Resort" : c.pcc.tier)}</b>
      <ul class="restr-list">
        <li>${esc(c.pcc.tierText)}</li>
        ${c.pcc.note ? `<li>${esc(c.pcc.note)}</li>` : ""}
      </ul>
    </div>`;
  }
  $("#sheet-content").innerHTML = `
    <h2>${esc(c.name)}</h2>
    <p class="loc">${esc(c.address || c.city + ", " + c.state)}
      ${distTo(c) != null ? " · " + fmtDist(distTo(c)) + " away" : ""}</p>
    <div class="pills">${programPills(c)} ${restrBadge(c)}
      <span class="badge ${p.status === "now" ? "badge-now" : p.status === "later" ? "badge-later" : "badge-no"}">${esc(p.note)}*</span>
    </div>
    <div class="sheet-section link-row">
      <a href="${dir}" target="_blank" rel="noopener">Directions</a>
      <a ${c.phone ? `href="tel:${esc(c.phone)}"` : 'class="disabled"'}>${c.phone ? "Call" : "No phone"}</a>
      <a ${c.website ? `href="${esc(c.website)}" target="_blank" rel="noopener"` : 'class="disabled"'}>${c.website ? "Website" : "No site"}</a>
    </div>
    <div class="sheet-section"><h4>Program details</h4>${mgcBox}${pccBox}
      ${!c.phone && !inMGC(c) ? `<p class="fineprint">PCC-only listing — phone/address not published on the PCC site. Add them to data/courses.json when you have them.</p>` : ""}
    </div>
    <div class="sheet-section">
      <h4>My notes (saved on this device)</h4>
      <textarea id="notes-input" placeholder="e.g. Great back nine, ask for Mike in the pro shop…">${esc(NOTES[c.id] || "")}</textarea>
    </div>
    <div class="sheet-section row-gap">
      <button class="btn btn-secondary" data-cmp="${c.id}">${S.compare.has(c.id) ? "✓ Comparing" : "+ Compare"}</button>
      <button class="btn ${FAVS.has(c.id) ? "btn-accent" : "btn-ghost"}" data-fav="${c.id}">
        ${FAVS.has(c.id) ? "★ Favorited" : "☆ Favorite"}</button>
    </div>
    <p class="fineprint">*Playability is estimated from listed restrictions and today’s date/time — always confirm with the course.</p>`;
  $("#sheet").classList.remove("hidden");
  $("#sheet-backdrop").classList.remove("hidden");
  $("#notes-input").addEventListener("change", (e) => {
    NOTES[c.id] = e.target.value.trim();
    if (!NOTES[c.id]) delete NOTES[c.id];
    store.set("notes", NOTES);
  });
  map.setView([c.lat, c.lng], Math.max(map.getZoom(), 10));
};
function closeSheet() {
  $("#sheet").classList.add("hidden");
  $("#sheet-backdrop").classList.add("hidden");
}

/* ------------------------------------------------------------------ */
/* 6. Actions & events                                                 */
/* ------------------------------------------------------------------ */

function toggleFav(id) {
  FAVS.has(id) ? FAVS.delete(id) : FAVS.add(id);
  store.set("favs", [...FAVS]);
  renderAll();
  if (!$("#sheet").classList.contains("hidden")) openSheet(id);
}
function toggleCompare(id) {
  if (S.compare.has(id)) S.compare.delete(id);
  else if (S.compare.size >= 4) { alert("Compare holds a foursome — 4 courses max. Remove one first."); return; }
  else S.compare.add(id);
  renderAll();
  if (!$("#sheet").classList.contains("hidden")) openSheet(id);
}
function renderAll() {
  renderList(); renderBest(); renderCompare(); renderSavings();
}

// Delegated clicks for card buttons (list, best, sheet)
document.addEventListener("click", (e) => {
  const open = e.target.closest("[data-open]");
  if (open) return openSheet(open.dataset.open);
  const fav = e.target.closest("[data-fav]");
  if (fav) return toggleFav(fav.dataset.fav);
  const cmp = e.target.closest("[data-cmp]");
  if (cmp) return toggleCompare(cmp.dataset.cmp);
  const del = e.target.closest("[data-del]");
  if (del) { LOG.splice(Number(del.dataset.del), 1); store.set("log", LOG); renderSavings(); }
});

// Search & filters
$("#search").addEventListener("input", (e) => { S.filters.text = e.target.value.trim(); renderList(); });
$("#f-program").addEventListener("change", (e) => { S.filters.program = e.target.value; renderList(); });
$("#f-radius").addEventListener("change", (e) => {
  S.filters.radius = Number(e.target.value);
  if (S.filters.radius && !S.here) locate();
  renderList();
});
$$(".chip[data-filter]").forEach((btn) =>
  btn.addEventListener("click", () => {
    const key = btn.dataset.filter;
    btn.classList.toggle("on");
    btn.classList.contains("on") ? S.filters.chips.add(key) : S.filters.chips.delete(key);
    if (key === "today") { /* nothing extra */ }
    renderList();
  }));

// Layer toggles
$$(".layer-chip").forEach((btn) =>
  btn.addEventListener("click", () => {
    btn.classList.toggle("on");
    S.layerOn[btn.dataset.layer] = btn.classList.contains("on");
    renderList();
  }));

// Tabs
$$(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.remove("on"));
    $$(".tabpane").forEach((x) => x.classList.remove("on"));
    t.classList.add("on");
    $("#tab-" + t.dataset.tab).classList.add("on");
  }));

// Locate
function locate() {
  if (!navigator.geolocation) { alert("This browser doesn't support location."); return; }
  $("#btn-locate").textContent = "Locating…";
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      S.here = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      if (youMarker) map.removeLayer(youMarker);
      youMarker = L.marker([S.here.lat, S.here.lng], {
        icon: L.divIcon({ className: "", html: '<div class="you-dot"></div>', iconSize: [18, 18] }),
        zIndexOffset: 1000,
      }).addTo(map).bindPopup("You are here");
      map.setView([S.here.lat, S.here.lng], 9);
      $("#btn-locate").innerHTML = "◎ Located";
      renderAll();
    },
    () => { $("#btn-locate").innerHTML = "◎ Locate me"; alert("Couldn't get your location. Check browser permissions."); },
    { enableHighAccuracy: false, timeout: 12000 });
}
$("#btn-locate").addEventListener("click", locate);

// Suggest button
$("#btn-suggest").addEventListener("click", suggestToday);

// Compare: share & clear (Bonus feature #2: shareable shortlist link)
$("#btn-share").addEventListener("click", async () => {
  const ids = S.compare.size ? [...S.compare] : [...FAVS];
  if (!ids.length) { alert("Pick some courses to compare (or favorite a few) first."); return; }
  const url = `${location.origin}${location.pathname}?list=${ids.join(",")}`;
  try {
    if (navigator.share) await navigator.share({ title: "Golf shortlist", url });
    else { await navigator.clipboard.writeText(url); alert("Link copied! Send it to your foursome."); }
  } catch { /* user cancelled share sheet */ }
});
$("#btn-clear-cmp").addEventListener("click", () => { S.compare.clear(); renderAll(); });

// Shared-list banner
$("#btn-clear-share").addEventListener("click", () => {
  S.shareList = null;
  history.replaceState(null, "", location.pathname);
  $("#share-banner").classList.add("hidden");
  renderAll();
});

// Savings form
$("#savings-form").addEventListener("submit", (e) => {
  e.preventDefault();
  LOG.unshift({
    course: $("#log-course").value,
    date: $("#log-date").value,
    program: $("#log-program").value,
    fee: $("#log-fee").value,
    saved: $("#log-saved").value,
  });
  store.set("log", LOG);
  e.target.reset();
  renderSavings();
});

// Sheet close
$("#sheet-backdrop").addEventListener("click", closeSheet);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });

/* ------------------------------------------------------------------ */
/* 7. Boot                                                             */
/* ------------------------------------------------------------------ */

function showDataError() {
  $("#course-list").innerHTML =
    `<div class="empty">Couldn't find the course data file (<code>courses.js</code>).<br>
     Make sure <code>courses.js</code> is uploaded in the same place as
     <code>index.html</code> (either next to it, or in a <code>data</code> folder).
     See the README.</div>`;
}

// Where the data file might live. The app tries these in order, so it works
// whether courses.js is inside a data/ folder or sitting next to index.html
// (GitHub's drag-and-drop uploader often flattens folders).
const DATA_PATHS = ["data/courses.js", "courses.js"];

function loadDataFrom(i) {
  if (i >= DATA_PATHS.length) return showDataError();
  const s = document.createElement("script");
  s.src = DATA_PATHS[i];
  s.onload = () => (window.GVM_DATA ? boot() : loadDataFrom(i + 1));
  s.onerror = () => loadDataFrom(i + 1);
  document.head.appendChild(s);
}

function boot() {
  // Course data (window.GVM_DATA) normally comes from a <script> tag in
  // index.html. If it isn't there — an older index.html, or the data file ended
  // up in a different folder — load it ourselves, trying each known location.
  // A <script> element works even when the page is opened straight from disk.
  const data = window.GVM_DATA;
  if (!data || !Array.isArray(data.courses)) {
    return loadDataFrom(0);
  }
  S.meta = data.meta;
  S.courses = data.courses;
  buildMarkers();
  fillLogCourses();
  // Shared shortlist link? (?list=id1,id2)
  const params = new URLSearchParams(location.search);
  if (params.get("list")) {
    const ids = params.get("list").split(",").filter((id) => S.courses.some((c) => c.id === id));
    if (ids.length) {
      S.shareList = ids;
      ids.forEach((id) => S.compare.size < 4 && S.compare.add(id));
      $("#share-count").textContent = ids.length;
      $("#share-banner").classList.remove("hidden");
    }
  }
  renderAll();
  // Markers are on the map now; make sure Leaflet has the true container size
  // so they land in the visible area on the first paint.
  fixMapSize();
  setTimeout(fixMapSize, 100);
}
boot();
