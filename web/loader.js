// Transportul de date al interfeței (varianta B: fișier JSON reîncărcat periodic).
// În varianta A (WebSocket) se înlocuiește DOAR acest fișier; app.js primește la fel obiectul Timeline.
"use strict";

const SeaGridLoader = (() => {
  const params = new URLSearchParams(location.search);
  // Serviți rădăcina repo-ului (python -m http.server 8000) și deschideți /web/.
  const SRC = params.get("src") || "../out/timeline.json";
  const DEFAULT_RELOAD_S = 3;

  async function fetchTimeline() {
    const res = await fetch(`${SRC}?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`${SRC}: HTTP ${res.status}`);
    return res.json();
  }

  // onTimeline(tl) e apelat la prima încărcare și de fiecare dată când apare un batch nou.
  function start(onTimeline, onError) {
    let lastKey = null;
    let timer = null;
    async function tick() {
      try {
        const tl = await fetchTimeline();
        const key = `${tl.now}|${tl.batch_index}|${tl.mode}`;
        if (key !== lastKey) {
          lastKey = key;
          onTimeline(tl);
        }
        const every = (tl.reload_interval_s || DEFAULT_RELOAD_S) * 1000;
        timer = setTimeout(tick, every);
      } catch (err) {
        onError(err);
        lastKey = null; // la revenire, timeline-ul se reîncarcă și mesajul de eroare dispare
        timer = setTimeout(tick, DEFAULT_RELOAD_S * 1000);
      }
    }
    tick();
    return () => clearTimeout(timer);
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
    return res.json();
  }

  return { start, fetchJSON, SRC };
})();
