// SeaGrid UI: interfață operațională de supraveghere maritimă și sonar intelligence.
// Doar afișare: tot ce e detecție și scor vine din timeline.json.
"use strict";

// Constante de AFIȘARE (nu praguri de detecție).
const MAP_CENTER = [44.25, 29.35];
const MAP_ZOOM = 9;
const TICK_MS = 100;
const TRAIL_MIN = 60;          // cât din traseu desenăm pentru nava selectată
const SENSOR_SHOW_MIN = 40;    // cât timp rămâne vizibil un eveniment de senzor
const ASSETS = "../assets/";
const FLASH_SCORE = 90;        // alertele cu scor peste această valoare clipesc în roșu
const PULSE_SCORE = 90;        // pulsația discretă a lui Radu, de la această valoare în sus
const FLASH_MS = 350;          // perioada clipirii

const LEVEL_COLOR = { low: "#5b9be6", medium: "#e3b341", high: "#f08c3a", critical: "#f0525b" };
const LEVEL_LABEL = { low: "Low", medium: "Medium", high: "High", critical: "Critical" };
const LEVEL_RANK = { low: 0, medium: 1, high: 2, critical: 3 };
const NORMAL_COLOR = "#3fb6a8";
const PATROL_TYPE = "patrol";   // ship_type al unităților de patrulare în timeline (scris de core)
const DARK_COLOR = "#8195ab";
const SIM_TAG = '<span class="tag-sim">SIMULATED</span>';
const SCRIPT_TAG = '<span class="tag-sim tag-script">SCRIPTED</span>';
const INFRA_STYLE = {
  pipeline: { color: "#f0a050", weight: 3 },
  cable: { color: "#b48af0", weight: 2, dashArray: "6 4" },
  anchorage: { color: "#5b9be6", weight: 1, fillOpacity: 0.08 },
  port_approach: { color: "#8195ab", weight: 1, fillOpacity: 0.06, dashArray: "3 3" },
};
// Infrastructura reală de referință (assets/reference_infrastructure.geojson): doar afișare, nu intră în scor.
const REF_STYLE = {
  pipeline: { color: "#f0a050", weight: 3, opacity: 0.7, dashArray: "10 5" },
  power_cable: { color: "#f2d94e", weight: 3, opacity: 0.8, dashArray: "2 6", lineCap: "round" },
  data_cable: { color: "#5fd3e8", weight: 2, opacity: 0.8, dashArray: "6 4" },
  eez_boundary: { color: "#f0525b", weight: 2, opacity: 0.7, dashArray: "12 6 2 6" },
  license_block: { color: "#9fe870", weight: 1, opacity: 0.6, fillColor: "#9fe870", fillOpacity: 0.06 },
};
// Infrastructura cea mai apropiată de alerta selectată (din nearest_infrastructure, calculat de core).
// Ținte radar Sentinel-1, după comparația cu AIS (statusul îl calculează core; pagina doar îl afișează).
const RADAR_STATUS = {
  dark: { color: "#f0525b", label: "No AIS · AIS is received here" },
  dark_uncovered: { color: "#e3b341", label: "No AIS · reception unproven" },
  matched: { color: "#3fb6a8", label: "Matched to AIS" },
  fixed: { color: "#8195ab", label: "Fixed structure" },
  coastal: { color: "#8195ab", label: "Harbour / coastal clutter" },
  excluded: { color: "#8195ab", label: "Inside an exclusion zone" },
  unchecked: { color: "#b9c6d4", label: "Not checked: no AIS recorded at the image time" },
};
const RADAR_IMAGE_OPACITY = 0.8;
const SENTINEL_ATTRIBUTION = 'Radar: contains modified <a href="https://dataspace.copernicus.eu/">Copernicus Sentinel</a> data (ESA)';
const LIVE_FIT_MAX_ZOOM = 10;   // prima centrare pe date reale nu intră mai aproape de atât
const COVERAGE_STYLE = { stroke: false, fillColor: "#3fb6a8", fillOpacity: 0.07, interactive: false };  // canvas: stil direct
const INFRA_HIGHLIGHT = { color: "#ffe066", weight: 6, opacity: 1, fillOpacity: 0.18 };
const INFRA_HIGHLIGHT_RADIUS = 11;
const REF_POINT = { platform: "#f0a050", port: "#5b9be6", security_hub: "#3fb6a8", naval_base: "#f472b6" };

// Rețeaua națională extinsă de 18 hidrofoane submarine (acoperire completă ZEE Marea Neagră)
const ALL_HYDROPHONES = [
  // Linia 1: Supraveghere Infrastructură Critică & Contacte Scenariu
  {
    id: "HYD-1",
    name: "Ana Gas Platform (Dark Transit)",
    lat: 44.265, lon: 29.490,
    offsetSec: 8400, // 08:20 UTC
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

const TACTICAL_CONTACTS = ALL_HYDROPHONES.filter((h) => h.hasContact);

function findHydro(id) {
  if (!id) return null;
  const s = String(id).trim();
  return ALL_HYDROPHONES.find((h) => h.id === s || h.id === s.replace("HYD-0", "HYD-") || h.id === s.replace("HYD-", "HYD-0"));
}

const S = {
  tl: null, start: 0, end: 0, t: 0, playing: false, live: false, selected: null,
  tracks: [], alerts: [], gapsByMmsi: {}, sensors: [], units: {}, unitByMmsi: {},
  subs: [], subSensors: {}, tlAlerts: [], revealedAlerts: new Set(),
  infraGeo: null, infraById: {}, infraHighlight: null,
  userSelected: false,   // până la primul clic, panoul urmărește alerta cu scorul cel mai mare
  realData: false,       // timeline în modul live (AIS real): fără elementele scriptate ale scenariului demo
  fitted: false,         // harta s-a centrat o dată pe datele reale
  radar: [],             // trecerile Sentinel-1 din timeline (doar pe date reale)
  radarEvents: {},       // event_id -> eveniment radar (dovada factorilor sar_*)
  engaged: loadEngaged(), // alert_id -> { unitId, at }: confirmările operatorului (doar în această pagină)
};

// "Acknowledge & engage": decizia operatorului, nu a sistemului. Se ține doar în browser, pe id-ul stabil al alertei;
// scorul, nivelul și recomandarea rămân cele din timeline.
function loadEngaged() {
  try { return JSON.parse(localStorage.getItem("seagrid.engaged") || "{}"); } catch (e) { return {}; }
}
function saveEngaged() {
  try { localStorage.setItem("seagrid.engaged", JSON.stringify(S.engaged)); } catch (e) { /* stocare indisponibilă */ }
}
const ENGAGED_TAG = '<span class="tag-engaged">ENGAGED</span>';

// Numele unei alerte: nava AIS, sau ținta radar fără AIS.
const shortTarget = (id) => String(id || "").replace(/^S1(\w)_(\d{8})T(\d{4})\d*_\d+-/, "S1$1 $2 $3 #");
const alertName = (a) => a.vessel_name || a.mmsi || (a.target_id ? `Radar target ${shortTarget(a.target_id)}` : "Unknown vessel");
// Pagina arată doar ce știa sistemul la momentul t: o trecere radar există de la publicarea ei.
const radarPassAt = (t) => { let p = null; for (const r of S.radar) if (r.avail <= t) p = r; return p; };
const findTarget = (id) => { for (const r of S.radar) for (const x of r.targets) if (x.target_id === id) return { pass: r, target: x }; return null; };

// Elementele scenariului demo (hidrofoane și contacte submarine scriptate în pagină) nu au sens pe date reale.
const showsDemoExtras = () => !S.realData;
function setRealData(on) {
  if (S.realData === on) return;
  S.realData = on;
  for (const el of document.querySelectorAll("[data-demo-only]")) el.hidden = on;
  for (const el of document.querySelectorAll("[data-live-only]")) el.hidden = !on;
  for (const key of ["hydroStations", "hydroCoverage", "submarines"]) {
    if (on) map.removeLayer(layers[key]); else layers[key].addTo(map);
  }
}

const $ = (id) => document.getElementById(id);
const ms = (iso) => Date.parse(iso);
const fmtTime = (t) => new Date(t).toISOString().slice(11, 16) + " UTC";
const pct = (x) => (x == null ? "?" : `${(x * 100).toFixed(0)}%`);
const num = (x, d = 2) => (x == null || Number.isNaN(Number(x)) ? "?" : Number(x).toFixed(d));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Ultimul eveniment acustic (din timeline) al unui hidrofon; null dacă pipeline-ul nu a raportat nimic.
function hydroEvent(h) {
  const evs = S.sensors.filter((e) => e.source === "acoustic" && findHydro(e.sensor_id) === h);
  return evs.length ? evs[evs.length - 1] : null;
}
// Momentul contactului: din eveniment dacă există, altfel din scenariul scris în pagină.
function hydroTime(h) {
  const e = hydroEvent(h);
  return e ? e.s : S.start + (h.offsetSec || 0) * 1000;
}
// Evenimentul de fibră e lângă țărm dacă așa spune nota detectorului (nu decidem pragul în pagină).
const isNearShoreNote = (note) => /near shore|coastal/i.test(note || "");

// ---------- hartă ----------
// STUB: dalele OpenStreetMap cer internet; fără rețea harta rămâne goală, dar straturile SeaGrid se văd.
// Dalele sunt întunecate din CSS (.leaflet-tile-pane), ca harta să nu orbească lângă panourile închise.
const map = L.map("map", { preferCanvas: true, zoomControl: true }).setView(MAP_CENTER, MAP_ZOOM);
const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 13,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · SeaGrid: approximate infrastructure coordinates',
}).addTo(map);

