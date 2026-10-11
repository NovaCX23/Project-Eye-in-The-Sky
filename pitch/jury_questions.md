# Likely jury questions

Each answer is meant to take about 20 seconds. Numbers come only from `metrics.md` (held-out seed).

1. **How many false alarms do you raise on normal traffic?** Read the held-out row of `metrics.md`. The normal traffic
   includes slow vessels on purpose (tankers at anchor, trawlers, a pilot boat); the exclusion zones (anchorage, port
   corridor) and the coverage edge remove the typical sources of false alarms.
2. **How fast do you alert?** An AIS gap is detected when `now - last message > threshold` (30 min, configurable);
   the mean time to alert over all anomaly types is in `metrics.md`.
3. **What if the AIS is spoofed rather than switched off?** Three checks: the position-jump rule (impossible speed between
   two messages), the identity-spoofing rule (the same MMSI broadcasting from two far-apart places at almost the same
   time, i.e. a cloned transponder), and the speed check on reappearance, which flags both too fast and too slow.
4. **Where do the explanations come from? Do you use an LLM?** No. Fixed templates filled with the detector's numbers
   (distances, minutes, speeds, the acoustic signature and its frequency). The same input always gives the same text.
5. **Why should we trust the score?** It is additive and transparent: each factor has its own points, visible in the UI,
   all in a single `config.yaml`. The panel also shows the nearest protected infrastructure and its distance.
6. **Is the data real?** No, it is synthetic and labelled SIMULATED. The coordinates are approximate. The architecture
   accepts real AIS through an adapter in `data/loader.py`.
7. **How did you avoid "cheating" on the evaluation?** Thresholds are tuned on one seed and numbers are reported on
   another (held-out); the pipeline never reads data from the future (automated test).
8. **How does it scale to the whole coast / real time?** Micro-batch today; the live variant changes only the transport
   (input, output, the page loader). See `architecture.md`.
9. **What do you do with a vibration on the cable and no visible vessel?** Today it only raises the score of alerts in
   the area; the next step is an alert triggered by sensors alone.
10. **How do you choose the patrol unit?** Units move on their patrol routes. For each alert from "high" up, by priority,
    we pick the free unit with the lowest ETA from where it is right now (straight line, no routing around land yet).
    It heads to the vessel's last known position, is redirected if the vessel reappears elsewhere, and escorts it once on
    scene. One unit per alert.
11. **Fishing boats move slowly too. Why are they not flagged?** Trawling is slow but covers ground: the loitering rule needs
    both a low mean speed and a small area over a 45-minute window. The synthetic trawlers and the pilot boat raise no event.
    The demo's loitering vessel is a fishing boat that stays almost still near the cable, which is different.
12. **Is the submerged contact a real detection?** No. SC-1 and SC-2 are a hand-written scenario, shown with a SCRIPTED label to
    illustrate what low-cost sensors (hydrophones, magnetometer buoys, fibre) could add. They are not part of the pipeline
    or the metrics.
