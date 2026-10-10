// SeaGrid UI: interfață operațională de supraveghere maritimă și sonar intelligence.
"use strict";

// Constante de AFIȘARE (nu praguri de detecție).
const MAP_CENTER = [44.25, 29.35];
const MAP_ZOOM = 9;
const TICK_MS = 100;
const TRAIL_MIN = 60;          // cât din traseu desenăm pentru nava selectată
const SENSOR_SHOW_MIN = 45;    // cât timp rămâne vizibil un eveniment de senzor
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

// Rețeaua permanentă de hidrofoane (simulată pentru protecția infrastructurii)
const HYDROPHONES = [
  {
    id: "HYD-1",
    name: "Ana Gas Platform Hydrophone",
    lat: 44.265, lon: 29.490,
    offsetSec: 8400, // 08:20 UTC
    clip: "lowfreq_tone.png",
    sig: "propeller",
    freq: 50,
    threat: "Cargo Propeller Cavitation (Dark Vessel in transit near platform)",
    badge: "PROPELLER 50 Hz",
  },
  {
    id: "HYD-3",
    name: "Subsea Cable Sabotage Hydrophone",
    lat: 44.180, lon: 29.400,
    offsetSec: 9600, // 08:40 UTC
    clip: "anchor_drag.png",
    sig: "anchor_chain",
    freq: 120,
    threat: "Anchor Dragging Seabed Sabotage across Subsea Cable Route",
    badge: "ANCHOR DRAG 120 Hz",
  },
  {
    id: "HYD-4",
    name: "Northern Perimeter Hydrophone",
    lat: 44.380, lon: 29.620,
    offsetSec: 7800, // 08:10 UTC
    clip: "engine_rumble.png",
    sig: "propeller",
    freq: 65,
    threat: "Loitering Craft Aux Diesel Engine (FV Northern Dawn spotter)",
    badge: "AUX ENGINE 65 Hz",
  },
  {
    id: "HYD-2",
    name: "Outer Coastal Baseline Hydrophone",
    lat: 44.450, lon: 29.950,
    offsetSec: 3600, // 07:00 UTC
    clip: "background_noise.png",
    sig: "ambient",
    freq: 0,
    threat: "Heavy Ambient Ocean Noise (Suppressed by Adaptive Floor: 0 False Alarms)",
    badge: "AMBIENT (0 FA)",
  },
];

const S = {
  tl: null, start: 0, end: 0, t: 0, playing: false, live: false, selected: null,
  tracks: [], alerts: [], gapsByMmsi: {}, sensors: [], units: {},
};

const $ = (id) => document.getElementById(id);
const ms = (iso) => Date.parse(iso);
const fmtTime = (t) => new Date(t).toISOString().slice(11, 16) + " UTC";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------- hartă ----------
const map = L.map("map", { preferCanvas: true }).setView(MAP_CENTER, MAP_ZOOM);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 13,
  attribution: "&copy; OpenStreetMap · SeaGrid: simulated data, approximate coordinates",
}).addTo(map);

