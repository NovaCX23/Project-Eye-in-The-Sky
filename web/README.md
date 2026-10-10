# web/ (Dev 5)

## Ce face
Pagină statică (Leaflet din CDN, JavaScript simplu, fără build) care redă `out/timeline.json`:
- harta cu infrastructura (aprox.), unitățile de patrulare (simulate), navele în mișcare;
- navă cu AIS oprit: marker gri și cerc de incertitudine care crește în timp (rata vine din pipeline, `metrics.uncertainty_km_per_h`);
- lista de alerte la momentul cursorului, scorul defalcat pe factori, liniile de explicație, unitatea recomandată cu ETA;
- slider de timp, play/pauză, viteză de redare, mod „Live” pentru `--watch`;
- etichete „SIMULAT” pentru tot ce e simulat și insigna „DATE SIMULATE”.

**Doar afișare.** Nicio regulă, prag sau scor nu se calculează aici.

## Fișiere
`index.html`, `app.js` (randare și redare), `loader.js` (transport: citește periodic `timeline.json`; singurul fișier
de schimbat pentru varianta A cu WebSocket), `style.css`.

## Consumă
`../out/timeline.json` (sau `?src=<cale>`), `../assets/infrastructure.geojson`, `../assets/patrol_units.json`.

## Rulare separată
```bash
python -m core.demo            # o dată, ca să existe out/timeline.json
python -m http.server 8000     # din rădăcina repo-ului
# http://localhost:8000/web/
```
Live: în alt terminal `python -m core.pipeline --watch`, apoi bifați „Live”.
Dalele hărții (OpenStreetMap) cer internet. Fără rețea, straturile SeaGrid se văd pe fundal gol.

## Sarcini (prioritizate)
1. P0: repetiția demo-ului: povestea trebuie să se vadă clar la 300× (alertă, scor care crește, unitate recomandată).
2. P1: linie de timp cu marcaje pentru momentele alertelor sub slider.
3. P1: evidențierea infrastructurii celei mai apropiate de alerta selectată.
4. P2: fundal de hartă offline (o imagine a coastei) pentru sala fără internet.
