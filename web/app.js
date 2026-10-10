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
const LEVEL_LABEL = { low: "Low", medium: "Medium", high: "High", critical: "Critical" };
const LEVEL_RANK = { low: 0, medium: 1, high: 2, critical: 3 };
const NORMAL_COLOR = "#3fb6a8";
const PATROL_COLOR = "#60a5fa";
const PATROL_TYPE = "patrol";      // ship_type al unităților de patrulare în timeline (scris de core)
const DARK_COLOR = "#8b9bb0";
const FLASH_SCORE = 90;        // AFIȘARE: alertele cu scor peste această valoare clipesc în roșu (nu e prag de detecție)
const FLASH_MS = 350;          // perioada clipirii
const SIM_TAG = '<span class="tag-sim">SIMULATED</span>';
const INFRA_STYLE = {
  pipeline: { color: "#f0a050", weight: 3 },
  cable: { color: "#b48af0", weight: 2, dashArray: "6 4" },
  anchorage: { color: "#4f8fd6", weight: 1, fillOpacity: 0.08 },
  port_approach: { color: "#8b9bb0", weight: 1, fillOpacity: 0.06, dashArray: "3 3" },
};
// Infrastructura reală de referință (assets/reference_infrastructure.geojson): doar afișare, nu intră în scor.
const REF_STYLE = {
  pipeline: { color: "#f0a050", weight: 3, opacity: 0.7, dashArray: "10 5" },
  power_cable: { color: "#f2d94e", weight: 3, opacity: 0.8, dashArray: "2 6", lineCap: "round" },
  data_cable: { color: "#5fd3e8", weight: 2, opacity: 0.8, dashArray: "6 4" },
  eez_boundary: { color: "#e5484d", weight: 2, opacity: 0.7, dashArray: "12 6 2 6" },
  license_block: { color: "#9fe870", weight: 1, opacity: 0.6, fillColor: "#9fe870", fillOpacity: 0.06 },
};
const REF_POINT = { platform: "#f0a050", port: "#4f8fd6", security_hub: "#3fb6a8", naval_base: "#f472b6" };