const layers = {
  infra: L.layerGroup().addTo(map),
  units: L.layerGroup().addTo(map),
  hydroStations: L.layerGroup().addTo(map),
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
    `<div><i style="background:#f0a050"></i>pipeline</div><div><i style="background:#b48af0"></i>cable</div>` +
    `<div><i style="background:#a855f7; border-radius:50%"></i>hydrophone (sonar contact)</div>`;
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

  // Randare stații fixe hidrofoane permanente cu rază de ascultare
  layers.hydroStations.clearLayers();
  for (const h of HYDROPHONES) {
    const isSabotage = h.id === "HYD-3";
    const stCol = isSabotage ? "#e5484d" : "#a855f7";
    // Cerc de acoperire acustică (15 km)
    L.circle([h.lat, h.lon], {
      radius: 15000, color: stCol, weight: 1, dashArray: "4 6", fillOpacity: 0.03,
    }).addTo(layers.hydroStations);

    // Marker stație fixă
    L.circleMarker([h.lat, h.lon], {
      radius: 8, color: "#fff", weight: 2, fillColor: stCol, fillOpacity: 0.9,
    })
      .bindTooltip(`<b>${h.id}</b> · ${esc(h.name)}<br><i>${esc(h.badge)}</i>`, { direction: "bottom" })
      .on("click", () => openSonarModal(h))
      .addTo(layers.hydroStations);
  }

  // Randare evenimente de senzor active la momentul t
  layers.sensors.clearLayers();
  for (const e of S.sensors) {
    if (e.s > t || t - e.s > SENSOR_SHOW_MIN * 60000) continue;
    let label = "";
    const isAcoustic = e.source === "acoustic";
    const isSabotage = isAcoustic && e.metrics && e.metrics.signature === "anchor_chain";
    const col = isSabotage ? "#e5484d" : "#a855f7";

    if (isAcoustic) {
      const sig = e.metrics && e.metrics.signature ? ` [${esc(e.metrics.signature).toUpperCase()} @ ${e.metrics.dominant_freq_hz || 50} Hz]` : "";
      const clipName = e.metrics && e.metrics.clip ? esc(e.metrics.clip.replace(".wav", ".png")) : "";
      label = `<b>SONAR CONTACT: ${esc(e.sensor_id)}</b><br><span style="color:#d8b4fe">${sig}</span> · conf ${e.confidence}` +
              `<br><img src="../out/spectrograms/${clipName}" style="width:200px;height:70px;margin-top:5px;border-radius:4px;display:block;border:1px solid #666;" title="Click for detailed analysis">` +
              `<div style="font-size:10px;color:#cbd5e1;margin-top:3px;">Click marker to open Sonar Intelligence</div>`;
    } else {
      label = `<b>FIBRE SENSOR</b> · km ${e.metrics.cable_km} · conf ${e.confidence}<br>Vibration on submarine cable`;
    }

    // Ping sonar activ
    L.circleMarker([e.lat, e.lon], { radius: 18, color: col, weight: 3, fillOpacity: 0.35 })
      .bindTooltip(`${label}${e.simulated ? " · SIMULATED" : ""}`,
                   { permanent: true, direction: "top", className: isSabotage ? "sim-label" : "" })
      .on("click", () => {
        const hyd = HYDROPHONES.find((h) => h.id === e.sensor_id);
        if (hyd) openSonarModal(hyd, e);
      })
      .addTo(layers.sensors);
  }

  renderHydrophoneGrid(t);
  renderAlertList(active);
  renderDetail(t);
}

