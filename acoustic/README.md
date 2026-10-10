# acoustic/ (Dev 3)

## Ce face
Detector de energie de joasă frecvență: pentru fiecare cadru de `acoustic.frame_s` secunde calculează raportul
dintre energia din banda `acoustic.band_hz` și energia totală (STFT cu librosa). Cadrele consecutive peste prag,
de cel puțin `min_event_s` secunde, devin un `SensorEvent` de tip `acoustic_lowfreq`.
Rezultatele sunt pre-calculate; pipeline-ul le citește filtrate după `now`.

## Clipuri
- `clips/manifest.json`: pentru fiecare clip, id-ul hidrofonului (simulat), poziția și `offset_min` față de `scenario.start`.
- `clips/background_noise.wav` și `clips/lowfreq_tone.wav`: SINTETICE, generate de `python -m acoustic.make_test_clips`
  (4 kHz, 20 s; zgomot alb vs. ton de 50 Hz + 100 Hz).
- **Clipuri reale:** nu descărcați seturi de date în repo. Puneți fișierele `.wav` primite de la organizatori în
  `acoustic/clips/real/` (ignorat de git) și adăugați în manifest o intrare cu `"file": "real/<nume>.wav"`,
  poziția senzorului, `offset_min` și `"simulated": false`.

## Consumă
Clipurile din manifest, `config.yaml` (`acoustic`, `scenario.start`).

## Produce
`out/acoustic_events.json`: listă de `SensorEvent` (`source="acoustic"`).

## Rulare separată
```bash
python -m acoustic.make_test_clips
python -m acoustic.analyze --out-dir out
python -m pytest acoustic
```
`librosa` se folosește doar în acest director.

## Sarcini (prioritizate)
1. P0: aflați ce clipuri și ce metadate (timp, poziție senzor) dau organizatorii.
2. P1: prag adaptiv față de zgomotul de fond al fiecărui hidrofon.
3. P1: încredere din durată și intensitate; ignorați tranzitorii scurți.
4. P2: banda caracteristică pentru elice vs. lanț de ancoră; spectrogramă salvată pentru pitch.