// Rețeaua națională extinsă de 18 hidrofoane submarine (acoperire completă ZEE Marea Neagră)
const ALL_HYDROPHONES = [
  // Linia 1: Supraveghere Infrastructură Critică & Contacte Scenariu
  {
    id: "HYD-1",
    name: "Ana Gas Platform (Dark Transit)",
    lat: 44.265, lon: 29.490,
    offsetSec: 8700, // 08:25 UTC
    clip: "lowfreq_tone.png",
    sig: "propeller",
    freq: 50,
    badgeText: "Propeller 50 Hz",
    badgeClass: "badge-propeller",
    summary: "Propeller cavitation, cargo ship without AIS",
    hasContact: true,
    realtimeText: "SONAR ALERT: Strong propeller cavitation (50 Hz fundamental + 100 Hz harmonic). RMS intensity: 0.21, low-energy ratio: 0.965. Confirms a vessel under way near the platform.",
  },
  {
    id: "HYD-3",
    name: "Subsea Communications Cable (Sabotage)",
    lat: 44.180, lon: 29.400,
    offsetSec: 13800, // 09:50 UTC
    clip: "anchor_drag.png",
    sig: "anchor_chain",
    freq: 120,
    badgeText: "Anchor Chain 120 Hz",
    badgeClass: "badge-chain",
    summary: "Anchor chain dragged across the subsea cable",
    hasContact: true,
    realtimeText: "CRITICAL SABOTAGE ALERT: Metallic scraping and rattling signature on the seabed at 120 Hz. Correlates with the fibre-optic cable vibration sensor!",
  },
  {
    id: "HYD-4",
    name: "North Perimeter (Suspicious Loitering Fishing Vessel)",
    lat: 44.380, lon: 29.620,
    offsetSec: 18000, // 11:00 UTC
    clip: "engine_rumble.png",
    sig: "propeller",
    freq: 65,
    badgeText: "Engine 65 Hz",
    badgeClass: "badge-propeller",
    summary: "Auxiliary engine of loitering vessel (Northern Dawn)",
    hasContact: true,
    realtimeText: "ACOUSTIC CONTACT: Low-RPM auxiliary diesel engine rumble (65 Hz). Correlated with the fishing vessel loitering in the area.",
  },
  {
    id: "HYD-2",
    name: "Outer Perimeter (Background Noise Control)",
    lat: 44.450, lon: 29.950,
    offsetSec: 2700, // 06:45 UTC
    clip: "background_noise.png",
    sig: "ambient",
    freq: 0,
    badgeText: "Background Noise (0 FA)",
    badgeClass: "badge-ambient",
    summary: "Normal ambient sea noise",
    hasContact: true,
    realtimeText: "Signal captured: broadband ocean noise (normal sea state). Estimated background level: 0.09. Adaptive filter active, no false alarm raised.",
  },

  // Linia 2: Bariera Costieră Litoral (Sud -> Nord)
  { id: "HYD-5", name: "Mangalia South (Maritime Border)", lat: 43.780, lon: 28.750, summary: "Southern coastal surveillance", hasContact: false },
  { id: "HYD-6", name: "Vama Veche Coastal", lat: 43.680, lon: 28.680, summary: "Shallow-water acoustic sensor", hasContact: false },
  { id: "HYD-7", name: "Agigea / Constanța South", lat: 44.080, lon: 28.820, summary: "Agigea port entrance protection", hasContact: false },
  { id: "HYD-8", name: "Constanța Port Approach Corridor", lat: 44.150, lon: 28.980, summary: "Commercial shipping lane", hasContact: false },
  { id: "HYD-9", name: "Cape Midia Oil Terminal", lat: 44.330, lon: 28.780, summary: "Midia terminal infrastructure monitoring", hasContact: false },
  { id: "HYD-10", name: "Periboina / Gura Portiței", lat: 44.520, lon: 29.050, summary: "Lagoon acoustic barrier", hasContact: false },
  { id: "HYD-11", name: "Sfântu Gheorghe South (Delta)", lat: 44.750, lon: 29.450, summary: "Sfântu Gheorghe branch", hasContact: false },
  { id: "HYD-12", name: "Sulina North Commercial Lane", lat: 44.920, lon: 29.820, summary: "Sulina channel exit (grain traffic)", hasContact: false },

  // Linia 3: Perimetru Offshore & ZEE Est (Ape Adânci)
  { id: "HYD-13", name: "Lebăda / Sinoe East Platform", lat: 44.480, lon: 29.800, summary: "OMV oil production cluster", hasContact: false },
  { id: "HYD-14", name: "Subsea Cable Deep Segment", lat: 44.220, lon: 30.150, summary: "Data cable route to the Caucasus", hasContact: false },
  { id: "HYD-15", name: "Midia Offshore Subsea Pipeline", lat: 44.380, lon: 29.150, summary: "Gas pipeline mid segment", hasContact: false },
  { id: "HYD-16", name: "EEZ South-East Outpost", lat: 44.100, lon: 30.500, summary: "Autonomous EEZ hydrophone buoy", hasContact: false },
  { id: "HYD-17", name: "EEZ Central-East Outpost", lat: 44.400, lon: 30.650, summary: "Deep-water early warning", hasContact: false },
  { id: "HYD-18", name: "EEZ North-East Outpost", lat: 44.750, lon: 30.700, summary: "Maritime perimeter towards Snake Island", hasContact: false },
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
  tracks: [], alerts: [], gapsByMmsi: {}, sensors: [], units: {}, unitByMmsi: {},
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
  reference: L.layerGroup().addTo(map),
  infra: L.layerGroup().addTo(map),
  units: L.layerGroup().addTo(map),     // bazele (fixe) + patrolLive (redesenat la fiecare tick)
  hydroStations: L.layerGroup().addTo(map),
  hydroCoverage: L.layerGroup().addTo(map),
  sensors: L.layerGroup().addTo(map),
  trails: L.layerGroup().addTo(map),
  uncertainty: L.layerGroup().addTo(map),
  vessels: L.layerGroup().addTo(map),
};
const patrolLive = L.layerGroup().addTo(layers.units);
L.control.layers(null, {
  "Real infrastructure (reference, approx.)": layers.reference,
  "Demo infrastructure (approx.)": layers.infra,
  "Patrol units (simulated)": layers.units,
}, { position: "topright", collapsed: false }).addTo(map);

