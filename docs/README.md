# SeaGrid pe scurt (TL;DR pentru oricine)

## Ce e asta?
Un program care stă de pază la „cablurile și țevile” României din Marea Neagră:
platforme de gaz, conducte, cabluri de internet de pe fundul mării și intrarea în portul Constanța.

Se uită la navele din zonă și strigă „atenție!” când una se poartă dubios.

## Ce înseamnă „dubios”?
- **Își stinge „GPS-ul public” (AIS).** Fiecare navă mare își anunță poziția prin radio. Dacă tace mai mult de 30 de minute lângă ceva important, e suspect.
- **Reapare unde nu trebuie.** Dacă zicea că merge cu 12 noduri, dar după 2 ore e mult prea aproape (sau prea departe), a făcut ceva între timp.
- **Stă pe loc unde n-are ce căuta.** O navă care se învârte încet deasupra unui cablu nu e la pescuit nevinovat.
- **„Sare” dintr-un loc în altul.** Poziția s-a mutat 25 km într-un minut: semnalul e falsificat.

Pe lângă nave, mai „ascultăm”:
- un **microfon subacvatic** (hidrofon), care aude zgomote joase de motor sau de ancoră târâtă;
- **fibra din cablu**, care simte vibrațiile când cineva umblă la el.

## Ce primești la final?
O **alertă** cu:
- un **scor de risc de la 0 la 100**: fiecare semn suspect adaugă puncte, iar pe ecran vezi exact câte și de ce;
- o **explicație în română**, de genul „AIS oprit 121 min, la 1 km de cablu, hidrofonul a auzit ceva”;
- **ce navă de patrulare să trimiți** și în cât timp ajunge.

## Povestea din demo
1. Cargoul **MV SEA FALCON** merge spre Constanța.
2. Lângă o platformă de gaz și un cablu, își oprește AIS-ul. Pe hartă devine gri și apare un cerc care tot crește: „e undeva aici”.
3. După 30 de minute sare prima alertă.
4. Aproape, pescadorul **FV NORTHERN DAWN** stă pe loc de mult. Cele două nave sunt legate între ele și scorul crește.
5. Hidrofonul aude ceva, fibra din cablu vibrează. Scorul devine **critic** și sistemul recomandă o navă de patrulare.
6. SEA FALCON reapare prea aproape pentru viteza pe care o declara: „prea lent”, deci s-a oprit undeva.

## Important
- **Totul e simulat.** Navele, senzorii și unitățile de patrulare sunt inventate și marcate **SIMULAT**.
- **Pozițiile platformelor și cablurilor sunt aproximative**, nu oficiale.
- **Explicațiile nu sunt scrise de un AI.** Sunt propoziții fixe completate cu cifrele detectorului.

## Cum îl pornesc? (3 pași)
```bash
python -m devtools.bootstrap      # o singură dată: instalează tot
python -m core.demo               # generează povestea
python -m http.server 8000        # apoi deschide http://localhost:8000/web/ și apasă ▶
```

Mai multe detalii: [README-ul principal](../README.md) · reguli pentru echipă: [AGENTS.md](../AGENTS.md)