// Fără internet (sală fără rețea): după câteva dale eșuate desenăm un contur de uscat aproximativ, ca harta să nu fie goală.
const OFFLINE_TILE_ERRORS = 4;
let tileErrors = 0;
let offlineShown = false;
tiles.on("tileerror", () => {
  if (++tileErrors < OFFLINE_TILE_ERRORS || offlineShown) return;
  offlineShown = true;
  map.createPane("land").style.zIndex = 250;   // peste dale (200), sub straturile SeaGrid (400+)
  SeaGridLoader.fetchJSON("coastline_approx.geojson").then((gj) => {
    L.geoJSON(gj, { renderer: L.svg({ pane: "land" }), interactive: false, style: { className: "offline-land", weight: 1 } }).addTo(map);
    map.attributionControl.addAttribution("Offline: approximate coastline");
  }).catch((err) => console.warn(err));
});

// Marcajele difuze (div-uri cu blur) stau în panouri proprii: hidrofoanele sub linii, unitățile peste ele.
map.createPane("glowLow").style.zIndex = 350;
map.createPane("glowHigh").style.zIndex = 450;
const glowIcon = (cls, size) => L.divIcon({ className: "", html: `<div class="${cls}"></div>`, iconSize: [size, size], iconAnchor: [size / 2, size / 2] });

const layers = {
  areaHydro: L.layerGroup(),
  radarImage: L.layerGroup(),
  coverage: L.layerGroup(),
  reference: L.layerGroup(),
  infra: L.layerGroup(),
  units: L.layerGroup(),
  hydroCoverage: L.layerGroup(),
  hydroStations: L.layerGroup(),
  sensors: L.layerGroup(),
  trails: L.layerGroup(),
  uncertainty: L.layerGroup(),
  vessels: L.layerGroup(),
  submarines: L.layerGroup(),
  routes: L.layerGroup(),
  radarTargets: L.layerGroup(),
};
for (const g of Object.values(layers)) g.addTo(map);

// Filtrele din antet sunt singura sursă de adevăr: fiecare checkbox listează straturile pe care le comandă.
for (const box of document.querySelectorAll(".map-filters input[data-layers]")) {
  box.addEventListener("change", () => {
    for (const key of box.dataset.layers.split(",")) {
      const g = layers[key.trim()];
      if (!g) continue;
      if (box.checked) g.addTo(map); else map.removeLayer(g);
    }
  });
}

const legend = L.control({ position: "bottomleft" });
legend.onAdd = () => {
  const d = L.DomUtil.create("div", "legend");
  L.DomEvent.disableClickPropagation(d);
  L.DomEvent.disableScrollPropagation(d);
  d.innerHTML =
    `<button type="button" class="legend-toggle" aria-expanded="true"><span class="caret">▾</span> Legend</button>` +
    `<div class="legend-body">` +
    `<div class="legend-head">Vessels and alerts</div>` +
    `<div><i style="background:${NORMAL_COLOR}"></i>Normal vessel</div>` +
    `<div><i style="background:${DARK_COLOR}"></i>AIS off (uncertainty area)</div>` +
    Object.entries(LEVEL_COLOR).map(([k, c]) => `<div><i style="background:${c}"></i>${LEVEL_LABEL[k]} alert</div>`).join("") +
    `<div><i class="glow-swatch"></i>Patrol unit (simulated) · dashed = dispatched, solid = engaged</div>` +
    `<div><i class="base-swatch"></i>Patrol base</div>` +
    `<div data-live-only hidden><i style="background:rgba(63,182,168,.35)"></i>AIS coverage (reception measured)</div>` +
    `<div data-radar-only hidden>` +
    `<div class="legend-head">Sentinel-1 radar</div>` +
    `<div><i class="radar-swatch strong" style="--c:#f0525b"></i>Target with no AIS (AIS received here)</div>` +
    `<div><i class="radar-swatch strong" style="--c:#e3b341"></i>Target with no AIS (reception unproven)</div>` +
    `<div><i class="radar-swatch" style="--c:#3fb6a8"></i>Target matched to AIS</div>` +
    `<div><i class="radar-swatch" style="--c:#8195ab"></i>Fixed structure / coastal clutter</div>` +
    `<div><i class="radar-swatch" style="--c:#b9c6d4"></i>Not checked (no AIS recorded then)</div>` +
    `</div>` +
    `<div data-demo-only>` +
    `<div class="legend-head">Sensors</div>` +
    `<div><i style="background:#a855f7; border-radius:50%"></i>Hydrophone with contact</div>` +
    `<div><i class="glow-swatch round"></i>Hydrophone on standby</div>` +
    `<div><i style="background:#f97316; border-radius:50%"></i>Fibre-optic (DAS) event</div>` +
    `<div><i class="glow-swatch sub"></i>Submerged contact (simulated)</div>` +
    `<div><i class="dot" style="border-color:#2dd4bf"></i>Magnetometer buoy (simulated)</div>` +
    `</div>` +
    `<div class="legend-head">Scored infrastructure</div>` +
    `<div><i class="dot" style="border-color:#fff; background:#f0a050"></i>Gas platform</div>` +
    `<div><i style="background:#f0a050"></i>Pipeline</div><div><i style="background:#b48af0"></i>Subsea cable</div>` +
    `<div class="legend-head">Reference (display only)</div>` +
    `<div><i class="dot" style="border-color:#f0a050"></i>Oil / gas platform</div>` +
    `<div><i style="background:#f0a050"></i>Gas pipeline</div>` +
    `<div><i style="background:#f2d94e"></i>Power cable</div>` +
    `<div><i style="background:#5fd3e8"></i>Data cable</div>` +
    `<div><i class="dot" style="border-color:#5b9be6"></i>Port · <i class="dot" style="border-color:#3fb6a8"></i>Security hub</div>` +
    `<div><i class="dot" style="border-color:#f472b6"></i>Naval base / range</div>` +
    `<div><i style="background:#f0525b"></i>Romanian EEZ boundary</div>` +
    `<div><i style="background:rgba(159,232,112,.25); border:1px solid #9fe870"></i>Oil / gas licence block</div>` +
    `</div>`;
  const btn = d.querySelector(".legend-toggle");
  const setCollapsed = (on) => {
    d.classList.toggle("collapsed", on);
    btn.setAttribute("aria-expanded", String(!on));
    btn.querySelector(".caret").textContent = on ? "▸" : "▾";
    try { localStorage.setItem("seagrid.legendCollapsed", on ? "1" : "0"); } catch (e) { /* stocare indisponibilă */ }
  };
  let saved = "0";
  try { saved = localStorage.getItem("seagrid.legendCollapsed") || "0"; } catch (e) { /* stocare indisponibilă */ }
  setCollapsed(saved === "1");
  btn.onclick = () => setCollapsed(!d.classList.contains("collapsed"));
  return d;
};
legend.addTo(map);

// Unitățile de patrulare (Chris, core/patrol.py): poziția vine din pista lor din timeline (ship_type "patrol"),
// misiunea și ETA-ul din istoricul alertei (unit_id / eta_min). Nimic nu se calculează aici.
// Excepție, doar pentru alerta SCRIPTATĂ a submarinului (care nu există în pipeline): din momentul redirecționării,
// unitatea e afișată pe drumul de la poziția ei de atunci spre contact, ajungând la ETA-ul scris în scenariu.
function trackPosAt(v, t) {
  const k = lastIndexLE(v.times, t);
  return k >= 0 ? [v.points[k].lat, v.points[k].lon] : null;
}