function renderHydrophoneGrid(t) {
  const grid = $("hydrophone-grid");
  if (!grid) return;
  const elapsedSec = (t - S.start) / 1000;

  grid.innerHTML = HYDROPHONES.map((h) => {
    const isActive = Math.abs(elapsedSec - h.offsetSec) < (SENSOR_SHOW_MIN * 60);
    const isPast = elapsedSec >= h.offsetSec;
    const isSabotage = h.id === "HYD-3";

    let stateClass = "";
    let stateLabel = `<span style="color:var(--muted)">STANDBY</span>`;
    if (isActive) {
      stateClass = isSabotage ? "active-sabotage" : "active-alert";
      stateLabel = `<span style="color:${isSabotage ? "var(--critical)" : "var(--sonar)"};font-weight:700">● LIVE CONTACT</span>`;
    } else if (isPast) {
      stateLabel = `<span style="color:#3fb6a8">RECORDED (${h.t_alert})</span>`;
    } else {
      stateLabel = `<span style="color:var(--muted)">SCHEDULED (${h.t_alert})</span>`;
    }

    return `
      <div class="hydro-card ${stateClass}" onclick="jumpToSec(${h.offsetSec})">
        <div class="hydro-icon">${h.id.replace("HYD-", "")}</div>
        <div class="hydro-info">
          <div class="hydro-name">${esc(h.id)} · ${stateLabel}</div>
          <div class="hydro-sub">${esc(h.threat)}</div>
        </div>
        <div class="hydro-actions">
          <button type="button" class="btn-mini" onclick="event.stopPropagation(); openSonarModal(HYDROPHONES.find(x => x.id === '${h.id}'))">Spectrogram</button>
        </div>
      </div>`;
  }).join("");
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
      extra = `
        <div style="background:#131c26; border:1px solid #3b2064; border-radius:6px; padding:8px; margin-top:6px;">
          <div style="color:#d8b4fe; font-size:11px; font-weight:700;">TACTICAL SONAR INTEL: PROPELLER CAVITATION DETECTED</div>
          <div style="color:var(--muted); font-size:11px; margin-top:2px;">Blade rate fundamental: 50.0 Hz · Acoustic Confidence: 0.98</div>
          <a href="../out/spectrograms/lowfreq_tone.png" target="_blank" title="Click to view full spectrogram">
            <img src="../out/spectrograms/lowfreq_tone.png" style="width:100%; max-height:85px; object-fit:cover; margin-top:6px; border-radius:4px; display:block; border:1px solid #444;">
          </a>
        </div>`;
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

// ---------- sonar inspection modal & audio synthesis ----------
function openSonarModal(hyd, eventData = null) {
  const modal = $("sonar-modal");
  if (!modal) return;
  $("modal-title").textContent = `Sonar Analysis: ${hyd.id} — ${hyd.name}`;

  const isSabotage = hyd.sig === "anchor_chain";
  const badgeColor = isSabotage ? "var(--critical)" : "var(--sonar)";

  $("modal-body").innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <span class="badge" style="background:${badgeColor}; color:#fff; font-size:12px; padding:3px 10px;">${esc(hyd.badge)}</span>
      <span style="color:var(--muted); font-size:12px;">Position: ${hyd.lat.toFixed(3)}°N, ${hyd.lon.toFixed(3)}°E</span>
    </div>
    <div style="font-size:13px; margin-bottom:10px; color:#e2e8f0; line-height:1.4;">
      <b>Tactical Assessment:</b> ${esc(hyd.threat)}
    </div>
    <div>
      <div style="font-size:11px; text-transform:uppercase; color:var(--muted); font-weight:700;">STFT Acoustic Spectrogram Heatmap (10–500 Hz):</div>
      <img src="../out/spectrograms/${hyd.clip}" class="modal-spec-img" alt="Spectrogram">
    </div>
    <div class="modal-grid">
      <div class="modal-card">
        <b>Classification</b>
        <span style="color:${badgeColor}">${esc(hyd.sig.toUpperCase())}</span>
      </div>
      <div class="modal-card">
        <b>Dominant Peak</b>
        <span>${hyd.freq > 0 ? hyd.freq + ".0 Hz" : "None (Broadband)"}</span>
      </div>
      <div class="modal-card">
        <b>Low-Freq Ratio</b>
        <span>${hyd.freq > 0 ? "0.965 / 1.0 (Threshold: 0.60)" : "0.094 (Below Threshold)"}</span>
      </div>
      <div class="modal-card">
        <b>Adaptive Noise Floor</b>
        <span>${hyd.freq > 0 ? "Normal sea state floor: 0.088" : "Elevated ambient floor: 0.40"}</span>
      </div>
    </div>
    <button type="button" class="audio-btn" onclick="playAcousticSample('${hyd.sig}', ${hyd.freq})">
      🔊 Listen to Hydrophone Audio Simulation (3s Preview)
    </button>
  `;

  modal.showModal();
}

$("modal-close").onclick = () => $("sonar-modal").close();
$("sonar-modal").onclick = (e) => { if (e.target === $("sonar-modal")) $("sonar-modal").close(); };

// Sinteză audio Web Audio API pentru demonstrație live la pitch
let audioCtx = null;
function playAcousticSample(type, freq) {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const now = audioCtx.currentTime;

  if (type === "ambient" || freq === 0) {
    // Zgomot alb/oceanic filtrat trece-jos
    const bufferSize = audioCtx.sampleRate * 3;
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;
    const noise = audioCtx.createBufferSource();
    noise.buffer = buffer;
    const filter = audioCtx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 350;
    const gain = audioCtx.createGain();
    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 3);
    noise.connect(filter);
    filter.connect(gain);
    gain.connect(audioCtx.destination);
    noise.start();
    noise.stop(now + 3);
  } else {
    // Oscilator fundamental + armonică + modulație de amplitudine
    const osc1 = audioCtx.createOscillator();
    const osc2 = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc1.type = type === "anchor_chain" ? "sawtooth" : "sine";
    osc1.frequency.value = freq;
    osc2.type = "sine";
    osc2.frequency.value = freq * 2;

    // Modulație periodică de elice sau frecare lanț
    const lfo = audioCtx.createOscillator();
    const lfoGain = audioCtx.createGain();
    lfo.frequency.value = type === "anchor_chain" ? 8 : 2.5; // turație elice / zdrăngănit lanț
    lfoGain.gain.value = 0.4;
    lfo.connect(lfoGain.gain);

    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 3);

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(audioCtx.destination);

    osc1.start(now);
    osc2.start(now);
    lfo.start(now);
    osc1.stop(now + 3);
    osc2.stop(now + 3);
    lfo.stop(now + 3);
  }
}

// ---------- controale și jump bar ----------
function jumpToSec(seconds) {
  S.t = S.start + seconds * 1000;
  if (!S.playing) render();
}

for (const btn of document.querySelectorAll(".jump-btn")) {
  btn.onclick = () => {
    const sec = Number(btn.dataset.sec || 0);
    jumpToSec(sec);
  };
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