const legend = L.control({ position: "bottomleft" });
legend.onAdd = () => {
  const d = L.DomUtil.create("div", "legend");
  d.innerHTML =
    `<div class="legend-head">Vessels and alerts</div>` +
    `<div><i style="background:${NORMAL_COLOR}"></i>Normal vessel</div>` +
    `<div><i style="background:${DARK_COLOR}"></i>AIS off (uncertainty area)</div>` +
    `<div><i class="legend-patrol"></i>Patrol vessel (simulated) · dashed line = dispatched</div>` +
    `<div><i class="legend-base"></i>Patrol base</div>` +
    Object.entries(LEVEL_COLOR).map(([k, c]) => `<div><i style="background:${c}"></i>${LEVEL_LABEL[k]} alert</div>`).join("") +
    `<div class="legend-head">Demo infrastructure</div>` +
    `<div><i style="background:#f0a050"></i>Pipeline</div><div><i style="background:#b48af0"></i>Subsea cable</div>` +
    `<div><i style="background:#a855f7; border-radius:50%"></i>Hydrophone (acoustic detector)</div>` +
    `<div class="legend-head">Reference (display only)</div>` +
    `<div><i class="dot" style="border-color:#f0a050"></i>Oil / gas platform</div>` +
    `<div><i style="background:#f0a050"></i>Gas pipeline</div>` +
    `<div><i style="background:#f2d94e"></i>Power cable</div>` +
    `<div><i style="background:#5fd3e8"></i>Data cable</div>` +
    `<div><i class="dot" style="border-color:#4f8fd6"></i>Port · <i class="dot" style="border-color:#3fb6a8"></i>Security hub</div>` +
    `<div><i class="dot" style="border-color:#f472b6"></i>Naval base / range</div>` +
    `<div><i style="background:#e5484d"></i>Romanian EEZ boundary</div>` +
    `<div><i style="background:rgba(159,232,112,.25); border:1px solid #9fe870"></i>Oil / gas licence block</div>`;
  return d;
};
legend.addTo(map);

// Clipirea e legată de un ceas global, nu de animații CSS: lista se reconstruiește la fiecare tick.
setInterval(() => document.body.classList.toggle("flash-on"), FLASH_MS);

function refTooltip(p) {
  return `<b>${esc(p.name)}</b>` + (p.group ? `<br>${esc(p.group)}` : "") +
    (p.note ? `<br>${esc(p.note)}` : "") + "<br><i>Reference only, not scored</i>";
}

