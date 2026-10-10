# SeaGrid: structura prezentării (5–7 minute)

1. **Problema (45 s).** Infrastructura critică din Marea Neagră (platforme, conducte, cabluri) e greu de supravegheat.
   Atacurile asupra cablurilor și conductelor încep adesea cu o navă care își „pierde” AIS-ul sau stă prea mult într-un loc.
2. **Ce face SeaGrid (45 s).** Fuzionează AIS, hidrofoane și senzori de fibră pe cablu; dă o alertă cu scor,
   explicație și unitatea de trimis. Explicațiile vin din șabloane cu cifrele detectorului, nu dintr-un LLM.
3. **Demo live (2–3 min)**, pe pagină, la viteza 300×:
   - trafic normal spre Constanța, nave la ancoră în radă (fără alerte);
   - MV SEA FALCON se stinge lângă platformă și cablu: marker gri, cercul de incertitudine crește;
   - alerta apare după pragul de 30 min, scor mediu;
   - FV NORTHERN DAWN staționează aproape: corelare, scor ridicat, unitate recomandată cu ETA;
   - hidrofonul și fibra (SIMULATE) confirmă: scor critic;
   - SEA FALCON reapare prea aproape pentru viteza raportată: „prea lent”.
4. **Cifre (45 s).** Din `metrics.md` (seed held-out): rata de detecție, alarme false, timpul până la alertă.
5. **Cum funcționează (45 s).** Micro-batch, nimic din viitor, praguri într-un singur fișier, id-uri deterministe,
   drum direct spre un server live.
6. **Ce urmează (30 s).** Date AIS reale, senzori reali, alerte doar din senzori, ETA care ocolește uscatul.

Mențiuni obligatorii: date simulate, coordonate aproximative, unități fictive.
