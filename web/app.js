// SeaGrid UI: doar afișare. Nicio logică de detecție aici; totul vine din timeline.json.
"use strict";

// Constante de AFIȘARE (nu praguri de detecție).
const MAP_CENTER = [44.25, 29.35];
const MAP_ZOOM = 9;
const TICK_MS = 100;
const TRAIL_MIN = 60;          // cât din traseu desenăm pentru nava selectată
const SENSOR_SHOW_MIN = 30;    // cât timp rămâne vizibil un eveniment de senzor
const ASSETS = "../assets/";

const LEVEL_COLOR = { low: "#4f8fd6", medium: "#e0b43a", high: "#ef7f2f", critical: "#e5484d" };
const LEVEL_TEXT = { low: "low", medium: "medium", high: "high", critical: "critical" };
const LEVEL_RANK = { low: 0, medium: 1, high: 2, critical: 3 };
const NORMAL_COLOR = "#3fb6a8";
const DARK_COLOR = "#8b9bb0";
const SIM_TAG = '<span class="tag-sim">SIMULATED</span>';
const INFRA_STYLE = {
  pipeline: { color: "#f0a050", weight: 3 },
  cable: { color: "#b48af0", weight: 2, dashArray: "6 4" },
  anchorage: { color: "#4f8fd6", weight: 1, fillOpacity: 0.08 },
  port_approach: { color: "#8b9bb0", weight: 1, fillOpacity: 0.06, dashArray: "3 3" },
};

const S = {
  tl: null, start: 0, end: 0, t: 0, playing: false, live: false, selected: null,
  tracks: [], alerts: [], gapsByMmsi: {}, sensors: [], units: {},
};

const $ = (id) => document.getElementById(id);
const ms = (iso) => Date.parse(iso);
const fmtTime = (t) => new Date(t).toISOString().slice(11, 16) + " UTC";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------- hartă ----------
// STUB: dalele OpenStreetMap cer internet; fără rețea harta rămâne goală, dar straturile SeaGrid se văd.
const map = L.map("map", { preferCanvas: true }).setView(MAP_CENTER, MAP_ZOOM);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 13,
  attribution: "&copy; OpenStreetMap · SeaGrid: simulated data, approximate coordinates",
}).addTo(map);
const layers = {
  infra: L.layerGroup().addTo(map),
  units: L.layerGroup().addTo(map),
  sensors: L.layerGroup().addTo(map),
  trails: L.layerGroup().addTo(map),
  uncertainty: L.layerGroup().addTo(map),
  vessels: L.layerGroup().addTo(map),
};

const legend = L.control({ position: "bottomleft" });
legend.onAdd = () => {
  const d = L.DomUtil.create("div", "legend");
  d.innerHTML =
    `<div><i style="background:${NORMAL_COLOR}"></i>normal vessel</div>` +
    `<div><i style="background:${DARK_COLOR}"></i>AIS off (uncertainty area)</div>` +
    Object.entries(LEVEL_COLOR).map(([k, c]) => `<div><i style="background:${c}"></i>${LEVEL_TEXT[k]} alert</div>`).join("") +
    `<div><i style="background:#f0a050"></i>pipeline</div><div><i style="background:#b48af0"></i>cable</div>`;
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
        .bindTooltip(`${esc(u.name)} · ${u.speed_kn} kn${u.simulated ? " · SIMULATED" : ""}`)
        .addTo(layers.units);
    }
  } catch (e) { console.warn(e); }
}

// ---------- date ----------
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
  $("status").textContent = `mode ${tl.mode} · batch ${tl.batch_index} · now ${fmtTime(S.end)}`;
  render();
}

// Starea unei alerte la momentul t: ultimul punct din istoric cu t_h <= t (calculat de pipeline).
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