async function loadAssets() {
  try {
    const ref = await SeaGridLoader.fetchJSON(ASSETS + "reference_infrastructure.geojson");
    // Poligoanele (blocuri de licență) primele, ca să rămână sub linii și puncte.
    ref.features.sort((a, b) => (b.geometry.type === "Polygon") - (a.geometry.type === "Polygon"));
    L.geoJSON(ref, {
      style: (f) => REF_STYLE[f.properties.kind] || { color: "#ccc", weight: 2, dashArray: "4 4" },
      pointToLayer: (f, ll) => L.circleMarker(ll, {
        radius: 6, color: REF_POINT[f.properties.kind] || "#ccc", weight: 2, fillColor: "#16212d", fillOpacity: 1,
      }),
      onEachFeature: (f, l) => l.bindTooltip(refTooltip(f.properties), { sticky: true }),
    }).addTo(layers.reference);
  } catch (e) { console.warn(e); }
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
      if (u.mmsi) S.unitByMmsi[u.mmsi] = u;
      L.marker([u.lat, u.lon], { icon: L.divIcon({ className: "patrol-base", iconSize: [12, 12] }), title: u.base || u.name })
        .bindTooltip(`<b>Base: ${esc(u.base || "?")}</b><br>Home of ${esc(u.name)}${u.simulated ? "<br>SIMULATED" : ""}`)
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
  $("status").textContent = `mode ${tl.mode} · now ${fmtTime(S.end)}`;

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
    // Estompate intenționat: rețeaua de hidrofoane e context, nu trebuie să acopere navele și alertele.
    L.circle([h.lat, h.lon], {
      radius: 15000, color: stCol, weight: 1, opacity: isContact ? 0.45 : 0.12, dashArray: "5 5",
      fillOpacity: isContact ? 0.05 : 0.008, interactive: false,
    }).addTo(layers.hydroCoverage);

    // Marker hidrofon fix (text curat în tooltip, fără imagini care dispar la drag)
    L.circleMarker([h.lat, h.lon], {
      radius: isContact ? 7 : 4, color: isContact ? "#ffffff" : stCol, weight: isContact ? 1.5 : 1, opacity: isContact ? 0.9 : 0.35,
      fillColor: stCol, fillOpacity: isContact ? 0.85 : 0.2,
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
    if (v.ship_type === PATROL_TYPE) continue;
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
        .bindTooltip(`Uncertainty area: ${radiusKm.toFixed(1)} km`)
        .addTo(layers.uncertainty);
    }
    L.circleMarker([p.lat, p.lon], {
      radius: level ? 8 : 5, color: gap ? DARK_COLOR : "#0b1118", weight: gap ? 2 : 1,
      dashArray: gap ? "2 2" : null, fillColor: color, fillOpacity: gap ? 0.2 : 0.95,
    })
      .bindTooltip(
        `<b>${esc(v.name || "Unknown vessel")}</b> · MMSI ${v.mmsi}<br>${p.sog ?? "?"} kn · ${p.cog ?? "?"}°` +
        `${gap ? "<br>AIS off since " + fmtTime(gap.s) : ""}${v.simulated ? "<br>SIMULATED" : ""}`)
      .on("click", () => { const a = active.find((x) => x.a.mmsi === v.mmsi); if (a) select(a.a.alert_id); })
      .addTo(layers.vessels);
    if (sel && sel.mmsi === v.mmsi) {
      const from = lastIndexLE(v.times, t - TRAIL_MIN * 60000);
      const pts = v.points.slice(Math.max(0, from), i + 1).map((q) => [q.lat, q.lon]);
      L.polyline(pts, { color: LEVEL_COLOR[level] || NORMAL_COLOR, weight: 2, opacity: 0.8 }).addTo(layers.trails);
    }
  }

  renderPatrols(t, active);

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
      const labelText = `<b>SONAR CONTACT (HYDROPHONE): ${esc(e.sensor_id)}</b><br>${sig} · Confidence ${(e.confidence * 100).toFixed(0)}%<br><i>Click for the detailed report</i>`;

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
      const note = e.metrics && e.metrics.note ? e.metrics.note : "cable vibration";
      const isNearShore = note.includes("shore") || Number(km) < 15;
      const colFibre = isNearShore ? "#38bdf8" : "#f97316";

      let descText = "";
      if (isNearShore) {
        descText = `<span style="color:#93c5fd;">ℹ️ <b>Coastal mechanical noise</b> (waves/traffic at km ${km} near shore). Harmless, no threat.</span>`;
      } else {
        descText = `<span style="color:#f87171;">⚠️ <b>Strong mechanical vibration on the cable</b> (suspected subsea sabotage!).</span>`;
      }

      const labelText =
        `<b>FIBRE-OPTIC SENSOR (DAS)</b> · ${esc(e.metrics.cable_id || "CABLE-1")}<br>` +
        `Position: km <b>${km}</b> from shore<br>` +
        `${descText}<br>` +
        `Amplitude: ${e.metrics.amplitude ?? "?"} · Confidence: ${(e.confidence * 100).toFixed(0)}%`;

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
      `<br><button type="button" class="btn-mini" style="margin-top:6px;" onclick="openSonarModal(findHydro('${activeHyd.id}'))">Open Spectrogram</button>`;
  } else {
    $("audio-status-text").innerHTML =
      `At this time (${fmtTime(t)}) only the <i>natural background noise of the Black Sea</i> is being captured. No suspicious vessel or abnormal acoustic activity recorded.`;
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
    <li data-id="${a.alert_id}" data-score="${Math.floor(st.score)}" class="${a.alert_id === S.selected ? "selected" : ""} ${st.score > FLASH_SCORE ? "flash" : ""}">
      <span class="chip lvl-${st.level}"></span>
      <span>${esc(a.vessel_name || a.mmsi)}${a.simulated ? SIM_TAG : ""}</span>
      <span class="score">${st.score}</span>
      <span class="sub">${esc(a.alert_type)} · level ${LEVEL_LABEL[st.level]} · since ${fmtTime(a.created)}</span>
    </li>`).join("");

  for (const li of $("alert-list").querySelectorAll("li")) li.onclick = () => select(li.dataset.id);
}

// Unitățile de patrulare: poziția vine din pista lor din timeline; misiunea și ETA-ul din istoricul alertei
// (ScorePoint.unit_id / eta_min). Nimic nu se calculează aici.
function renderPatrols(t, active) {
  patrolLive.clearLayers();
  const missionByUnit = {};
  for (const { a, st } of active) if (st.unit_id) missionByUnit[st.unit_id] = { a, st };
  // Ținta afișată: poziția navei la t (din pista ei), altfel poziția alertei.
  const targetOf = (a) => {
    const v = S.tracks.find((x) => x.mmsi === a.mmsi && x.ship_type !== PATROL_TYPE);
    const k = v ? lastIndexLE(v.times, t) : -1;
    return k >= 0 ? [v.points[k].lat, v.points[k].lon] : [a.lat, a.lon];
  };
  for (const v of S.tracks) {
    if (v.ship_type !== PATROL_TYPE) continue;
    const i = lastIndexLE(v.times, t);
    if (i < 0) continue;
    const p = v.points[i];
    const u = S.unitByMmsi[v.mmsi];
    const m = u && missionByUnit[u.id];
    const from = lastIndexLE(v.times, t - TRAIL_MIN * 60000);
    L.polyline(v.points.slice(Math.max(0, from), i + 1).map((q) => [q.lat, q.lon]),
      { color: PATROL_COLOR, weight: 2, opacity: 0.45 }).addTo(patrolLive);
    let status = "Patrolling";
    if (m) {
      const onScene = m.st.eta_min === 0;
      const target = esc(m.a.vessel_name || m.a.mmsi);
      status = onScene ? `On scene: ${target}` : `Dispatched to ${target} · ETA ${m.st.eta_min.toFixed(0)} min`;
      if (!onScene) {
        L.polyline([[p.lat, p.lon], targetOf(m.a)], { color: PATROL_COLOR, weight: 2, dashArray: "6 6", opacity: 0.9 })
          .bindTooltip(`${esc(v.name)} → ${target} · ETA ${m.st.eta_min.toFixed(0)} min`, { sticky: true })
          .addTo(patrolLive);
      }
    }
    // Leaflet pune propriul transform pe icon, deci rombul e un element interior rotit.
    L.marker([p.lat, p.lon], { icon: L.divIcon({ className: `patrol-icon${m ? " on-mission" : ""}`, html: "<span></span>",
                                                iconSize: [18, 18] }), zIndexOffset: 1000 })
      .bindTooltip(`<b>${esc(v.name)}</b><br>${status}<br>${p.sog ?? "?"} kn${v.simulated ? "<br>SIMULATED" : ""}`)
      .on("click", () => { if (m) select(m.a.alert_id); })
      .addTo(patrolLive);
  }
}

function renderDetail(t) {
  const a = S.alerts.find((x) => x.alert_id === S.selected);
  const st = a && a.created <= t ? stateAt(a, t) : null;
  $("detail").hidden = !st;
  if (!st) return;
  const factors = a.factors.filter((f) => ms(f.added_at) <= t);
  $("detail-title").innerHTML = `${esc(a.vessel_name || "Unknown vessel")} · ${st.score}/100 ${a.simulated ? SIM_TAG : ""}`;
  $("detail-meta").textContent =
    `MMSI ${a.mmsi} · level ${LEVEL_LABEL[st.level]} · onset ${fmtTime(ms(a.start_time))} · alert ${fmtTime(a.created)} · id ${a.alert_id}`;
  $("factors").innerHTML = factors.map((f) => `
    <div class="factor"><div class="row"><span>${esc(f.label)}${f.simulated ? SIM_TAG : ""}</span><b>+${f.points}</b></div>
    <div class="bar"><span style="width:${f.points}%"></span></div></div>`).join("") +
    `<div class="factor total"><div class="row"><span>Total (capped)</span><b>${st.score}</b></div>
     <div class="bar"><span style="width:${st.score}%"></span></div></div>`;

  $("detail-lines").innerHTML = factors.map((f) => {
    let extra = "";
    if (f.code === "acoustic_lowfreq") {
      extra = `
        <div style="background:#131c26; border:1px solid #3b2064; border-radius:6px; padding:8px; margin-top:6px;">
          <div style="color:#d8b4fe; font-size:11px; font-weight:700;">HYDROPHONE ACOUSTIC CONTACT: PROPELLER CAVITATION</div>
          <div style="color:var(--muted); font-size:11px; margin-top:2px;">Peak frequency: 50.0 Hz · Confidence: 98.3%</div>
          <button type="button" class="btn-mini" style="margin-top:5px;" onclick="openSonarModal(findHydro('HYD-1'))">View Sonar Spectrogram</button>
        </div>`;
    }
    return `<li>${esc(f.detail)}${extra}</li>`;
  }).join("");

  const u = st.unit_id && S.units[st.unit_id];
  $("recommendation").innerHTML = st.unit_id
    ? `<b>${esc(u ? u.name : st.unit_id)}</b> · ${st.eta_min === 0 ? "on scene" : `ETA ${st.eta_min.toFixed(0)} min`}` +
      `${u && u.simulated ? SIM_TAG : ""}`
    : "No unit recommended yet (below the alert threshold).";
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
  $("modal-title").textContent = `Sonar Analysis: ${hyd.id} — ${hyd.name}`;

  if (!hyd.hasContact) {
    $("modal-body").innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="badge" style="background:#0284c7; color:#fff; font-size:12px; padding:3px 10px;">STANDBY · NO CONTACT</span>
        <span style="color:var(--muted); font-size:12px;">Coordinates: ${hyd.lat.toFixed(3)}°N, ${hyd.lon.toFixed(3)}°E</span>
      </div>
      <div style="font-size:13px; margin-bottom:12px; color:#e2e8f0; line-height:1.4;">
        <b>Tactical Assessment:</b> Hydrophone operational in the Romanian EEZ early-warning network. No abnormal acoustic activity or propeller cavitation recorded within 15 km during the scenario.
      </div>
      <div style="background:#0b1118; border:1px dashed #334155; border-radius:6px; padding:24px 16px; text-align:center; color:var(--muted); font-size:12px; margin-bottom:12px;">
        <div style="color:#38bdf8; font-weight:700; margin-bottom:4px;">NORMAL AMBIENT LEVEL (SEA STATE 2)</div>
        Clean spectrum: natural background sea noise. Adaptive filter active, no anomaly detected.
      </div>
      <div class="modal-grid">
        <div class="modal-card">
          <b>Hydrophone Status</b>
          <span style="color:#38bdf8;">ACTIVE (STANDBY)</span>
        </div>
        <div class="modal-card">
          <b>Dominant Frequency</b>
          <span>N/A (diffuse noise)</span>
        </div>
        <div class="modal-card">
          <b>Low-Energy Ratio</b>
          <span>0.082 / 1.0 (below threshold)</span>
        </div>
        <div class="modal-card">
          <b>Current Adaptive Threshold</b>
          <span>0.60 (stable sea background)</span>
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
      <span style="color:var(--muted); font-size:12px;">Coordinates: ${hyd.lat.toFixed(3)}°N, ${hyd.lon.toFixed(3)}°E</span>
    </div>
    <div style="font-size:13px; margin-bottom:10px; color:#e2e8f0; line-height:1.4;">
      <b>Tactical Assessment:</b> ${esc(hyd.realtimeText)}
    </div>
    <div>
      <div style="font-size:11px; text-transform:uppercase; color:var(--muted); font-weight:700;">STFT Spectrogram (Spectral Density 10–500 Hz):</div>
      <img src="../out/spectrograms/${hyd.clip}" class="modal-spec-img" alt="Sonar spectrogram">
    </div>
    <div class="modal-grid">
      <div class="modal-card">
        <b>Signature Classification</b>
        <span style="color:${badgeColor}">${esc(hyd.sig.toUpperCase())}</span>
      </div>
      <div class="modal-card">
        <b>Dominant Frequency</b>
        <span>${hyd.freq > 0 ? hyd.freq + ".0 Hz" : "No peak (broadband noise)"}</span>
      </div>
      <div class="modal-card">
        <b>Low-Energy Ratio</b>
        <span>${hyd.freq > 0 ? "0.965 / 1.0 (above the 0.60 threshold)" : "0.094 (below threshold)"}</span>
      </div>
      <div class="modal-card">
        <b>Ambient Noise Threshold</b>
        <span>${hyd.freq > 0 ? "Base adaptive threshold: 0.60" : "Raised adaptive threshold: 0.65"}</span>
      </div>
    </div>
  `;

  modal.showModal();
}

