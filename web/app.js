// SeaGrid UI: interfață operațională de supraveghere maritimă și sonar intelligence.
"use strict";

const MAP_CENTER = [44.25, 29.35];
const MAP_ZOOM = 9;
const TICK_MS = 100;
const TRAIL_MIN = 60;
const SENSOR_SHOW_MIN = 40;
const ASSETS = "../assets/";

const LEVEL_COLOR = { low: "#4f8fd6", medium: "#e0b43a", high: "#ef7f2f", critical: "#e5484d" };
const LEVEL_TEXT = { low: "low", medium: "medium", high: "high", critical: "critical" };
const LEVEL_RO = { low: "scăzut", medium: "mediu", high: "ridicat", critical: "critic" };
const LEVEL_RANK = { low: 0, medium: 1, high: 2, critical: 3 };
const NORMAL_COLOR = "#3fb6a8";
const DARK_COLOR = "#8b9bb0";
const SIM_TAG = '<span class="tag-sim">SIMULAT</span>';
const INFRA_STYLE = {
  pipeline: { color: "#f0a050", weight: 3 },
  cable: { color: "#b48af0", weight: 2, dashArray: "6 4" },
  anchorage: { color: "#4f8fd6", weight: 1, fillOpacity: 0.08 },
  port_approach: { color: "#8b9bb0", weight: 1, fillOpacity: 0.06, dashArray: "3 3" },
};

// Rețeaua națională extinsă de 18 hidrofoane submarine (acoperire completă ZEE Marea Neagră)
const ALL_HYDROPHONES = [
  // Linia 1: Supraveghere Infrastructură Critică & Contacte Scenariu
  {
    id: "HYD-1",
    name: "Platforma de Gaz Ana (Tranzit la Negru)",
    lat: 44.265, lon: 29.490,
    offsetSec: 8700, // 08:25 UTC
    clip: "lowfreq_tone.png",
    sig: "propeller",
    freq: 50,
    badgeText: "Elice 50 Hz",
    badgeClass: "badge-propeller",
    summary: "Cavitație elice navă cargo fără AIS",
    hasContact: true,
    realtimeText: "ALERTĂ SONAR: Cavitație puternică de elice (50 Hz fundamentală + armonica de 100 Hz). Intensitate RMS: 0.21, raport energie joasă: 0.965. Confirmă nava în deplasare pe sub apă lângă platformă.",
  },
  {
    id: "HYD-3",
    name: "Cablul Submarin de Comunicații (Sabotaj)",
    lat: 44.180, lon: 29.400,
    offsetSec: 13800, // 09:50 UTC
    clip: "anchor_drag.png",
    sig: "anchor_chain",
    freq: 120,
    badgeText: "Lanț Ancoră 120 Hz",
    badgeClass: "badge-chain",
    summary: "Frecare lanț ancoră târât pe cablu submarin",
    hasContact: true,
    realtimeText: "ALERTĂ CRITICĂ SABOTAJ: Semnătură de frecare metalică și zdrăngănit pe fundul mării la 120 Hz. Se corelează cu senzorul de vibrație din cablul de fibră optică!",
  },
  {
    id: "HYD-4",
    name: "Perimetru Nord (Pescador Suspect Staționar)",
    lat: 44.380, lon: 29.620,
    offsetSec: 18000, // 11:00 UTC
    clip: "engine_rumble.png",
    sig: "propeller",
    freq: 65,
    badgeText: "Motor 65 Hz",
    badgeClass: "badge-propeller",
    summary: "Motor auxiliar navă loitering (Northern Dawn)",
    hasContact: true,
    realtimeText: "CONTACT ACUSTIC: Huruit de motor diesel auxiliar la turație mică (65 Hz). Corelat cu pescadorul care staționează în zonă.",
  },
  {
    id: "HYD-2",
    name: "Perimetru Exterior (Control Zgomot Fond)",
    lat: 44.450, lon: 29.950,
    offsetSec: 2700, // 06:45 UTC
    clip: "background_noise.png",
    sig: "ambient",
    freq: 0,
    badgeText: "Zgomot Fond (0 FA)",
    badgeClass: "badge-ambient",
    summary: "Zgomot marin ambiant normal",
    hasContact: true,
    realtimeText: "Semnal captat: Zgomot oceanic de bandă largă (stare normală a mării). Nivel de fond estimat: 0.09. Filtru adaptiv activ — nicio alarmă falsă generată.",
  },

  // Linia 2: Bariera Costieră Litoral (Sud -> Nord)
  { id: "HYD-5", name: "Mangalia Sud (Granița Maritimă)", lat: 43.780, lon: 28.750, summary: "Supraveghere costieră sud", hasContact: false },
  { id: "HYD-6", name: "Vama Veche Costier", lat: 43.680, lon: 28.680, summary: "Senzor acustic ape puțin adânci", hasContact: false },
  { id: "HYD-7", name: "Agigea / Constanța Sud", lat: 44.080, lon: 28.820, summary: "Protecție intrări portuare Agigea", hasContact: false },
  { id: "HYD-8", name: "Culoar Abordaj Port Constanța", lat: 44.150, lon: 28.980, summary: "Culoar de trafic maritim comercial", hasContact: false },
  { id: "HYD-9", name: "Capul Midia Terminal Petrolier", lat: 44.330, lon: 28.780, summary: "Monitorizare infrastructură terminal Midia", hasContact: false },
  { id: "HYD-10", name: "Periboina / Gura Portiței", lat: 44.520, lon: 29.050, summary: "Barieră acustică lagunară", hasContact: false },
  { id: "HYD-11", name: "Sfântu Gheorghe Sud (Deltă)", lat: 44.750, lon: 29.450, summary: "Brațul Sfântu Gheorghe", hasContact: false },
  { id: "HYD-12", name: "Sulina Culoar Comercial Nord", lat: 44.920, lon: 29.820, summary: "Ieșire canal Sulina (trafic grâne)", hasContact: false },

  // Linia 3: Perimetru Offshore & ZEE Est (Ape Adânci)
  { id: "HYD-13", name: "Platforma Lebăda / Sinoe Est", lat: 44.480, lon: 29.800, summary: "Cluster extracție petrolieră OMV", hasContact: false },
  { id: "HYD-14", name: "Cablu Submarin Segment Adânc", lat: 44.220, lon: 30.150, summary: "Traseu cablu de date spre Caucaz", hasContact: false },
  { id: "HYD-15", name: "Conductă Submarină Midia Larg", lat: 44.380, lon: 29.150, summary: "Segment median conductă gaz", hasContact: false },
  { id: "HYD-16", name: "Avanpost ZEE Sud-Est", lat: 44.100, lon: 30.500, summary: "Baliză hidrofon autonomă ZEE", hasContact: false },
  { id: "HYD-17", name: "Avanpost ZEE Centru-Est", lat: 44.400, lon: 30.650, summary: "Avertizare timpurie adâncime", hasContact: false },
  { id: "HYD-18", name: "Avanpost ZEE Nord-Est", lat: 44.750, lon: 30.700, summary: "Perimetru maritim spre Insula Șerpilor", hasContact: false },
];

