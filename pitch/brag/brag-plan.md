# /brag plan: SeaGrid (49.5 s)

**Angle:** one story, two worlds. The video opens on the simulated demo (a cargo ship goes dark near a subsea cable
and the evidence stacks up to 100/100), then turns: "That was a simulation. This is the real sea." Real AIS off
Varna, a real Sentinel-1 radar pass, and the operator's one-click response. The outro line carries the thesis:
a ship can switch off its transponder, not the radar.

**Hook:** "A ship goes dark." The word *dark.* lands on the exact replay second SEA FALCON's AIS falls silent (07:29:26),
with a sonar ping on the ship.

**Honesty:** the demo is labelled "simulated demo" from the first frame; the live part names its real sources
(aisstream.io, Sentinel-1D 04:13 UTC); patrol units are labelled simulated; the outro footer says it all once more.
Every number on screen comes from the real timelines (`out/timeline.json` for the demo; core.live snapshots at
2026-10-12 10:45 and 09:30 UTC for the live scenes). The live radar pass predates the AIS recording, so the video
says "40 ships found from orbit", not that a dark vessel was caught.

**Tone:** cinematic-polished; dark navy, IBM Plex (the app's own fonts and colours), glass captions in the app's style.
**Duration:** 49.5 s at the user's request ("as long as you need to showcase, still catchy").

| # | Time | Scene | On screen | Audio |
|---|---|---|---|---|
| 1 | 0.0–3.5 | Hook | Demo map tight on SEA FALCON, 07:27 → 07:31. "A ship goes **dark.**" | swell, ping + sub on "dark." (2.13 s) |
| 2 | 3.5–7.5 | Reveal | SeaGrid lockup over the blurred map: "Watches the ships around the Black Sea's cables, pipelines and gas platforms." | Dm9 pad, brand ping |
| 3 | 7.5–12.0 | Flagged | 07:52 → 08:04; alert appears at 08:00, ring on the ship. "Silent, 1 km from a subsea cable. **Flagged.**" | arpeggio in, alert ping 10.5 s |
| 4 | 12.0–20.5 | Evidence | Push-in on the factor panel as +10, +15, +20 land (08:10, 08:20, 08:30) | full pulse; cue on each factor |
| 5 | 20.5–25.5 | Reappears | 09:30, speed-inconsistent reappearance, 100/100, patrol route | two-note + sub at 21.9 s |
| 6 | 25.5–27.3 | The turn | Cursor clicks **Live** in the header | click 26.4 s, music drops out |
| 7 | 27.3–32.8 | Real sea | "That was a simulation. / This is the real sea." then 86 real AIS ships off Varna | riser, boom on "real sea." (28.05 s) |
| 8 | 32.8–38.5 | Radar | Real Sentinel-1 image fades in over the live map. "40 ships found from orbit. On radar, no AIS? Dark vessel." | riser, boom on the image (33.9 s) |
| 9 | 38.5–44.5 | Respond | Zoom on the alert panel; clicks **Acknowledge & engage** (40.5 s), then **Copy tasking** → "Copied" (42.5 s) | two soft UI clicks |
| 10 | 44.5–49.5 | Outro | "A ship can switch off its transponder. / It can't switch off the radar." SeaGrid, sources footer | ping + sub on line 2 |

Transitions dip through `#0b131d`. Music: synthesized in `work/audio.py` (D minor, 112 BPM), effects tuned to the key
and sent to the same reverb.
