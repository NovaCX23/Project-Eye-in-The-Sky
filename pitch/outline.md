# SeaGrid: presentation outline (5–7 minutes)

1. **The problem (45 s).** The critical infrastructure in the Black Sea (platforms, pipelines, cables) is hard to monitor.
   Attacks on cables and pipelines often start with a vessel that "loses" its AIS or stays too long in one place.
2. **What SeaGrid does (45 s).** It fuses AIS, hydrophones and fibre sensors on the cable; it raises an alert with a score,
   an explanation and the unit to send. Explanations come from templates filled with the detector's numbers, not from an LLM.
3. **Live demo (2–3 min)**, on the page, at 300× speed. The alert panel follows the highest-scoring alert on its own;
   click an alert only to show another one. Times are simulated UTC.
   - 06:00–07:30: normal traffic: cargo ships towards Constanța, tankers at anchor, trawlers working the shelf,
     a pilot boat at the port entrance. No alerts on any of them.
   - 07:29: MV SEA FALCON goes dark near the North platform and the subsea cable: grey marker, the uncertainty circle grows.
   - 08:00: the alert appears after the 30 min threshold, medium score. The nearest infrastructure (the subsea cable)
     lights up on the map and is listed in the panel.
   - 08:10: FV NORTHERN DAWN loiters nearby: correlation, high score; patrol vessel Alfa is dispatched, the dashed line
     shows its ETA counting down.
   - 08:20–08:30: the hydrophone (propeller signature) and the fibre on the cable (SIMULATED) confirm: critical score.
     Alfa is on scene at 08:35.
   - 09:30: SEA FALCON reappears too close for its reported speed: "too slow"; Alfa is redirected to the new position.
   - Optional, if time allows: the scripted submerged contact SC-1 (SCRIPTED label, not scored by the pipeline) and the
     later alerts (position jump, cloned transponder, ship-to-ship rendezvous) that come from the evaluation anomalies.
4. **Numbers (45 s).** Only from `metrics.md` (held-out seed 1337): every injected anomaly detected (gap, loitering,
   position jump, rendezvous, identity spoofing), no false alarms on normal traffic, mean time to alert as in the table.
   Say that the data is synthetic.
5. **How it works (45 s).** See `architecture.md`: micro-batch, nothing from the future, thresholds in a single file,
   deterministic ids, a direct path to a live server.
6. **What's next (30 s).** Real AIS data, real sensors, sensor-only alerts, an ETA that routes around land.

Mandatory disclaimers: simulated data, approximate coordinates, fictitious units, the submerged-contact scenario is scripted.