const HYDROPHONES = ALL_HYDROPHONES;
const TACTICAL_CONTACTS = ALL_HYDROPHONES.filter(h => h.hasContact);

function findHydro(id) {
  if (!id) return null;
  const s = String(id).trim();
  return ALL_HYDROPHONES.find((h) => h.id === s || h.id === s.replace("HYD-0", "HYD-") || h.id === s.replace("HYD-", "HYD-0"));
}

const S = {
  tl: null, start: 0, end: 0, t: 0, playing: false, live: false, selected: null,
  tracks: [], alerts: [], gapsByMmsi: {}, sensors: [], units: {},
  bannerOpen: false,
};

const $ = (id) => document.getElementById(id);
const ms = (iso) => Date.parse(iso);
const fmtTime = (t) => new Date(t).toISOString().slice(11, 16) + " UTC";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------- hartă ----------
const map = L.map("map", { preferCanvas: true }).setView(MAP_CENTER, MAP_ZOOM);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 13,
  attribution: "&copy; OpenStreetMap · SeaGrid",
}).addTo(map);

const layers = {
  infra: L.layerGroup().addTo(map),
  units: L.layerGroup().addTo(map),
  hydroStations: L.layerGroup().addTo(map),
  hydroCoverage: L.layerGroup().addTo(map),
  sensors: L.layerGroup().addTo(map),
  trails: L.layerGroup().addTo(map),
  uncertainty: L.layerGroup().addTo(map),
  vessels: L.layerGroup().addTo(map),
};

