# Likely jury questions

1. **How many false alarms do you raise on normal traffic?** Answer from `metrics.md` (held-out). The exclusion zones (anchorage, port)
   and the coverage edge remove the typical sources.
2. **How fast do you alert?** An AIS gap is detected when `now - last message > threshold` (30 min, configurable);
   the mean time is in `metrics.md`.
3. **What if the AIS is spoofed rather than switched off?** The position-jump rule and the speed check on
   reappearance, in both directions.
4. **Where do the explanations come from? Do you use an LLM?** No. Fixed templates filled with the detector's numbers; reproducible.
5. **Why should we trust the score?** It is additive and transparent: each factor has its own points, visible in the UI,
   all in a single `config.yaml`.
6. **Is the data real?** No, it is synthetic and labelled SIMULATED. The coordinates are approximate. The architecture accepts real AIS
   through an adapter in `data/loader.py`.
7. **How did you avoid "cheating" on the evaluation?** Thresholds are tuned on one seed and numbers are reported on another (held-out);
   the pipeline never reads data from the future (automated test).
8. **How does it scale to the whole coast / real time?** Micro-batch today; the live variant changes only the transport
   (input, output, the page loader).
9. **What do you do with a vibration on the cable and no visible vessel?** Today it only raises the score of alerts in the area; the next step
   is an alert triggered by sensors alone.
10. **How do you choose the patrol unit?** Lowest ETA over great-circle distance (simplified: no routing around land).