// ---------- randare ----------
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
        .bindTooltip(`Uncertainty area: ${radiusKm.toFixed(1)} km`)
        .addTo(layers.uncertainty);
    }
    L.circleMarker([p.lat, p.lon], {
      radius: level ? 8 : 5, color: gap ? DARK_COLOR : "#0b1118", weight: gap ? 2 : 1,
      dashArray: gap ? "2 2" : null, fillColor: color, fillOpacity: gap ? 0.2 : 0.95,
    })
      .bindTooltip(
        `<b>${esc(v.name || "unknown")}</b> · MMSI ${v.mmsi}<br>${p.sog ?? "?"} kn · ${p.cog ?? "?"}°` +
        `${gap ? "<br>AIS off since " + fmtTime(gap.s) : ""}${v.simulated ? "<br>SIMULATED" : ""}`)
      .on("click", () => { const a = active.find((x) => x.a.mmsi === v.mmsi); if (a) select(a.a.alert_id); })
      .addTo(layers.vessels);
    if (sel && sel.mmsi === v.mmsi) {
      const from = lastIndexLE(v.times, t - TRAIL_MIN * 60000);
      const pts = v.points.slice(Math.max(0, from), i + 1).map((q) => [q.lat, q.lon]);
      L.polyline(pts, { color: LEVEL_COLOR[level] || NORMAL_COLOR, weight: 2, opacity: 0.8 }).addTo(layers.trails);
    }
  }

  layers.sensors.clearLayers();
  for (const e of S.sensors) {
    if (e.s > t || t - e.s > SENSOR_SHOW_MIN * 60000) continue;
    let label = "";
    if (e.source === "acoustic") {
      const sig = e.metrics && e.metrics.signature ? ` [${esc(e.metrics.signature)} @ ${e.metrics.dominant_freq_hz || 50} Hz]` : "";
      label = `<b>Acoustic ${esc(e.sensor_id)}</b>${sig} · conf ${e.confidence}`;
      if (e.metrics && e.metrics.clip) {
        const pngName = esc(e.metrics.clip.replace(".wav", ".png"));
        label += `<br><img src="../out/spectrograms/${pngName}" style="width:180px;height:65px;margin-top:4px;border-radius:4px;display:block;border:1px solid #555;">`;
      }
    } else {
      label = `Fibre km ${e.metrics.cable_km} · conf ${e.confidence}`;
    }
    L.circleMarker([e.lat, e.lon], { radius: 14, color: "#b48af0", weight: 2, fillOpacity: 0.25 })
      .bindTooltip(`${label}${e.simulated ? " · SIMULATED" : ""}`,
                   { permanent: true, direction: "top", className: e.simulated ? "sim-label" : "" })
      .addTo(layers.sensors);
  }

  renderAlertList(active);
  renderDetail(t);
}

function renderAlertList(active) {
  $("alert-count").textContent = active.length;
  $("no-alerts").hidden = active.length > 0;
  $("alert-list").innerHTML = active.map(({ a, st }) => `
    <li data-id="${a.alert_id}" class="${a.alert_id === S.selected ? "selected" : ""}">
      <span class="chip lvl-${st.level}"></span>
      <span>${esc(a.vessel_name || a.mmsi)}${a.simulated ? SIM_TAG : ""}</span>
      <span class="score">${st.score}</span>
      <span class="sub">${esc(a.alert_type)} · level ${LEVEL_TEXT[st.level]} · since ${fmtTime(a.created)}</span>
    </li>`).join("");
  for (const li of $("alert-list").querySelectorAll("li")) li.onclick = () => select(li.dataset.id);
}

function renderDetail(t) {
  const a = S.alerts.find((x) => x.alert_id === S.selected);
  const st = a && a.created <= t ? stateAt(a, t) : null;
  $("detail").hidden = !st;
  if (!st) return;
  const factors = a.factors.filter((f) => ms(f.added_at) <= t);
  $("detail-title").innerHTML = `${esc(a.vessel_name || "Unknown vessel")} · ${st.score}/100 ${a.simulated ? SIM_TAG : ""}`;
  $("detail-meta").textContent =
    `MMSI ${a.mmsi} · level ${LEVEL_TEXT[st.level]} · started ${fmtTime(ms(a.start_time))} · alert ${fmtTime(a.created)} · id ${a.alert_id}`;
  $("factors").innerHTML = factors.map((f) => `
    <div class="factor"><div class="row"><span>${esc(f.label)}${f.simulated ? SIM_TAG : ""}</span><b>+${f.points}</b></div>
    <div class="bar"><span style="width:${f.points}%"></span></div></div>`).join("") +
    `<div class="factor total"><div class="row"><span>Total (capped)</span><b>${st.score}</b></div>
     <div class="bar"><span style="width:${st.score}%"></span></div></div>`;
  $("detail-lines").innerHTML = factors.map((f) => {
    let extra = "";
    if (f.code === "acoustic_lowfreq") {
      extra = `<br><span style="color:#b48af0;font-size:11px;font-weight:bold;">[Signature: propeller @ 50 Hz]</span><br><a href="../out/spectrograms/lowfreq_tone.png" target="_blank" title="Click to view full spectrogram"><img src="../out/spectrograms/lowfreq_tone.png" style="width:220px;height:75px;margin-top:5px;border-radius:4px;display:block;border:1px solid #444;"></a>`;
    }
    return `<li>${esc(f.detail)}${extra}</li>`;
  }).join("");
  const u = st.unit_id && S.units[st.unit_id];
  $("recommendation").innerHTML = st.unit_id
    ? `<b>${esc(u ? u.name : st.unit_id)}</b> · ETA ${st.eta_min.toFixed(0)} min${u && u.simulated ? SIM_TAG : ""}`
    : "Not yet (the alert level is below the recommendation threshold).";
}

function select(id) {
  S.selected = id;
  const a = S.alerts.find((x) => x.alert_id === id);
  if (a) map.panTo([a.lat, a.lon]);
  render();
}

// ---------- redare ----------
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