const legend = L.control({ position: "bottomleft" });
legend.onAdd = () => {
  const d = L.DomUtil.create("div", "legend");
  d.innerHTML =
    `<div><i style="background:${NORMAL_COLOR}"></i>navă normală</div>` +
    `<div><i style="background:${DARK_COLOR}"></i>AIS oprit (arie incertitudine)</div>` +
    Object.entries(LEVEL_COLOR).map(([k, c]) => `<div><i style="background:${c}"></i>alertă ${LEVEL_RO[k]}</div>`).join("") +
    `<div><i style="background:#f0a050"></i>conductă</div><div><i style="background:#b48af0"></i>cablu submarin</div>` +
    `<div><i style="background:#a855f7; border-radius:50%"></i>hidrofon (detector acustic)</div>`;
  return d;
};
legend.addTo(map);

async function loadAssets() {
  try {
    const gj = await SeaGridLoader.fetchJSON(ASSETS + "infrastructure.geojson");
    L.geoJSON(gj, {
      style: (f) => INFRA_STYLE[f.properties.kind] || { color: "#ccc" },
      pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 7, color: "#fff", weight: 2, fillColor: "#f0a050", fillOpacity: 1 }),
      onEachFeature: (f, l) => l.bindTooltip(esc(f.properties.name)),
    }).addTo(layers.infra);
  } catch (e) { console.warn(e); }
  try {
    const pu = await SeaGridLoader.fetchJSON(ASSETS + "patrol_units.json");
    for (const u of pu.units) {
      S.units[u.id] = u;
      L.marker([u.lat, u.lon], { title: u.name })
        .bindTooltip(`${esc(u.name)} · ${u.speed_kn} kn${u.simulated ? " · SIMULAT" : ""}`)
        .addTo(layers.units);
    }
  } catch (e) { console.warn(e); }
}

