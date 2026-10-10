# SeaGrid: presentation outline (5–7 minutes)

1. **The problem (45 s).** The critical infrastructure in the Black Sea (platforms, pipelines, cables) is hard to monitor.
   Attacks on cables and pipelines often start with a vessel that "loses" its AIS or stays too long in one place.
2. **What SeaGrid does (45 s).** It fuses AIS, hydrophones and fibre sensors on the cable; it raises an alert with a score,
   an explanation and the unit to send. Explanations come from templates filled with the detector's numbers, not from an LLM.
3. **Live demo (2–3 min)**, on the page, at 300× speed:
   - normal traffic towards Constanța, vessels at anchor (no alerts);
   - MV SEA FALCON goes dark near the platform and the cable: grey marker, the uncertainty circle grows;
   - the alert appears after the 30 min threshold, medium score;
   - FV NORTHERN DAWN loiters nearby: correlation, high score, recommended unit with ETA;
   - the hydrophone and the fibre (SIMULATED) confirm: critical score;
   - SEA FALCON reappears too close for its reported speed: "too slow".
4. **Numbers (45 s).** From `metrics.md` (held-out seed): detection rate, false alarms, time to alert.
5. **How it works (45 s).** Micro-batch, nothing from the future, thresholds in a single file, deterministic ids,
   a direct path to a live server.
6. **What's next (30 s).** Real AIS data, real sensors, sensor-only alerts, an ETA that routes around land.

Mandatory disclaimers: simulated data, approximate coordinates, fictitious units.
