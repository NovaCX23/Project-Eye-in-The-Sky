# Întrebări probabile ale juriului

1. **Câte alarme false dați pe trafic normal?** Răspuns din `metrics.md` (held-out). Zonele de excludere (radă, port)
   și marginea acoperirii elimină sursele tipice.
2. **Cât de repede alertați?** Gaura AIS se detectează la `now - ultimul mesaj > prag` (30 min, configurabil);
   timpul mediu e în `metrics.md`.
3. **Ce se întâmplă dacă AIS-ul e falsificat, nu oprit?** Regula de salt de poziție și verificarea de viteză la
   reapariție, în ambele direcții.
4. **De unde vin explicațiile? Folosiți un LLM?** Nu. Șabloane fixe completate cu cifrele detectorului; reproductibile.
5. **De ce să avem încredere în scor?** E aditiv și transparent: fiecare factor are punctele lui, vizibile în interfață,
   toate într-un singur `config.yaml`.
6. **Datele sunt reale?** Nu, sintetice, marcate SIMULAT. Coordonatele sunt aproximative. Arhitectura acceptă AIS real
   printr-un adaptor în `data/loader.py`.
7. **Cum ați evitat să „trișați” la evaluare?** Pragurile se reglează pe un seed, cifrele se raportează pe altul (held-out);
   pipeline-ul nu citește niciodată date din viitor (test automat).
8. **Cum scalează la toată coasta / timp real?** Micro-batch azi; varianta live schimbă doar transportul
   (intrare, ieșire, încărcătorul paginii).
9. **Ce faceți cu o vibrație pe cablu fără nicio navă vizibilă?** Azi doar crește scorul alertelor din zonă; următorul pas
   e alerta pornită doar de senzori.
10. **Pe ce criteriu alegeți unitatea de patrulare?** ETA minim pe distanță pe cerc mare (simplificat: fără ocolirea uscatului).