function openFibreModal(e) {
  const modal = $("sonar-modal");
  if (!modal) return;
  const km = e.metrics && e.metrics.cable_km ? Number(e.metrics.cable_km).toFixed(1) : "?";
  const note = e.metrics && e.metrics.note ? e.metrics.note : "cable vibration";
  const isNearShore = note.includes("shore") || Number(km) < 15;

  $("modal-title").textContent = `Fibre-Optic Sensor (DAS): ${esc(e.sensor_id || "DAS-CABLE-1")}`;
  $("modal-body").innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <span class="badge" style="background:${isNearShore ? '#0284c7' : '#dc2626'}; color:#fff; font-size:12px; padding:3px 10px;">
        ${isNearShore ? "HARMLESS COASTAL NOISE" : "SUSPECTED SABOTAGE"}
      </span>
      <span style="color:var(--muted); font-size:12px;">Subsea Cable ${esc(e.metrics.cable_id || "CABLE-1")} · km ${km}</span>
    </div>
    <div style="font-size:13px; margin-bottom:12px; color:#e2e8f0; line-height:1.5;">
      <b>What does this signal at 06:30 mean?</b><br>
      ${isNearShore 
        ? "This is a <b>shore-side mechanical noise event</b> at km 8 off the Constanța coast. The subsea cable uses DAS (Distributed Acoustic Sensing). At km 8, at 06:30, the sensor recorded harmless noise from breaking waves or coastal fishing boats. The amplitude is very low (0.2) and the confidence only 30%, so the system <b>does NOT raise a security alert</b>." 
        : "Strong vibration on the offshore subsea cable. High amplitude consistent with physical contact or an anchor dragged across the cable."}
    </div>
    <div class="modal-grid">
      <div class="modal-card">
        <b>Sensor Type</b>
        <span>Subsea Fibre Optic (DAS)</span>
      </div>
      <div class="modal-card">
        <b>Position on Cable</b>
        <span>km ${km} from shore</span>
      </div>
      <div class="modal-card">
        <b>Vibration Amplitude</b>
        <span>${e.metrics.amplitude ?? "?"} (danger threshold: > 0.5)</span>
      </div>
      <div class="modal-card">
        <b>Detector Note</b>
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
  $("status").textContent = `Cannot load ${SeaGridLoader.SRC}: run make demo and serve the repo root.`;
  console.error(err);
});