function renderPatrols(t, active) {
  layers.routes.clearLayers();
  // Misiunea curentă a fiecărei unități: cea mai recentă recomandare dintre alertele active.
  const missionByUnit = {};
  for (const { a, st } of active) {
    if (!st.unit_id) continue;
    const first = a.hist.find((h) => h.unit_id === st.unit_id);
    const since = first ? first.tm : a.created;
    const cur = missionByUnit[st.unit_id];
    if (!cur || since > cur.since) missionByUnit[st.unit_id] = { a, st, since, eta0: first ? first.eta_min : st.eta_min };
  }
  const targetOf = (a) => {
    if (a.scripted) return [a.lat, a.lon];
    const v = S.tracks.find((x) => x.mmsi === a.mmsi && x.ship_type !== PATROL_TYPE);
    return (v && trackPosAt(v, t)) || [a.lat, a.lon];
  };
  for (const v of S.tracks) {
    if (v.ship_type !== PATROL_TYPE) continue;
    let pos = trackPosAt(v, t);
    if (!pos) continue;
    const u = S.unitByMmsi[v.mmsi];
    const m = u && missionByUnit[u.id];
    let status = "Patrolling";
    let etaLeft = null;
    if (m) {
      const target = targetOf(m.a);
      if (m.a.scripted) {
        const from = trackPosAt(v, m.since) || pos;
        const f = Math.min(1, Math.max(0, (t - m.since) / Math.max(1, m.eta0 * 60000)));
        pos = [from[0] + (target[0] - from[0]) * f, from[1] + (target[1] - from[1]) * f];
        etaLeft = Math.round(m.eta0 * (1 - f));
      } else {
        etaLeft = m.st.eta_min;
      }
      const name = esc(alertName(m.a));
      const onScene = etaLeft === 0;
      status = (S.engaged[m.a.alert_id] ? "Engaged by operator · " : "") +
        (onScene ? `On scene: ${name}` : `Dispatched to ${name} · ETA ${Number(etaLeft).toFixed(0)} min${m.a.scripted ? " (scripted re-task)" : ""}`);
      if (!onScene) {
        const engaged = S.engaged[m.a.alert_id];
        L.polyline([pos, target], { color: engaged ? "#3fb6a8" : "#7cc4ff", weight: engaged ? 3 : 2, dashArray: engaged ? null : "6 6", opacity: 0.9 })
          .bindTooltip(`${esc(v.name)} → ${name} · ETA ${Number(etaLeft).toFixed(0)} min`, { sticky: true })
          .addTo(layers.routes);
      }
    } else {
      // Urma ultimei ore de patrulare, discretă
      const from = lastIndexLE(v.times, t - TRAIL_MIN * 60000);
      const i = lastIndexLE(v.times, t);
      L.polyline(v.points.slice(Math.max(0, from), i + 1).map((q) => [q.lat, q.lon]),
        { color: "#7cc4ff", weight: 2, opacity: 0.3, interactive: false }).addTo(layers.routes);
    }
    const p = v.points[lastIndexLE(v.times, t)];
    L.marker(pos, { icon: glowIcon(`glow-unit${m ? " on-mission" : ""}`, 26), pane: "glowHigh", keyboard: false })
      .bindTooltip(`<b>${esc(v.name)}</b><br>${status}<br>${p.sog ?? "?"} kn${v.simulated ? "<br>SIMULATED" : ""}`, { direction: "top", offset: [0, -12] })
      .on("click", () => { if (m) select(m.a.alert_id); })
      .addTo(layers.routes);
  }
}

// Clipirea e legată de un ceas global, nu de animații CSS: lista se reconstruiește la fiecare tick.
setInterval(() => document.body.classList.toggle("flash-on"), FLASH_MS);

function refTooltip(p) {
  return `<b>${esc(p.name)}</b>` + (p.group ? `<br><span class="muted">${esc(p.group)}</span>` : "") +
    (p.note ? `<br>${esc(p.note)}` : "") + "<br><i>Reference only, not scored</i>";
}

async function loadAssets() {
  // Fișierele se încarcă în paralel; un fișier lipsă nu le blochează pe celelalte.
  const [ref, subs] = await Promise.allSettled([
    SeaGridLoader.fetchJSON(ASSETS + "reference_infrastructure.geojson"),
    SeaGridLoader.fetchJSON(ASSETS + "simulated_submarine_contacts.json"),
  ]);
  if (subs.status === "fulfilled") {
    S.subs = subs.value.contacts || [];
    if (S.tl && showsDemoExtras()) S.alerts = S.tlAlerts.concat(scriptedAlerts());
    for (const m of subs.value.low_cost_sensors || []) {
      S.subSensors[m.id] = m;
      L.circleMarker([m.lat, m.lon], { radius: 5, color: "#2dd4bf", weight: 2, fillColor: "#2dd4bf", fillOpacity: 0.25 })
        .bindTooltip(`<b>${esc(m.name)}</b><br>${esc(m.note)}<br>SIMULATED`, { direction: "top", offset: [0, -6] })
        .addTo(layers.hydroStations);
    }
  } else console.warn(subs.reason);
  if (ref.status === "fulfilled") {
    const data = ref.value;
    // Poligoanele (blocuri de licență) primele, ca să rămână sub linii și puncte.
    data.features.sort((a, b) => (b.geometry.type === "Polygon") - (a.geometry.type === "Polygon"));
    L.geoJSON(data, {
      style: (f) => REF_STYLE[f.properties.kind] || { color: "#ccc", weight: 2, dashArray: "4 4" },
      pointToLayer: (f, ll) => L.circleMarker(ll, {
        // Umplutură translucidă în culoarea punctului: lizibilă și pe tema de noapte, și pe cea de zi.
        radius: 6, color: REF_POINT[f.properties.kind] || "#ccc", weight: 2,
        fillColor: REF_POINT[f.properties.kind] || "#ccc", fillOpacity: 0.3,
      }),
      onEachFeature: (f, l) => l.bindTooltip(refTooltip(f.properties), { sticky: true }),
    }).addTo(layers.reference);
  } else console.warn(ref.reason);
}

// Infrastructura punctată și unitățile de patrulare ale zonei rulate: assets/ pentru scenariul demo,
// timeline.area_assets în modul live (ex. assets/areas/varna). Se reîncarcă doar când se schimbă zona.
async function loadAreaAssets(base) {
  if (S.assetsBase === base) return;
  S.assetsBase = base;
  const [gj, pu, hy] = await Promise.allSettled([
    SeaGridLoader.fetchJSON(base + "infrastructure.geojson"),
    SeaGridLoader.fetchJSON(base + "patrol_units.json"),
    // Hidrofoanele SIMULATE ale zonei live (doar poziție și rază; nu există flux acustic real).
    base === ASSETS ? Promise.reject(new Error("demo hydrophones are scripted in the page")) : SeaGridLoader.fetchJSON(base + "hydrophones.json"),
  ]);
  if (S.assetsBase !== base) return;   // între timp a sosit un timeline din altă zonă
  layers.infra.clearLayers();
  layers.units.clearLayers();
  layers.areaHydro.clearLayers();
  if (hy.status === "fulfilled") {
    const rangeM = (hy.value.range_km || 15) * 1000;
    for (const h of hy.value.stations) {
      L.circle([h.lat, h.lon], { radius: rangeM, color: "#0284c7", weight: 1, opacity: 0.25, dashArray: "5 5", fillOpacity: 0.02, interactive: false })
        .addTo(layers.areaHydro);
      L.marker([h.lat, h.lon], { icon: glowIcon("glow-dot", 24), pane: "glowLow", keyboard: false })
        .bindTooltip(`<b>${esc(h.id)}</b> · ${esc(h.name)}<br><span class="tt-info">SIMULATED station · ${hy.value.range_km || 15} km range · no live acoustic feed</span>`,
          { direction: "top", offset: [0, -8] })
        .addTo(layers.areaHydro);
    }
  }
  S.infraGeo = null; S.infraById = {}; S.infraHighlight = null;
  S.units = {}; S.unitByMmsi = {};
  if (gj.status === "fulfilled") {
    S.infraGeo = L.geoJSON(gj.value, {
      style: (f) => INFRA_STYLE[f.properties.kind] || { color: "#ccc" },
      pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 7, color: "#fff", weight: 2, fillColor: "#f0a050", fillOpacity: 1 }),
      onEachFeature: (f, l) => {
        l.bindTooltip(esc(f.properties.name));
        if (f.properties.id) S.infraById[f.properties.id] = l;
      },
    }).addTo(layers.infra);
    if (S.tl) render();
  } else console.warn(gj.reason);
  if (pu.status === "fulfilled") {
    // Bazele sunt fixe; unitățile în mișcare se desenează din pistele din timeline (renderPatrols).
    for (const u of pu.value.units) {
      S.units[u.id] = u;
      if (u.mmsi) S.unitByMmsi[String(u.mmsi)] = u;
      L.marker([u.lat, u.lon], { icon: glowIcon("patrol-base", 14), keyboard: false })
        .bindTooltip(`<b>Base: ${esc(u.base || "?")}</b><br>Home of ${esc(u.name)}${u.simulated ? "<br>SIMULATED" : ""}`, { direction: "top", offset: [0, -8] })
        .addTo(layers.units);
    }
    if (S.tl) render(); // numele unităților apar în recomandare chiar dacă timeline-ul a sosit primul
  } else console.warn(pu.reason);
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
  S.tlAlerts = tl.alerts.map((a) => ({
    ...a,
    created: ms(a.created_at),
    hist: a.history.map((h) => ({ ...h, tm: ms(h.t) })),
  }));
  setRealData(tl.mode === "live");
  S.alerts = showsDemoExtras() ? S.tlAlerts.concat(scriptedAlerts()) : S.tlAlerts;
  S.gapsByMmsi = {};
  for (const e of tl.events.filter((e) => e.event_type === "ais_gap")) {
    (S.gapsByMmsi[e.mmsi] ||= []).push({ ...e, s: ms(e.start), e: e.end ? ms(e.end) : S.end });
  }
  S.sensors = tl.events.filter((e) => e.source === "acoustic" || e.source === "fibre").map((e) => ({ ...e, s: ms(e.start) }))
    .sort((a, b) => a.s - b.s);
  S.radar = (tl.radar_passes || []).map((r) => ({ ...r, avail: ms(r.available_at), acq: ms(r.acquired_at) }))
    .sort((a, b) => a.acq - b.acq);
  S.radarEvents = Object.fromEntries(tl.events.filter((e) => e.source === "sar").map((e) => [e.event_id, e]));
  for (const el of document.querySelectorAll("[data-radar-only]")) el.hidden = !S.radar.length;
  if (S.radar.length && !S.sentinelCredited) {
    S.sentinelCredited = true;
    map.attributionControl.addAttribution(SENTINEL_ATTRIBUTION);
  }
  $("sim-badge").hidden = !tl.simulated;
  $("live-badge").hidden = !S.realData;
  $("live-badge").textContent = `LIVE · REAL AIS${S.radar.length ? " + RADAR" : ""}${tl.area_name ? " · " + tl.area_name : ""}`;
  drawCoverage(tl.ais_coverage || []);
  loadAreaAssets(tl.area_assets ? "../" + tl.area_assets + "/" : ASSETS);
  if (S.realData && !S.fitted) {
    // Prima dată pe date reale: urmărim ultimul batch și centrăm harta pe zona unde se aude AIS.
    S.fitted = true;
    S.live = true;
    $("live").checked = true;
    // Navele văzute plus acoperirea învățată (la început, câteva celule lângă port).
    const ships = S.tracks.filter((v) => v.ship_type !== PATROL_TYPE && v.points.length)
      .map((v) => [v.points[v.points.length - 1].lat, v.points[v.points.length - 1].lon]);
    const box = coverageBounds(tl.ais_coverage || []);
    if (ships.length && box) box.extend(L.latLngBounds(ships));
    const fit = box || (ships.length > 1 ? L.latLngBounds(ships) : null);
    if (fit) map.fitBounds(fit, { padding: [20, 20], maxZoom: LIVE_FIT_MAX_ZOOM });
  }
  $("slider").max = Math.max(1, Math.round((S.end - S.start) / 1000));
  if (S.live || S.t === 0 || S.t > S.end) S.t = S.live ? S.end : Math.min(Math.max(S.t, S.start), S.end);
  $("status").textContent = `mode ${tl.mode} · batch ${tl.batch_index} · now ${fmtTime(S.end)}`;

  if (showsDemoExtras()) {
    buildHydrophoneLayers();
    renderAcousticHistory();
  }
  render();
}