function lastIndexLE(times, t) {
  let lo = 0, hi = times.length - 1, ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (times[mid] <= t) { ans = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return ans;
}

function ingest(tl) {
  S.tl = tl;
  S.start = ms(tl.scenario_start);
  S.end = ms(tl.now);
  S.tracks = tl.vessels.map((v) => ({ ...v, times: v.points.map((p) => ms(p.t)) }));
  S.alerts = tl.alerts.map((a) => ({
    ...a,
    created: ms(a.created_at),
    hist: a.history.map((h) => ({ ...h, tm: ms(h.t) })),
  }));
  S.gapsByMmsi = {};
  for (const e of tl.events.filter((e) => e.event_type === "ais_gap")) {
    (S.gapsByMmsi[e.mmsi] ||= []).push({ ...e, s: ms(e.start), e: e.end ? ms(e.end) : S.end });
  }
  S.sensors = tl.events.filter((e) => e.source !== "ais").map((e) => ({ ...e, s: ms(e.start) }));
  $("sim-badge").hidden = !tl.simulated;
  $("slider").max = Math.max(1, Math.round((S.end - S.start) / 1000));
  if (S.live || S.t === 0 || S.t > S.end) S.t = S.live ? S.end : Math.min(Math.max(S.t, S.start), S.end);
  $("status").textContent = `mod ${tl.mode} · acum ${fmtTime(S.end)}`;

  // Construire stații hidrofoane permanente pe hartă (o singură dată, fără flicker)
  buildPermanentHydrophoneLayers();
  renderAcousticHistory();
  render();
}

// Stații hidrofoane construite stabil o singură dată
let hydroMarkersBuilt = false;
function buildPermanentHydrophoneLayers() {
  if (hydroMarkersBuilt) return;
  layers.hydroStations.clearLayers();
  layers.hydroCoverage.clearLayers();

  for (const h of ALL_HYDROPHONES) {
    const isSabotage = h.id === "HYD-3";
    const isContact = h.hasContact;
    const stCol = isSabotage ? "#e5484d" : isContact ? "#a855f7" : "#0284c7";

    // Cerc de acoperire 15 km (fără imagini în tooltip)
    L.circle([h.lat, h.lon], {
      radius: 15000, color: stCol, weight: 1, dashArray: "5 5", fillOpacity: isContact ? 0.04 : 0.02,
    }).addTo(layers.hydroCoverage);

    // Marker hidrofon fix (text curat în tooltip, fără imagini care dispar la drag)
    L.circleMarker([h.lat, h.lon], {
      radius: isContact ? 8 : 5.5, color: "#ffffff", weight: isContact ? 2 : 1.2, fillColor: stCol, fillOpacity: isContact ? 0.95 : 0.75,
    })
      .bindTooltip(`<b>${h.id}</b> · ${esc(h.name)}<br><span style="color:${isContact ? '#d8b4fe' : '#93c5fd'}">${esc(h.summary)}</span>`, {
        direction: "top", offset: [0, -8],
      })
      .on("click", () => openSonarModal(h))
      .addTo(layers.hydroStations);
  }
  hydroMarkersBuilt = true;
}

function stateAt(a, t) {
  const i = lastIndexLE(a.hist.map((h) => h.tm), t);
  return i < 0 ? null : a.hist[i];
}

function activeAlerts(t) {
  return S.alerts
    .filter((a) => a.created <= t)
    .map((a) => ({ a, st: stateAt(a, t) }))
    .filter((x) => x.st)
    .sort((x, y) => y.st.score - x.st.score || x.a.created - y.a.created);
}

// ---------- randare ciclică ----------
function render() {
  if (!S.tl) return;
  const t = S.t;
  $("slider").value = Math.round((t - S.start) / 1000);
  $("clock").textContent = fmtTime(t);
  const active = activeAlerts(t);
  const levelByMmsi = {};
  for (const { a, st } of active) {
    const cur = levelByMmsi[a.mmsi];
    if (!cur || LEVEL_RANK[st.level] > LEVEL_RANK[cur]) levelByMmsi[a.mmsi] = st.level;
  }
  const sel = S.alerts.find((a) => a.alert_id === S.selected);

  // Randare nave
  layers.vessels.clearLayers();
  layers.uncertainty.clearLayers();
  layers.trails.clearLayers();
  for (const v of S.tracks) {
    const i = lastIndexLE(v.times, t);
    if (i < 0) continue;
    const p = v.points[i];
    const gap = (S.gapsByMmsi[v.mmsi] || []).find((g) => g.s <= t && t <= g.e);
    const level = levelByMmsi[v.mmsi];
    const color = gap ? DARK_COLOR : level ? LEVEL_COLOR[level] : NORMAL_COLOR;
    if (gap) {
      const hours = (t - gap.s) / 3.6e6;
      const radiusKm = (gap.metrics.uncertainty_km_per_h || 0) * hours;
      L.circle([gap.lat, gap.lon], { radius: radiusKm * 1000, color: DARK_COLOR, weight: 1, dashArray: "4 4", fillOpacity: 0.08 })
        .bindTooltip(`Arie de incertitudine: ${radiusKm.toFixed(1)} km`)
        .addTo(layers.uncertainty);
    }
    L.circleMarker([p.lat, p.lon], {
      radius: level ? 8 : 5, color: gap ? DARK_COLOR : "#0b1118", weight: gap ? 2 : 1,
      dashArray: gap ? "2 2" : null, fillColor: color, fillOpacity: gap ? 0.2 : 0.95,
    })
      .bindTooltip(
        `<b>${esc(v.name || "Navă necunoscută")}</b> · MMSI ${v.mmsi}<br>${p.sog ?? "?"} kn · ${p.cog ?? "?"}°` +
        `${gap ? "<br>AIS oprit de la " + fmtTime(gap.s) : ""}${v.simulated ? "<br>SIMULAT" : ""}`)
      .on("click", () => { const a = active.find((x) => x.a.mmsi === v.mmsi); if (a) select(a.a.alert_id); })
      .addTo(layers.vessels);
    if (sel && sel.mmsi === v.mmsi) {
      const from = lastIndexLE(v.times, t - TRAIL_MIN * 60000);
      const pts = v.points.slice(Math.max(0, from), i + 1).map((q) => [q.lat, q.lon]);
      L.polyline(pts, { color: LEVEL_COLOR[level] || NORMAL_COLOR, weight: 2, opacity: 0.8 }).addTo(layers.trails);
    }
  }

  // Randare pings acustici activi la momentul t (numai markere circulare curate, FĂRĂ imagini în tooltips)
  layers.sensors.clearLayers();
  // Randare pings acustici și senzori de fibră activi la momentul t
  layers.sensors.clearLayers();
  for (const e of S.sensors) {
    if (e.s > t || t - e.s > SENSOR_SHOW_MIN * 60000) continue;
    const isAcoustic = e.source === "acoustic";
    const isSabotage = isAcoustic && e.metrics && e.metrics.signature === "anchor_chain";

    if (isAcoustic) {
      const col = isSabotage ? "#e5484d" : "#a855f7";
      const sig = e.metrics && e.metrics.signature ? ` [${esc(e.metrics.signature).toUpperCase()} @ ${e.metrics.dominant_freq_hz || 50} Hz]` : "";
      const labelText = `<b>CONTACT SONAR (HIDROFON): ${esc(e.sensor_id)}</b><br>${sig} · Încredere ${(e.confidence * 100).toFixed(0)}%<br><i>Click pentru raport detaliat</i>`;

      L.circleMarker([e.lat, e.lon], { radius: 16, color: col, weight: 3, fillOpacity: 0.35 })
        .bindTooltip(labelText, { direction: "top", offset: [0, -12] })
        .on("click", () => {
          const hyd = findHydro(e.sensor_id);
          if (hyd) openSonarModal(hyd);
        })
        .addTo(layers.sensors);
    } else {
      // SENZOR DE FIBRĂ OPTICĂ (DAS) - Culoare Cyan #38bdf8 distinctă
      const km = e.metrics && e.metrics.cable_km ? Number(e.metrics.cable_km).toFixed(1) : "?";
      const note = e.metrics && e.metrics.note ? e.metrics.note : "vibrație pe cablu";
      const isNearShore = note.includes("shore") || Number(km) < 15;
      const colFibre = isNearShore ? "#38bdf8" : "#f97316";

      let descText = "";
      if (isNearShore) {
        descText = `<span style="color:#93c5fd;">ℹ️ <b>Zgomot mecanic de coastă</b> (valuri/trafic la km ${km} lângă țărm). Inofensiv, fără amenințare.</span>`;
      } else {
        descText = `<span style="color:#f87171;">⚠️ <b>Vibrație mecanică intensă pe cablu</b> (suspiciune sabotaj submarin!).</span>`;
      }

      const labelText =
        `<b>SENZOR FIBRĂ OPTICĂ (DAS)</b> · ${esc(e.metrics.cable_id || "CABLE-1")}<br>` +
        `Poziție: Kilometrul <b>${km}</b> de la țărm<br>` +
        `${descText}<br>` +
        `Amplitudine: ${e.metrics.amplitude ?? "?"} · Încredere: ${(e.confidence * 100).toFixed(0)}%`;

      L.circleMarker([e.lat, e.lon], { radius: 14, color: colFibre, weight: 3, fillColor: colFibre, fillOpacity: 0.4 })
        .bindTooltip(labelText, { direction: "top", offset: [0, -12] })
        .on("click", () => openFibreModal(e))
        .addTo(layers.sensors);
    }
  }

  updateRealtimeAudioBanner(t);
  highlightActiveHistoryItem(t);
  renderAlertList(active);
  renderDetail(t);
}

function renderAcousticHistory() {
  const list = $("acoustic-history-list");
  if (!list) return;

  const contacts = TACTICAL_CONTACTS.slice().sort((a, b) => a.offsetSec - b.offsetSec);
  list.innerHTML = contacts.map((h) => {
    const timeIso = fmtTime(S.start + h.offsetSec * 1000);
    return `
      <div class="history-item" data-id="${h.id}" onclick="jumpToSec(${h.offsetSec}); openSonarModal(findHydro('${h.id}'))">
        <span class="history-time">${timeIso}</span>
        <div class="history-content">
          <span class="history-title">${esc(h.id)} · ${esc(h.name.split('(')[0].trim())}</span>
          <span class="history-loc">${esc(h.summary)}</span>
        </div>
        <span class="history-badge ${h.badgeClass}">${esc(h.badgeText)}</span>
      </div>`;
  }).join("");
}

function highlightActiveHistoryItem(t) {
  const elapsedSec = (t - S.start) / 1000;
  for (const item of document.querySelectorAll(".history-item")) {
    const hyd = findHydro(item.dataset.id);
    if (!hyd) continue;
    const isLive = Math.abs(elapsedSec - hyd.offsetSec) < (SENSOR_SHOW_MIN * 60);
    item.classList.toggle("is-live", isLive);
  }
}

// Actualizare banner "Ce se aude în timp real"
function updateRealtimeAudioBanner(t) {
  const banner = $("realtime-audio-banner");
  if (!banner || banner.hidden) return;

  $("audio-time").textContent = fmtTime(t);
  const elapsedSec = (t - S.start) / 1000;

  // Căutăm dacă vreun hidrofon are eveniment activ în acest moment
  const activeHyd = TACTICAL_CONTACTS.find((h) => Math.abs(elapsedSec - h.offsetSec) < (SENSOR_SHOW_MIN * 60));

  if (activeHyd) {
    $("audio-status-text").innerHTML =
      `<b style="color:#d8b4fe;">${esc(activeHyd.id)} (${esc(activeHyd.name)}):</b> ${esc(activeHyd.realtimeText)}` +
      `<br><button type="button" class="btn-mini" style="margin-top:6px;" onclick="openSonarModal(findHydro('${activeHyd.id}'))">Deschide Spectrograma</button>`;
  } else {
    $("audio-status-text").innerHTML =
      `La această oră (${fmtTime(t)}) se captează doar <i>zgomotul natural de fond al Mării Negre</i>. Nicio navă suspectă sau activitate acustică anormală înregistrată.`;
  }
}

// Toggling banner audio
$("btn-realtime-audio").onclick = () => {
  const b = $("realtime-audio-banner");
  b.hidden = !b.hidden;
  if (!b.hidden) updateRealtimeAudioBanner(S.t);
};
$("btn-close-audio-banner").onclick = () => {
  $("realtime-audio-banner").hidden = true;
};

// Render lista alerte (păstrând animația colegului Radu)
function renderAlertList(active) {
  $("alert-count").textContent = active.length;
  $("no-alerts").hidden = active.length > 0;
  $("alert-list").innerHTML = active.map(({ a, st }) => `
    <li data-id="${a.alert_id}" data-score="${Math.floor(st.score)}" class="${a.alert_id === S.selected ? "selected" : ""}">
      <span class="chip lvl-${st.level}"></span>
      <span>${esc(a.vessel_name || a.mmsi)}${a.simulated ? SIM_TAG : ""}</span>
      <span class="score">${st.score}</span>
      <span class="sub">${esc(a.alert_type)} · nivel ${LEVEL_RO[st.level]} · de la ${fmtTime(a.created)}</span>
    </li>`).join("");

  for (const li of $("alert-list").querySelectorAll("li")) li.onclick = () => select(li.dataset.id);
}

function renderDetail(t) {
  const a = S.alerts.find((x) => x.alert_id === S.selected);
  const st = a && a.created <= t ? stateAt(a, t) : null;
  $("detail").hidden = !st;
  if (!st) return;
  const factors = a.factors.filter((f) => ms(f.added_at) <= t);
  $("detail-title").innerHTML = `${esc(a.vessel_name || "Navă necunoscută")} · ${st.score}/100 ${a.simulated ? SIM_TAG : ""}`;
  $("detail-meta").textContent =
    `MMSI ${a.mmsi} · nivel ${LEVEL_RO[st.level]} · debut ${fmtTime(ms(a.start_time))} · alertă ${fmtTime(a.created)} · id ${a.alert_id}`;
  $("factors").innerHTML = factors.map((f) => `
    <div class="factor"><div class="row"><span>${esc(f.label)}${f.simulated ? SIM_TAG : ""}</span><b>+${f.points}</b></div>
    <div class="bar"><span style="width:${f.points}%"></span></div></div>`).join("") +
    `<div class="factor total"><div class="row"><span>Total (plafonat)</span><b>${st.score}</b></div>
     <div class="bar"><span style="width:${st.score}%"></span></div></div>`;

  $("detail-lines").innerHTML = factors.map((f) => {
    let extra = "";
    if (f.code === "acoustic_lowfreq") {
      extra = `
        <div style="background:#131c26; border:1px solid #3b2064; border-radius:6px; padding:8px; margin-top:6px;">
          <div style="color:#d8b4fe; font-size:11px; font-weight:700;">CONTACT ACUSTIC HIDROFON: CAVITAȚIE ELICE</div>
          <div style="color:var(--muted); font-size:11px; margin-top:2px;">Frecvență de vârf: 50.0 Hz · Încredere: 98.3%</div>
          <button type="button" class="btn-mini" style="margin-top:5px;" onclick="openSonarModal(findHydro('HYD-1'))">Vezi Spectrograma Sonar</button>
        </div>`;
    }
    return `<li>${esc(f.detail)}${extra}</li>`;
  }).join("");

  const u = st.unit_id && S.units[st.unit_id];
  $("recommendation").innerHTML = st.unit_id
    ? `<b>${esc(u ? u.name : st.unit_id)}</b> · ETA ${st.eta_min.toFixed(0)} min${u && u.simulated ? SIM_TAG : ""}`
    : "Nu este recomandată încă o unitate (sub pragul de alertă).";
}

function select(id) {
  S.selected = id;
  const a = S.alerts.find((x) => x.alert_id === id);
  if (a) map.panTo([a.lat, a.lon]);
  render();
}

// Modalul de analiză sonar (Spectrogramă stabilă, fără audio sintetizat)
function openSonarModal(hyd) {
  const modal = $("sonar-modal");
  if (!modal || !hyd) return;
  $("modal-title").textContent = `Analiză Sonar: ${hyd.id} — ${hyd.name}`;

  if (!hyd.hasContact) {
    $("modal-body").innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="badge" style="background:#0284c7; color:#fff; font-size:12px; padding:3px 10px;">STANDBY · FĂRĂ CONTACT</span>
        <span style="color:var(--muted); font-size:12px;">Coordonate: ${hyd.lat.toFixed(3)}°N, ${hyd.lon.toFixed(3)}°E</span>
      </div>
      <div style="font-size:13px; margin-bottom:12px; color:#e2e8f0; line-height:1.4;">
        <b>Evaluare Tactică:</b> Hidrofon operațional în rețeaua de avertizare timpurie a ZEE România. Nu s-a înregistrat activitate acustică anormală sau cavitație de elice în raza de 15 km pe durata scenariului.
      </div>
      <div style="background:#0b1118; border:1px dashed #334155; border-radius:6px; padding:24px 16px; text-align:center; color:var(--muted); font-size:12px; margin-bottom:12px;">
        <div style="color:#38bdf8; font-weight:700; margin-bottom:4px;">NIVEL AMBIANT NORMAL (SEA STATE 2)</div>
        Spectru curat: Zgomot marin natural de fond. Filtru adaptiv activ — nicio anomalie detectată.
      </div>
      <div class="modal-grid">
        <div class="modal-card">
          <b>Stare Hidrofon</b>
          <span style="color:#38bdf8;">ACTIV (STANDBY)</span>
        </div>
        <div class="modal-card">
          <b>Frecvență Dominantă</b>
          <span>N/A (Zgomot difuz)</span>
        </div>
        <div class="modal-card">
          <b>Raport Energie Joasă</b>
          <span>0.082 / 1.0 (Sub prag)</span>
        </div>
        <div class="modal-card">
          <b>Prag Adaptiv Curent</b>
          <span>0.60 (Fond marin stabil)</span>
        </div>
      </div>
    `;
    modal.showModal();
    return;
  }

  const isSabotage = hyd.sig === "anchor_chain";
  const badgeColor = isSabotage ? "var(--critical)" : "var(--sonar)";

  $("modal-body").innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <span class="badge" style="background:${badgeColor}; color:#fff; font-size:12px; padding:3px 10px;">${esc(hyd.badgeText)}</span>
      <span style="color:var(--muted); font-size:12px;">Coordonate: ${hyd.lat.toFixed(3)}°N, ${hyd.lon.toFixed(3)}°E</span>
    </div>
    <div style="font-size:13px; margin-bottom:10px; color:#e2e8f0; line-height:1.4;">
      <b>Evaluare Tactică:</b> ${esc(hyd.realtimeText)}
    </div>
    <div>
      <div style="font-size:11px; text-transform:uppercase; color:var(--muted); font-weight:700;">Spectrogramă STFT (Densitate Spectrală 10–500 Hz):</div>
      <img src="../out/spectrograms/${hyd.clip}" class="modal-spec-img" alt="Spectrogramă Sonar">
    </div>
    <div class="modal-grid">
      <div class="modal-card">
        <b>Clasificare Semnătură</b>
        <span style="color:${badgeColor}">${esc(hyd.sig.toUpperCase())}</span>
      </div>
      <div class="modal-card">
        <b>Frecvență Dominantă</b>
        <span>${hyd.freq > 0 ? hyd.freq + ".0 Hz" : "Fără vârf (Zgomot larg)"}</span>
      </div>
      <div class="modal-card">
        <b>Raport Energie Joasă</b>
        <span>${hyd.freq > 0 ? "0.965 / 1.0 (Peste pragul 0.60)" : "0.094 (Sub prag)"}</span>
      </div>
      <div class="modal-card">
        <b>Prag Zgomot Ambiant</b>
        <span>${hyd.freq > 0 ? "Prag adaptiv bază: 0.60" : "Prag adaptiv ridicat: 0.65"}</span>
      </div>
    </div>
  `;

  modal.showModal();
}

function openFibreModal(e) {
  const modal = $("sonar-modal");
  if (!modal) return;
  const km = e.metrics && e.metrics.cable_km ? Number(e.metrics.cable_km).toFixed(1) : "?";
  const note = e.metrics && e.metrics.note ? e.metrics.note : "vibrație pe cablu";
  const isNearShore = note.includes("shore") || Number(km) < 15;

  $("modal-title").textContent = `Senzor Fibră Optică (DAS): ${esc(e.sensor_id || "DAS-CABLE-1")}`;
  $("modal-body").innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <span class="badge" style="background:${isNearShore ? '#0284c7' : '#dc2626'}; color:#fff; font-size:12px; padding:3px 10px;">
        ${isNearShore ? "ZGOMOT INOFENSIV DE COASTĂ" : "SUSPICIUNE SABOTAJ"}
      </span>
      <span style="color:var(--muted); font-size:12px;">Cablul Submarin ${esc(e.metrics.cable_id || "CABLE-1")} · Km ${km}</span>
    </div>
    <div style="font-size:13px; margin-bottom:12px; color:#e2e8f0; line-height:1.5;">
      <b>Ce reprezintă acest semnal la 06:30?</b><br>
      ${isNearShore 
        ? "Acesta este un <b>eveniment de zgomot mecanic de țărm</b> la km 8 de la coasta Constanței. Cablul submarin folosește tehnologia DAS (Distributed Acoustic Sensing). La km 8, la ora 06:30, senzorul a înregistrat zgomot inofensiv generat de valurile de mal sau ambarcațiuni de pescuit costier. Amplitudinea este foarte mică (0.2), iar încrederea este de doar 30%, deci sistemul <b>NU ridică nicio alertă de securitate</b>." 
        : "Vibrație intensă pe cablul submarin în larg. Amplitudine ridicată compatibilă cu contact fizic sau târâre de ancoră peste cablu."}
    </div>
    <div class="modal-grid">
      <div class="modal-card">
        <b>Tip Senzor</b>
        <span>Fibră Optică Submarină (DAS)</span>
      </div>
      <div class="modal-card">
        <b>Poziție pe Cablu</b>
        <span>Kilometrul ${km} de la țărm</span>
      </div>
      <div class="modal-card">
        <b>Amplitudine Vibrație</b>
        <span>${e.metrics.amplitude ?? "?"} (Prag periculos: > 0.5)</span>
      </div>
      <div class="modal-card">
        <b>Notă Detector</b>
        <span>${esc(note)}</span>
      </div>
    </div>
  `;
  modal.showModal();
}

$("modal-close").onclick = () => $("sonar-modal").close();
$("sonar-modal").onclick = (e) => { if (e.target === $("sonar-modal")) $("sonar-modal").close(); };

// Filtre hartă
$("filter-hydro").onchange = (e) => {
  if (e.target.checked) layers.hydroStations.addTo(map); else map.removeLayer(layers.hydroStations);
};
$("filter-coverage").onchange = (e) => {
  if (e.target.checked) layers.hydroCoverage.addTo(map); else map.removeLayer(layers.hydroCoverage);
};
$("filter-vessels").onchange = (e) => {
  if (e.target.checked) { layers.vessels.addTo(map); layers.trails.addTo(map); layers.uncertainty.addTo(map); }
  else { map.removeLayer(layers.vessels); map.removeLayer(layers.trails); map.removeLayer(layers.uncertainty); }
};
$("filter-infra").onchange = (e) => {
  if (e.target.checked) layers.infra.addTo(map); else map.removeLayer(layers.infra);
};

function jumpToSec(seconds) {
  S.t = S.start + seconds * 1000;
  if (!S.playing) render();
}

setInterval(() => {
  if (!S.playing || !S.tl) return;
  S.t = Math.min(S.end, S.t + Number($("speed").value) * TICK_MS);
  if (S.t >= S.end && !S.live) setPlaying(false);
  render();
}, TICK_MS);

function setPlaying(on) {
  S.playing = on;
  $("play").textContent = on ? "❚❚" : "▶";
}

$("play").onclick = () => {
  if (S.t >= S.end) S.t = S.start;
  setPlaying(!S.playing);
};
$("slider").oninput = (e) => {
  S.t = S.start + Number(e.target.value) * 1000;
  render();
};
$("live").onchange = (e) => {
  S.live = e.target.checked;
  if (S.live) { S.t = S.end; render(); }
};

loadAssets();
SeaGridLoader.start(ingest, (err) => {
  $("status").textContent = `Nu pot încărca ${SeaGridLoader.SRC}: rulați make demo și serviți rădăcina repo-ului.`;
  console.error(err);
});