// Acoperirea AIS vine din timeline (celule învățate de core din înregistrare); pagina doar le desenează.
let coverageKey = "";
function drawCoverage(cells) {
  const key = cells.length + ":" + (cells[0] || []).join(",") + ":" + (cells[cells.length - 1] || []).join(",");
  if (key === coverageKey) return;
  coverageKey = key;
  layers.coverage.clearLayers();
  for (const [s, w, n, e] of cells) {
    L.rectangle([[s, w], [n, e]], COVERAGE_STYLE).addTo(layers.coverage);
  }
}

function coverageBounds(cells) {
  if (!cells.length) return null;
  return L.latLngBounds(cells.flatMap(([s, w, n, e]) => [[s, w], [n, e]]));
}

// Stațiile de hidrofoane sunt fixe: se construiesc o singură dată (fără flicker la fiecare tick).
let hydroMarkersBuilt = false;
function buildHydrophoneLayers() {
  if (hydroMarkersBuilt) return;
  for (const h of ALL_HYDROPHONES) {
    const isSabotage = h.sig === "anchor_chain";
    const isContact = h.hasContact;
    const stCol = isSabotage ? "#f0525b" : isContact ? "#a855f7" : "#0284c7";

    // Cercul de acoperire de 15 km: estompat, ca să nu acopere navele și alertele.
    L.circle([h.lat, h.lon], {
      radius: 15000, color: stCol, weight: 1, opacity: isContact ? 0.45 : 0.12, dashArray: "5 5",
      fillOpacity: isContact ? 0.05 : 0.008, interactive: false,
    }).addTo(layers.hydroCoverage);

    const marker = isContact
      ? L.circleMarker([h.lat, h.lon], {
        radius: 7, color: "#ffffff", weight: 1.5, opacity: 0.9, fillColor: stCol, fillOpacity: 0.85,
      })
      : L.marker([h.lat, h.lon], { icon: glowIcon("glow-dot", 24), pane: "glowLow", keyboard: false });
    marker
      .bindTooltip(`<b>${esc(h.id)}</b> · ${esc(h.name)}<br><span class="${isContact ? "tt-sonar" : "tt-info"}">${esc(h.summary)}</span>`, {
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
  // Urmărire automată: fără o alegere a prezentatorului, detaliile arată alerta cu scorul cel mai mare.
  if (!S.userSelected) S.selected = active.length ? active[0].a.alert_id : null;
  const levelByMmsi = {};
  for (const { a, st } of active) {
    if (!a.mmsi) continue;   // ținte radar fără AIS: se colorează în renderRadar
    const cur = levelByMmsi[a.mmsi];
    if (!cur || LEVEL_RANK[st.level] > LEVEL_RANK[cur]) levelByMmsi[a.mmsi] = st.level;
  }
  const sel = S.alerts.find((a) => a.alert_id === S.selected);

  layers.vessels.clearLayers();
  layers.uncertainty.clearLayers();
  layers.trails.clearLayers();
  for (const v of S.tracks) {
    if (v.ship_type === PATROL_TYPE) continue;   // patrulele au desenul lor (renderPatrols)
    const i = lastIndexLE(v.times, t);
    if (i < 0) continue;
    const p = v.points[i];
    const gap = (S.gapsByMmsi[v.mmsi] || []).find((g) => g.s <= t && t <= g.e);
    const level = levelByMmsi[v.mmsi];
    const color = gap ? DARK_COLOR : level ? LEVEL_COLOR[level] : NORMAL_COLOR;
    if (gap) {
      const hours = (t - gap.s) / 3.6e6;
      const radiusKm = ((gap.metrics && gap.metrics.uncertainty_km_per_h) || 0) * hours;
      L.circle([gap.lat, gap.lon], { radius: radiusKm * 1000, color: DARK_COLOR, weight: 1, dashArray: "4 4", fillOpacity: 0.08 })
        .bindTooltip(`Uncertainty area: ${radiusKm.toFixed(1)} km`)
        .addTo(layers.uncertainty);
    }
    L.circleMarker([p.lat, p.lon], {
      radius: level ? 8 : 5, color: gap ? DARK_COLOR : "#0b131d", weight: gap ? 2 : 1,
      dashArray: gap ? "2 2" : null, fillColor: color, fillOpacity: gap ? 0.2 : 0.95,
    })
      .bindTooltip(
        `<b>${esc(v.name || "Unknown vessel")}</b> · MMSI ${esc(v.mmsi)}${v.ship_type ? ` · ${esc(v.ship_type)}` : ""}<br>${p.sog ?? "?"} kn · ${p.cog ?? "?"}°` +
        `${gap ? "<br>AIS off since " + fmtTime(gap.s) : ""}${v.simulated ? "<br>SIMULATED" : ""}`)
      .on("click", () => { const a = active.find((x) => x.a.mmsi === v.mmsi); if (a) select(a.a.alert_id); })
      .addTo(layers.vessels);
    if (sel && sel.mmsi === v.mmsi) {
      const from = lastIndexLE(v.times, t - TRAIL_MIN * 60000);
      const pts = v.points.slice(Math.max(0, from), i + 1).map((q) => [q.lat, q.lon]);
      L.polyline(pts, { color: LEVEL_COLOR[level] || NORMAL_COLOR, weight: 2, opacity: 0.8 }).addTo(layers.trails);
    }
  }

  // Evenimente acustice și de fibră active la momentul t
  layers.sensors.clearLayers();
  for (const e of S.sensors) {
    if (e.s > t || t - e.s > SENSOR_SHOW_MIN * 60000) continue;
    const m = e.metrics || {};
    if (e.source === "acoustic") {
      const col = m.signature === "anchor_chain" ? "#f0525b" : "#a855f7";
      const sig = m.signature ? `${esc(m.signature).toUpperCase()}${m.dominant_freq_hz ? ` @ ${num(m.dominant_freq_hz, 0)} Hz` : ""}` : "low-frequency energy";
      L.circleMarker([e.lat, e.lon], { radius: 16, color: col, weight: 3, fillOpacity: 0.3 })
        .bindTooltip(`<b>SONAR CONTACT: ${esc(e.sensor_id)}</b><br>${sig} · confidence ${pct(e.confidence)}<br><i>Click for the detailed report</i>`,
          { direction: "top", offset: [0, -12] })
        .on("click", () => { const hyd = findHydro(e.sensor_id); if (hyd) openSonarModal(hyd); else openFibreModal(e); })
        .addTo(layers.sensors);
    } else {
      const nearShore = isNearShoreNote(m.note);
      const colFibre = nearShore ? "#38bdf8" : "#f97316";
      const desc = nearShore
        ? `<span class="tt-info">Coastal mechanical noise near shore (low confidence).</span>`
        : `<span class="tt-warn">Mechanical vibration on the cable.</span>`;
      const fibreMarker = nearShore
        ? L.marker([e.lat, e.lon], { icon: glowIcon("glow-dot glow-lg", 44), pane: "glowHigh", keyboard: false })
        : L.circleMarker([e.lat, e.lon], { radius: 14, color: colFibre, weight: 3, fillColor: colFibre, fillOpacity: 0.35 });
      fibreMarker
        .bindTooltip(
          `<b>FIBRE-OPTIC SENSOR (DAS)</b> · ${esc(m.cable_id || e.sensor_id || "cable")}<br>` +
          `km <b>${num(m.cable_km, 1)}</b> from shore · ${esc(m.note || "")}<br>${desc}<br>` +
          `Amplitude ${m.amplitude ?? "?"} · confidence ${pct(e.confidence)}`,
          { direction: "top", offset: [0, -12] })
        .on("click", () => openFibreModal(e))
        .addTo(layers.sensors);
    }
  }

  highlightNearestInfra(sel && sel.created <= t ? sel : null);
  if (showsDemoExtras()) {
    renderSubmarines(t);
    updateRealtimeAudioBanner(t);
    highlightActiveHistoryItem(t);
  }
  renderPatrols(t, active);
  renderRadar(t, active);
  renderAlertList(active);
  renderDetail(t);
  renderTimelineMarkers(t);
}

// Evidențiază infrastructura cea mai apropiată de alerta selectată. Distanța vine din timeline (core),
// pagina doar schimbă stilul stratului deja desenat. Se reface doar când se schimbă selecția.
function highlightNearestInfra(a) {
  const near = a && a.nearest_infrastructure && a.nearest_infrastructure[0];
  const key = near ? `${a.alert_id}:${near.infra_id}` : null;
  if (key === (S.infraHighlight && S.infraHighlight.key)) return;
  if (S.infraHighlight) {
    const { layer, name } = S.infraHighlight;
    S.infraGeo.resetStyle(layer);
    if (layer.setRadius) layer.setRadius(7);
    layer.unbindTooltip().bindTooltip(esc(name));
    S.infraHighlight = null;
  }
  const layer = near && S.infraById[near.infra_id];
  if (!layer) return;
  layer.setStyle(INFRA_HIGHLIGHT);
  if (layer.setRadius) layer.setRadius(INFRA_HIGHLIGHT_RADIUS);
  if (layer.bringToFront) layer.bringToFront();
  layer.unbindTooltip().bindTooltip(
    `Nearest: <b>${esc(near.name)}</b> · ${num(near.distance_km, 1)} km`,
    { permanent: true, direction: "top", className: "infra-hl-label" });
  S.infraHighlight = { key, layer, name: near.name };
}

// ---------- contacte submarine (scenariu SIMULAT, doar afișare) ----------
// Pozițiile vin din assets/simulated_submarine_contacts.json; pagina doar interpolează între puncte în timp.
const SUB_COLOR = "#2dd4bf";
const SUB_LOST_MIN = 20;       // cât timp mai afișăm ultima estimare după ultimul punct
const DAS_LABEL = "DAS-CABLE-1";

function subStateAt(c, t) {
  const pts = c.track.map((p) => ({ ...p, tm: S.start + p.min * 60000 }));
  if (!pts.length || t < pts[0].tm) return null;
  const last = pts[pts.length - 1];
  if (t > last.tm + SUB_LOST_MIN * 60000) return null;
  if (t >= last.tm) return { ...last, lost: t > last.tm, past: pts.map((p) => [p.lat, p.lon]) };
  const i = pts.findIndex((p) => p.tm > t) - 1;
  const a = pts[i], b = pts[i + 1], f = (t - a.tm) / (b.tm - a.tm);
  const lerp = (x, y) => x + (y - x) * f;
  return {
    lat: lerp(a.lat, b.lat), lon: lerp(a.lon, b.lon), unc_km: lerp(a.unc_km, b.unc_km), conf: lerp(a.conf, b.conf),
    by: a.by, tm: t, lost: false,
    past: pts.slice(0, i + 1).map((p) => [p.lat, p.lon]).concat([[lerp(a.lat, b.lat), lerp(a.lon, b.lon)]]),
  };
}

function sensorPos(id) {
  const h = findHydro(id);
  if (h) return [h.lat, h.lon];
  const m = S.subSensors[id];
  return m ? [m.lat, m.lon] : null;
}

// Alerta unui contact submarin vine din evaluarea SCRIPTATĂ din fișierul de scenariu (scor, nivel, factori),
// nu e calculată în pagină. O transformăm doar în aceeași formă ca alertele din timeline, ca să fie afișată la fel.
function scriptedAlerts() {
  if (!S.start) return [];
  return S.subs.filter((c) => c.assessment && c.assessment.length).map((c) => {
    const steps = c.assessment.map((x) => ({ ...x, tm: S.start + x.min * 60000 }));
    const focus = c.track.find((p) => p.min >= steps[steps.length - 1].min) || c.track[c.track.length - 1];
    return {
      alert_id: `scripted-${c.id}`, scripted: true, simulated: true, mmsi: null, sub_id: c.id,
      vessel_name: c.name, alert_type: "submerged_contact",
      created: steps[0].tm, start_time: new Date(S.start + c.track[0].min * 60000).toISOString(),
      lat: focus.lat, lon: focus.lon,
      hist: steps.map((x) => ({ tm: x.tm, score: x.score, level: x.level, unit_id: x.unit_id || null, eta_min: x.eta_min ?? null })),
      factors: steps.flatMap((x) => (x.factors || []).map((f) => ({ ...f, added_at: new Date(x.tm).toISOString(), simulated: true }))),
    };
  });
}

function renderSubmarines(t) {
  layers.submarines.clearLayers();
  const active = [];
  for (const c of S.subs) {
    const st = subStateAt(c, t);
    if (!st) continue;
    active.push({ c, st });
    L.polyline(st.past, { color: SUB_COLOR, weight: 2, opacity: 0.55, dashArray: "2 6", lineCap: "round" }).addTo(layers.submarines);
    // Linii de triangulare spre senzorii care contribuie la poziție
    for (const id of st.by || []) {
      const pos = sensorPos(id);
      if (pos) L.polyline([pos, [st.lat, st.lon]], { color: SUB_COLOR, weight: 1, opacity: 0.35, dashArray: "4 6", interactive: false }).addTo(layers.submarines);
    }
    L.circle([st.lat, st.lon], {
      radius: st.unc_km * 1000, color: SUB_COLOR, weight: 1, opacity: 0.5, fillColor: SUB_COLOR, fillOpacity: 0.07, dashArray: "3 5", interactive: false,
    }).addTo(layers.submarines);
    L.marker([st.lat, st.lon], { icon: glowIcon(`glow-sub${st.lost ? " lost" : ""}`, 30), pane: "glowHigh", keyboard: false })
      .bindTooltip(`<b>${esc(c.name)}</b> · SIMULATED<br>${esc(c.classification)}<br>` +
        `±${st.unc_km.toFixed(1)} km · confidence ${pct(st.conf)}${st.lost ? " · <i>contact lost</i>" : ""}<br><i>Click for detection details</i>`,
        { direction: "top", offset: [0, -14] })
      .on("click", () => openSubModal(c, st))
      .addTo(layers.submarines);
  }
  renderSubList(active);
}

function renderSubList(active) {
  const box = $("sub-list");
  if (!box) return;
  $("sub-count").textContent = active.length;
  $("no-subs").hidden = active.length > 0;
  box.innerHTML = active.map(({ c, st }) => `
    <div class="history-item sub-item" data-id="${esc(c.id)}" role="button" tabindex="0">
      <span class="history-time">${fmtTime(S.start + c.track[0].min * 60000)}</span>
      <div class="history-content">
        <span class="history-title">${esc(c.name)}${SIM_TAG}</span>
        <span class="history-loc">${esc(c.summary)}</span>
      </div>
      <span class="history-badge badge-sub">${st.lost ? "Lost" : "±" + st.unc_km.toFixed(1) + " km"}</span>
    </div>`).join("");
  for (const el of box.querySelectorAll(".sub-item")) {
    const open = () => { const x = active.find((a) => a.c.id === el.dataset.id); if (x) { map.panTo([x.st.lat, x.st.lon]); openSubModal(x.c, x.st); } };
    el.onclick = open;
    el.onkeydown = (ev) => { if (ev.key === "Enter") open(); };
  }
}

function openSubModal(c, st) {
  const modal = $("sonar-modal");
  if (!modal) return;
  const sensorName = (id) => (findHydro(id) ? `${id} (hydrophone)` : S.subSensors[id] ? `${id} (magnetometer buoy)` : id === DAS_LABEL ? `${id} (fibre-optic DAS)` : id);
  $("modal-title").textContent = `${c.name} — submerged contact`;
  $("modal-body").innerHTML = `
    <div class="modal-row">
      <span class="modal-badge" style="background:#0f766e;">${st.lost ? "CONTACT LOST" : "TRACKING"} · SIMULATED</span>
      <span class="muted small">${st.lat.toFixed(3)}°N, ${st.lon.toFixed(3)}°E · ${fmtTime(st.tm)}</span>
    </div>
    <div class="modal-text"><b>Classification:</b> ${esc(c.classification)}.<br>${esc(c.summary)}.</div>
    <div class="modal-grid">
      ${card("Position uncertainty", `±${st.unc_km.toFixed(1)} km`)}
      ${card("Confidence", pct(st.conf))}
      ${card("Sensors in this fix", esc((st.by || []).join(", ")) || "—")}
      ${card("First detected", fmtTime(S.start + c.track[0].min * 60000))}
    </div>
    <h3>How it is detected (low-cost)</h3>
    <ul class="lines">${(c.methods || []).map((m) => `<li><b>${esc(m.name)}.</b> ${esc(m.detail)}</li>`).join("")}</ul>
    <p class="muted small" style="margin:10px 0 0;">Contributing sensors: ${c.sensors.map((id) => esc(sensorName(id))).join(" · ")}.<br>
    Scenario data for the demo: shown on the map only, not part of the risk score.</p>`;
  modal.showModal();
}

function renderTimelineMarkers(t) {
  const container = $("slider-markers");
  if (!container) return;
  const dur = S.end - S.start;
  if (dur <= 0) {
    container.innerHTML = "";
    return;
  }
  S.alerts.forEach(a => {
    if (a.created <= t) S.revealedAlerts.add(a.alert_id);
  });
  container.innerHTML = S.alerts
    .filter(a => S.revealedAlerts.has(a.alert_id))
    .map(a => {
      const pct = ((a.created - S.start) / dur) * 100;
      const st = a.hist && a.hist.length > 0 ? a.hist[0] : null;
      const color = st ? LEVEL_COLOR[st.level] : LEVEL_COLOR.high;
      return `<div class="timeline-marker" style="left: ${pct}%; background: ${color}" title="${esc(a.alert_type)} at ${fmtTime(a.created)}"></div>`;
    }).join("");
}

function renderAcousticHistory() {
  const list = $("acoustic-history-list");
  if (!list) return;
  const contacts = TACTICAL_CONTACTS.slice().sort((a, b) => hydroTime(a) - hydroTime(b));
  list.innerHTML = contacts.map((h) => `
      <div class="history-item" data-id="${esc(h.id)}" role="button" tabindex="0">
        <span class="history-time">${fmtTime(hydroTime(h))}</span>
        <div class="history-content">
          <span class="history-title">${esc(h.id)} · ${esc(h.name.split("(")[0].trim())}</span>
          <span class="history-loc">${esc(h.summary)}</span>
        </div>
        <span class="history-badge ${esc(h.badgeClass)}">${esc(h.badgeText)}</span>
      </div>`).join("");
  for (const item of list.querySelectorAll(".history-item")) {
    const open = () => { const h = findHydro(item.dataset.id); jumpTo(hydroTime(h)); openSonarModal(h); };
    item.onclick = open;
    item.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } };
  }
}

const isHydroLive = (h, t) => t >= hydroTime(h) && t - hydroTime(h) < SENSOR_SHOW_MIN * 60000;

function highlightActiveHistoryItem(t) {
  let shown = 0;
  for (const item of document.querySelectorAll("#acoustic-history-list .history-item")) {
    const h = findHydro(item.dataset.id);
    if (!h) continue;
    // La derulare nu arătăm contacte pe care sistemul nu le avea încă la momentul t.
    item.hidden = hydroTime(h) > t;
    if (!item.hidden) shown++;
    item.classList.toggle("is-live", isHydroLive(h, t));
  }
  const none = $("no-acoustic");
  if (none) none.hidden = shown > 0;
}

// Banner „Ce se aude în timp real”
function updateRealtimeAudioBanner(t) {
  const banner = $("realtime-audio-banner");
  if (!banner || banner.hidden) return;
  $("audio-time").textContent = fmtTime(t);
  const activeHyd = TACTICAL_CONTACTS.find((h) => isHydroLive(h, t));
  const box = $("audio-status-text");
  if (activeHyd) {
    box.innerHTML = `<b class="tt-sonar">${esc(activeHyd.id)} (${esc(activeHyd.name)}):</b> ${esc(activeHyd.realtimeText)}<br>` +
      `<button type="button" class="btn-mini" style="margin-top:6px;">Open spectrogram</button>`;
    box.querySelector("button").onclick = () => openSonarModal(activeHyd);
  } else {
    box.innerHTML = `At ${fmtTime(t)} only the <i>natural background noise of the Black Sea</i> is being captured. No suspicious vessel or abnormal acoustic activity recorded.`;
  }
}

$("btn-realtime-audio").onclick = () => {
  const b = $("realtime-audio-banner");
  b.hidden = !b.hidden;
  if (!b.hidden) updateRealtimeAudioBanner(S.t);
};
$("btn-close-audio-banner").onclick = () => { $("realtime-audio-banner").hidden = true; };

// ---------- radar Sentinel-1 ----------
// Decupajul radar al țintei (scris de sar.process) și legătura spre produsul ESA din catalog.
function radarEvidence(e) {
  const hit = findTarget(e.target_id);
  const m = e.metrics || {};
  const chip = hit && hit.target.chip;
  return `
    <div class="evidence radar-evidence">
      ${chip ? `<img class="radar-chip" src="../${esc(chip)}" alt="Radar crop of the target" width="96" height="96">` : ""}
      <div>
        <div class="evidence-title">RADAR TARGET · ${esc(m.satellite || "Sentinel-1")} · ${esc(m.acquired || "")}</div>
        <div class="evidence-sub">${num(m.length_m, 0)} m apparent length · ${num(m.peak_db, 1)} dB over the sea clutter</div>
        ${hit && hit.pass.source_url ? `<a class="evidence-link" href="${esc(hit.pass.source_url)}" target="_blank" rel="noopener">ESA product in the catalogue ↗</a>` : ""}
      </div>
    </div>`;
}

let radarKey = "";
function renderRadar(t, active) {
  const pass = radarPassAt(t);
  const selected = S.alerts.find((a) => a.alert_id === S.selected);
  const alertByTarget = {};
  for (const { a, st } of active) if (a.target_id) alertByTarget[a.target_id] = st.level;
  const key = [pass ? pass.pass_id : "", selected ? selected.target_id || "" : "", JSON.stringify(alertByTarget)].join("|");
  renderDarkTargets(pass);
  if (key === radarKey) return;   // nimic nou: fără redesenare (tooltipurile nu clipesc)
  radarKey = key;
  layers.radarImage.clearLayers();
  layers.radarTargets.clearLayers();
  if (!pass) return;
  if (pass.image && pass.image_bounds.length === 2) {
    L.imageOverlay("../" + pass.image, pass.image_bounds, { opacity: RADAR_IMAGE_OPACITY, interactive: false, className: "radar-image" })
      .addTo(layers.radarImage);
  }
  if (pass.footprint.length > 2) {
    L.polygon(pass.footprint, { color: "#9ab8d8", weight: 1, dashArray: "4 6", fill: false, interactive: false })
      .addTo(layers.radarImage);
  }
  const when = `${esc(pass.satellite)} · image ${fmtTime(pass.acq)} · published ${fmtTime(pass.avail)}`;
  for (const x of pass.targets) {
    const look = RADAR_STATUS[x.status] || RADAR_STATUS.fixed;
    const level = alertByTarget[x.target_id];
    const strong = x.status === "dark" || x.status === "dark_uncovered";
    const isSel = selected && selected.target_id === x.target_id;
    const size = strong ? 18 : 11;
    const marker = L.marker([x.lat, x.lon], {
      icon: L.divIcon({
        className: "",
        html: `<div class="radar-target${strong ? " strong" : ""}${isSel ? " selected" : ""}" style="--c:${level ? LEVEL_COLOR[level] : look.color}"></div>`,
        iconSize: [size, size], iconAnchor: [size / 2, size / 2],
      }),
      keyboard: false, zIndexOffset: strong ? 500 : 0,
    });
    const who = x.mmsi
      ? `<br>${x.status === "matched" ? "AIS" : "Silent vessel"}: ${esc(x.vessel_name || "unknown")} (MMSI ${esc(x.mmsi)})${x.match_km != null ? ` · ${num(x.match_km, 2)} km` : ""}`
      : "";
    marker.bindTooltip(
      `${x.chip ? `<img class="radar-chip small" src="../${esc(x.chip)}" alt="" width="64" height="64"><br>` : ""}` +
      `<b>Radar target</b> · ${num(x.length_m, 0)} m · ${num(x.peak_db, 1)} dB<br>${esc(look.label)}${who}` +
      `${x.note ? `<br><i>${esc(x.note)}</i>` : ""}<br><span class="muted">${when}</span>`,
      { direction: "top", offset: [0, -8] });
    const a = S.alerts.find((al) => al.target_id === x.target_id);
    if (a) marker.on("click", () => select(a.alert_id));
    marker.addTo(layers.radarTargets);
  }
}

// Lista țintelor fără AIS ale trecerii vizibile (cele mai luminoase primele).
let darkKey = "";
function renderDarkTargets(pass) {
  const dark = pass ? pass.targets.filter((x) => x.status === "dark" || x.status === "dark_uncovered") : [];
  const key = (pass ? pass.pass_id : "") + "|" + dark.length;
  if (key === darkKey) return;
  darkKey = key;
  $("radar-count").textContent = dark.length;
  $("radar-meta").textContent = pass
    ? `${pass.satellite} · image ${fmtTime(pass.acq)} · published ${fmtTime(pass.avail)} · ${pass.targets.length} targets on the sea`
    : "No radar image published up to this moment.";
  $("no-radar").hidden = dark.length > 0 || !pass;
  $("radar-list").innerHTML = dark.sort((a, b) => b.peak_db - a.peak_db).map((x) => `
    <li data-id="${esc(x.target_id)}" tabindex="0">
      ${x.chip ? `<img class="radar-chip small" src="../${esc(x.chip)}" alt="" width="40" height="40">` : ""}
      <span><b>${num(x.length_m, 0)} m</b> · ${num(x.peak_db, 1)} dB<br><span class="muted">${esc((RADAR_STATUS[x.status] || {}).label || x.status)}${x.mmsi ? ` · ${esc(x.vessel_name || x.mmsi)}` : ""}</span></span>
    </li>`).join("");
  for (const li of $("radar-list").querySelectorAll("li")) {
    const go = () => {
      const hit = findTarget(li.dataset.id);
      if (!hit) return;
      map.setView([hit.target.lat, hit.target.lon], Math.max(map.getZoom(), 11));
      const a = S.alerts.find((al) => al.target_id === li.dataset.id);
      if (a) select(a.alert_id);
    };
    li.onclick = go;
    li.onkeydown = (ev) => { if (ev.key === "Enter") go(); };
  }
}

function renderAlertList(active) {
  $("alert-count").textContent = active.length;
  $("no-alerts").hidden = active.length > 0;
  $("alert-list").innerHTML = active.map(({ a, st }) => {
    // O alertă confirmată de operator nu mai clipește: cineva se ocupă de ea.
    const eng = S.engaged[a.alert_id];
    const cls = [a.alert_id === S.selected ? "selected" : "", eng ? "engaged" : st.score > FLASH_SCORE ? "flash" : st.score >= PULSE_SCORE ? "pulse" : ""].join(" ");
    return `
    <li data-id="${esc(a.alert_id)}" class="${cls}" tabindex="0">
      <span class="chip lvl-${esc(st.level)}"></span>
      <span class="name">${esc(alertName(a))}${a.scripted ? SCRIPT_TAG : a.simulated ? SIM_TAG : ""}${eng ? ENGAGED_TAG : ""}</span>
      <span class="score">${st.score}</span>
      <span class="sub">${esc(a.alert_type)} · ${LEVEL_LABEL[st.level] || esc(st.level)} · since ${fmtTime(a.created)}</span>
    </li>`;
  }).join("");
  for (const li of $("alert-list").querySelectorAll("li")) {
    li.onclick = () => select(li.dataset.id);
    li.onkeydown = (ev) => { if (ev.key === "Enter") select(li.dataset.id); };
  }
}

function renderDetail(t) {
  const a = S.alerts.find((x) => x.alert_id === S.selected);
  const st = a && a.created <= t ? stateAt(a, t) : null;
  $("detail").hidden = !st;
  if (!st) return;
  const factors = a.factors.filter((f) => ms(f.added_at) <= t);
  $("detail-title").innerHTML = `${esc(a.scripted ? a.vessel_name || "Unknown vessel" : alertName(a))} · ${st.score}/100 ${a.scripted ? SCRIPT_TAG : a.simulated ? SIM_TAG : ""}`;
  $("detail-meta").textContent = (a.scripted
    ? `Submerged contact ${a.sub_id} · scripted demo scenario (not computed by the pipeline) · level ${LEVEL_LABEL[st.level] || st.level} · alert ${fmtTime(a.created)}`
    : `${a.mmsi ? `MMSI ${a.mmsi}` : `No AIS · radar target ${a.target_id}`} · level ${LEVEL_LABEL[st.level] || st.level} · onset ${fmtTime(ms(a.start_time))} · alert ${fmtTime(a.created)} · id ${a.alert_id}`);
  $("factors").innerHTML = factors.map((f) => `
    <div class="factor"><div class="row"><span>${esc(f.label)}${f.simulated ? SIM_TAG : ""}</span><b>+${f.points}</b></div>
    <div class="bar"><span style="width:${Math.min(100, f.points)}%"></span></div></div>`).join("") +
    `<div class="factor total"><div class="row"><span>Total (capped)</span><b>${st.score}</b></div>
     <div class="bar"><span style="width:${Math.min(100, st.score)}%"></span></div></div>`;

  $("detail-lines").innerHTML = factors.map((f) => {
    let extra = "";
    if (f.code === "acoustic_lowfreq") {
      // Dovada acustică vine din evenimentul legat de factor, nu din valori scrise în pagină.
      const ev = S.sensors.find((e) => e.event_id === f.event_id) || null;
      const m = (ev && ev.metrics) || {};
      const hyd = ev ? findHydro(ev.sensor_id) : null;
      extra = `
        <div class="evidence">
          <div class="evidence-title">ACOUSTIC CONTACT${ev ? ` · ${esc(ev.sensor_id)}` : ""}${m.signature ? ` · ${esc(m.signature).toUpperCase()}` : ""}</div>
          <div class="evidence-sub">Peak frequency ${m.dominant_freq_hz ? num(m.dominant_freq_hz, 1) + " Hz" : "?"} · confidence ${pct(ev && ev.confidence)}</div>
          ${hyd ? `<button type="button" class="btn-mini" data-hyd="${esc(hyd.id)}">View sonar spectrogram</button>` : ""}
        </div>`;
    }
    const sar = f.event_id && S.radarEvents[f.event_id];
    if (sar) extra = radarEvidence(sar);
    return `<li>${esc(f.detail)}${extra}</li>`;
  }).join("");
  for (const b of $("detail-lines").querySelectorAll("button[data-hyd]")) b.onclick = () => openSonarModal(findHydro(b.dataset.hyd));

  const near = a.nearest_infrastructure || [];
  $("detail-infra-block").hidden = !near.length;
  $("detail-infra").innerHTML = near.map((n, i) => `
    <li class="${i === 0 ? "nearest" : ""}"><span>${esc(n.name)}</span><b>${num(n.distance_km, 1)} km</b></li>`).join("");

  const u = st.unit_id && S.units[st.unit_id];
  $("recommendation").innerHTML = st.unit_id
    ? `<b>${esc(u ? u.name : st.unit_id)}</b> · ${st.eta_min === 0 ? "on scene" : `ETA ${st.eta_min != null ? Number(st.eta_min).toFixed(0) + " min" : "?"}`}${u && u.simulated ? SIM_TAG : ""}`
    // Timeline-ul nu spune de ce lipsește unitatea (sub nivelul de recomandare sau toate unitățile trimise deja).
    : "No unit recommended at this moment (below the recommendation level, or every unit is already dispatched).";
  renderEngage(a, st, u);
}

function taskingText(a, st, u) {
  const lines = [
    `TASKING ${new Date(S.t).toISOString().slice(0, 16).replace("T", " ")} UTC`,
    `Unit: ${u ? u.name : st.unit_id}${u && u.simulated ? " (SIMULATED)" : ""}`,
    `Target: ${alertName(a)}${a.mmsi ? ` (MMSI ${a.mmsi})` : ""}`,
    `Position: ${num(a.lat, 4)} N, ${num(a.lon, 4)} E`,
    `Risk: ${st.score}/100 (${LEVEL_LABEL[st.level] || st.level})` + (st.eta_min != null ? ` · ETA ${Number(st.eta_min).toFixed(0)} min` : ""),
    `Reason: ${a.explanation || a.alert_type}`,
    `Alert id: ${a.alert_id}`,
  ];
  return lines.join("\n");
}

function renderEngage(a, st, u) {
  const box = $("engage");
  const eng = S.engaged[a.alert_id];
  if (!st.unit_id && !eng) { box.innerHTML = ""; return; }
  box.innerHTML = eng
    ? `<div class="engaged-note">${ENGAGED_TAG} ${esc(S.units[eng.unitId] ? S.units[eng.unitId].name : eng.unitId)} engaged by the operator at ${fmtTime(eng.at)}</div>
       <button type="button" class="btn-mini" id="btn-copy-tasking">Copy tasking</button>
       <button type="button" class="btn-mini" id="btn-release">Release</button>`
    : `<button type="button" class="btn-engage" id="btn-engage">Acknowledge &amp; engage</button>
       <button type="button" class="btn-mini" id="btn-copy-tasking">Copy tasking</button>`;
  const engage = $("btn-engage");
  if (engage) engage.onclick = () => { S.engaged[a.alert_id] = { unitId: st.unit_id, at: S.t }; saveEngaged(); render(); };
  const release = $("btn-release");
  if (release) release.onclick = () => { delete S.engaged[a.alert_id]; saveEngaged(); render(); };
  const copy = $("btn-copy-tasking");
  if (copy) copy.onclick = async () => {
    try { await navigator.clipboard.writeText(taskingText(a, st, u)); copy.textContent = "Copied"; }
    catch (e) { copy.textContent = "Copy failed"; }
  };
}

function select(id) {
  S.selected = id;
  S.userSelected = true;
  const a = S.alerts.find((x) => x.alert_id === id);
  const sub = a && a.scripted ? S.subs.find((c) => c.id === a.sub_id) : null;
  const pos = sub ? subStateAt(sub, S.t) : null;
  if (pos) map.panTo([pos.lat, pos.lon]); else if (a) map.panTo([a.lat, a.lon]);
  render();
}

// ---------- modale ----------
function card(label, value, color) {
  return `<div class="modal-card"><b>${esc(label)}</b><span${color ? ` style="color:${color}"` : ""}>${value}</span></div>`;
}

// Pragul de detecție raportat de pipeline (din orice eveniment acustic), ca să nu-l scriem în pagină.
function reportedThreshold() {
  const e = S.sensors.find((x) => x.source === "acoustic" && x.metrics && x.metrics.ratio_threshold != null);
  return e ? num(e.metrics.ratio_threshold) : "?";
}

function openSonarModal(hyd) {
  const modal = $("sonar-modal");
  if (!modal || !hyd) return;
  $("modal-title").textContent = `Sonar analysis: ${hyd.id} — ${hyd.name}`;
  const coords = `${hyd.lat.toFixed(3)}°N, ${hyd.lon.toFixed(3)}°E`;
  const ev = hydroEvent(hyd);

  if (!hyd.hasContact || (!ev && hyd.sig !== "ambient")) {
    $("modal-body").innerHTML = `
      <div class="modal-row">
        <span class="modal-badge" style="background:#0284c7;">STANDBY · NO CONTACT</span>
        <span class="muted small">${coords}</span>
      </div>
      <div class="modal-text"><b>Assessment:</b> no acoustic event was reported by this hydrophone during the scenario.</div>
      <div class="modal-note">Simulated station. The pipeline only raises an event when low-frequency energy exceeds its adaptive threshold.</div>
      <div class="modal-grid">
        ${card("Status", "Active (standby)", "#38bdf8")}
        ${card("Events in scenario", "0")}
        ${card("Detection threshold", reportedThreshold() + " low-frequency ratio")}
        ${card("Coverage radius", "15 km (display)")}
      </div>`;
    modal.showModal();
    return;
  }

  const m = (ev && ev.metrics) || {};
  const badgeColor = hyd.sig === "anchor_chain" ? "var(--critical)" : "var(--sonar)";
  const img = hyd.clip ? `
    <div>
      <div class="modal-spec-label">STFT spectrogram</div>
      <img src="../out/spectrograms/${encodeURIComponent(hyd.clip)}" class="modal-spec-img" alt="Sonar spectrogram" onerror="this.parentElement.hidden=true">
    </div>` : "";
  $("modal-body").innerHTML = `
    <div class="modal-row">
      <span class="modal-badge" style="background:${badgeColor};">${esc(hyd.badgeText)}</span>
      <span class="muted small">${coords}${ev ? ` · ${fmtTime(ev.s)}` : ""}</span>
    </div>
    <div class="modal-text"><b>Assessment:</b> ${esc(hyd.realtimeText)}</div>
    ${img}
    <div class="modal-grid">
      ${card("Signature", esc((m.signature || hyd.sig || "?").toUpperCase()), badgeColor)}
      ${card("Dominant frequency", m.dominant_freq_hz ? num(m.dominant_freq_hz, 1) + " Hz" : "No peak (broadband)")}
      ${card("Low-frequency ratio", ev ? `${num(m.lowfreq_ratio, 3)} (threshold ${num(m.ratio_threshold)})` : "Below threshold")}
      ${card("Confidence", ev ? `${pct(ev.confidence)} · ${num(m.duration_s, 0)} s` : "No event")}
    </div>`;
  modal.showModal();
}

function openFibreModal(e) {
  const modal = $("sonar-modal");
  if (!modal || !e) return;
  const m = e.metrics || {};
  const nearShore = isNearShoreNote(m.note);
  $("modal-title").textContent = `Fibre-optic sensor (DAS): ${e.sensor_id || "cable"}`;
  $("modal-body").innerHTML = `
    <div class="modal-row">
      <span class="modal-badge" style="background:${nearShore ? "#0284c7" : "#dc2626"};">${nearShore ? "COASTAL NOISE" : "CABLE VIBRATION"}</span>
      <span class="muted small">Cable ${esc(m.cable_id || "?")} · km ${num(m.cable_km, 1)} · ${fmtTime(e.s)}</span>
    </div>
    <div class="modal-text">
      ${nearShore
        ? `Distributed acoustic sensing (DAS) on the subsea cable recorded mechanical noise <b>near the shore</b> at km ${num(m.cable_km, 1)}: waves or coastal traffic. Amplitude ${m.amplitude ?? "?"} and confidence ${pct(e.confidence)} are low, so on its own it does not raise a security alert.`
        : `Distributed acoustic sensing (DAS) on the subsea cable recorded <b>mechanical vibration offshore</b> at km ${num(m.cable_km, 1)}, consistent with physical contact or an anchor dragged across the cable. Amplitude ${m.amplitude ?? "?"}, confidence ${pct(e.confidence)}.`}
    </div>
    <div class="modal-grid">
      ${card("Sensor type", "Subsea fibre optic (DAS)")}
      ${card("Position on cable", `km ${num(m.cable_km, 1)} from shore`)}
      ${card("Vibration amplitude", esc(m.amplitude ?? "?"))}
      ${card("Detector note", esc(m.note || "—"))}
    </div>
    <p class="muted small" style="margin:12px 0 0;">${e.simulated ? "SIMULATED event." : ""}</p>`;
  modal.showModal();
}

$("modal-close").onclick = () => $("sonar-modal").close();
$("sonar-modal").onclick = (e) => { if (e.target === $("sonar-modal")) $("sonar-modal").close(); };

// ---------- replay ----------
function jumpTo(tms) {
  S.t = Math.min(Math.max(tms, S.start), S.end);
  if (S.live) { S.live = false; $("live").checked = false; }
  render();
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
  $("play").setAttribute("aria-label", on ? "Pause" : "Play");
}

$("play").onclick = () => {
  if (S.t >= S.end) S.t = S.start;
  setPlaying(!S.playing);
};
$("slider").oninput = (e) => {
  S.t = S.start + Number(e.target.value) * 1000;
  if (S.live) { S.live = false; $("live").checked = false; }
  render();
};
$("live").onchange = (e) => {
  S.live = e.target.checked;
  if (S.live) { S.t = S.end; render(); }
};
// Spațiu = play/pause, când focusul nu e într-un câmp de formular.
document.addEventListener("keydown", (ev) => {
  if (ev.code !== "Space" || ev.target.closest("input, select, button, textarea, [tabindex]") || $("sonar-modal").open) return;
  ev.preventDefault();
  $("play").click();
});

// Zi / noapte: atributul data-theme e setat din <head> înainte de randare (fără flash).
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = $("theme-toggle");
  btn.textContent = theme === "day" ? "☾ Night" : "☀ Day";
  btn.setAttribute("aria-label", theme === "day" ? "Switch to night mode" : "Switch to day mode");
  try { localStorage.setItem("seagrid.theme", theme); } catch (e) { /* stocare indisponibilă */ }
}
applyTheme(document.documentElement.dataset.theme === "day" ? "day" : "night");
$("theme-toggle").onclick = () => applyTheme(document.documentElement.dataset.theme === "day" ? "night" : "day");

loadAssets();
loadAreaAssets(ASSETS);
$(SeaGridLoader.MODE === "live" ? "mode-live" : "mode-demo").setAttribute("aria-current", "page");
SeaGridLoader.start(ingest, (err) => {
  const hint = SeaGridLoader.MODE === "live"
    ? "start python -m data.aisstream and python -m core.live"
    : "run python -m core.demo";
  $("status").textContent = `Cannot load ${SeaGridLoader.SRC}: ${hint}, and serve the repo root.`;
  console.error(err);
});
