# Analiza slovenskega trga stanovanjskih nepremičnin 2015–2025

**Predmet:** Podatkovno rudarjenje
**Letnik:** 2025/26, FRI Ljubljana
**Skupina:** 06
- Povezava do aplikacije: https://nepremicnine-2015-2025.streamlit.app/

## Opis projekta

Streamlit aplikacija za analizo slovenskega trga stanovanjskih nepremičnin na osnovi podatkov ETN/GURS za obdobje 2015–2025, s poudarkom na top 10 občinah po obsegu poslov. Cilj projekta ni zgolj opisati gibanje cen, temveč jih kontekstualizirati z makroekonomskimi dogodki (COVID-19, vojna v Ukrajini, ECB cikel obrestnih mer, inflacija).

Aplikacija razčlenjuje slovenski nepremičninski trg skozi štiri ključna vprašanja:

1. **Kako** se je gibanje cen razlikovalo med občinami in tipi nepremičnin? (Ljubljana 2024: 4.026 €/m² vs. Velenje 2.034 €/m² — razpon skoraj 2.000 €/m²)
2. **Kdaj** so se zgodili največji preobrati? (Vrh rasti 2021–2022, ohlajanje po dvigih ECB obresti)
3. **Kakšna je dostopnost** stanovanj za povprečnega prebivalca? (Hipotekarni obrok za 60 m² stanovanje v Ljubljani: 44 % plače leta 2015 → ~80 % leta 2023)
4. **Kaj lahko pričakujemo** v naslednjih petih letih? (Prophet napovedi v treh scenarijih z ECB, inflacijo in plačami kot eksogenimi spremenljivkami)

Ključna ugotovitev: **glavni dejavnik upada dostopnosti niso bile cene, temveč dvigi obrestnih mer ECB med 2022 in 2023** — brez njih bi mesečni obrok v Ljubljani ostal blizu 55 % namesto 80 % neto plače.

## Zahteve za lokalno namestitev aplikacije streamlit

# Sistemske zahteve

Spodaj je seznam Python knjižnic, ki jih aplikacija uporablja, z minimalnimi verzijami.

## Seznam odvisnosti

| Knjižnica | Minimalna verzija | Namen |
|---|---|---|
| `streamlit` | `>=1.30` | Spletna aplikacija in interaktivni vmesnik |
| `pandas` | `>=2.0` | Obdelava in agregacija podatkov |
| `numpy` | `>=1.24` | Numerični izračuni |
| `plotly` | `>=5.18` | Interaktivni grafi in vizualizacije |
| `prophet` | `>=1.1` | Časovne napovedi cen 2026–2030 |
| `statsmodels` | `>=0.14` | Statistični modeli in regresije |
| `pyproj` | `>=3.6` | Pretvorba koordinatnih sistemov (D96 → WGS84) |
| `h3` | `>=3.7` | Hexbin geografska agregacija |

```bash
cd real_estate_analysis
pip install -r requirements.txt
```

### Podatki

Postavite datoteko `vsi_bivanski.csv` v mapo `data/raw/`:
```
data/
└── raw/
    └── vsi_bivanski.csv   ← ETN izvoz z GURS/OPSI
```

Podatki so dostopni na: https://podatki.gov.si/dataset/evidenca-trga-nepremicnin

### Zagon

```bash
streamlit run app.py
```

## Struktura

```
real_estate_analysis/
├── app.py                       # Domača stran + navigacija
├── pages/
│   ├── 1_Pregled.py             # Skupna časovnica + hero metrike
│   ├── 2_Top_obcine.py          # Interaktivni trend cen po občinah
│   ├── 3_Obseg_trga.py          # Obseg trga (transakcije)
│   ├── 4_Letne_spremembe.py     # YoY heatmap
│   ├── 5_Dostopnost.py          # 3 scenariji dostopnosti
│   ├── 6_Geografija_hexbin.py   # Hexbin zemljevidi
│   ├── 7_Napovedi.py            # Prophet napovedi 2026–2030
│   └── 8_Kalkulator.py          # Personalizirani kalkulator
├── utils/
│   ├── data_loader.py           # Nalaganje in čiščenje podatkov
│   ├── calculations.py          # Hipotekarni izračuni
│   ├── visualizations.py        # Reusable Plotly grafi
│   ├── events_timeline.py       # Makroekonomski dogodki
│   ├── sources.py               # Citati podatkovnih virov
│   └── geo.py                   # D96→WGS84, hexbin
├── data/raw/vsi_bivanski.csv
├── .streamlit/config.toml
└── requirements.txt
```

## Viri podatkov

### GURS — Evidenca trga nepremičnin (ETN)
Uradni register kupoprodajnih poslov. Vir vseh transakcijskih podatkov.
🔗 https://www.e-prostor.gov.si/
🔗 OPSI: https://podatki.gov.si/dataset/evidenca-trga-nepremicnin
Licenca: CC BY (Odprti podatki Slovenije)

### SURS — Povprečne mesečne neto plače
Povprečna mesečna neto plača, letno, Slovenija 2015–2025.
🔗 https://pxweb.stat.si/

### SURS — Število prebivalcev po občinah
Tabela 05C4002S, 1. januar vsako leto.
🔗 https://pxweb.stat.si/pxweb/sl/stat/stat__05__prebivalstvo__10__stevilo_preb__05__05C40__/05C4002S.px/

### ECB — Key ECB interest rates
ECB main refinancing operations rate, letno povprečje.
🔗 https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html

### Banka Slovenije — Obrestne mere in makrobonitetni ukrepi
Povprečne obrestne mere za stanovanjske kredite; LTV omejitev 80 %.
🔗 https://www.bsi.si/statistika/financne-institucije-in-trgi/obrestne-mere
🔗 https://www.bsi.si/financna-stabilnost/makrobonitetna-politika

### Eurostat — HICP inflacija
Letna stopnja inflacije za Slovenijo (HICP).
🔗 https://ec.europa.eu/eurostat/web/hicp

## Metodologija (povzetek)

- **Filtri ETN:** tržni posli (`TRZNOST_POSLA ∈ {1, 2, 5}` — vključuje vse oznake, ki so v različnih obdobjih predstavljale tržne posle zaradi sprememb GURS šifranta), bivanjske nepremičnine, 300 < €/m² < 15.000, površina > 5 m²
- **GURS šifrant TRZNOST_POSLA:** v opazovanem obdobju se je trikrat spremenil — 2015–2019 pretežno koda 1, 2020–2022 pretežno koda 2, 2025 pretežno koda 5. Za konsistentno definicijo tržnega posla vključujemo vse tri oznake.
- **IQR trim:** znotraj vsake (občina, tip, leto) odstranjeni spodnji in zgornji 5-percentil za odstranitev napak vnosa in ekstremnih primerov
- **Top 10 občin:** Ljubljana, Maribor, Celje, Koper, Kranj, Domžale, Novo Mesto, Velenje, Kamnik, Nova Gorica
- **Klasifikacija TIP:** na podlagi `DEJANSKA_RABA_DELA_STAVBE` (GURS šifre 111* = Hiša, 112*/47*/2* = Stanovanje)
- **CENA_M2:** izpeljana kot `POGODBENA_CENA_ODSKODNINA / POVRSINA_DELA_STAVBE`
- **Hipotekarni izračun:** 20-letni kredit, 20 % polog, obrestna mera = ECB + 2 % bančna marža
- **Prophet napovedi:** trije scenariji (optimistični, baseline, pesimistični) z eksogenimi spremenljivkami (ECB, inflacija HICP, povprečna plača); 80 % interval zaupanja
- **2025:** delni podatki — ETN zamik vnosa 3–6 mesecev; vizualno označeno s črtkanimi linijami

## Ključne ugotovitve

- **Cene stanovanj v Ljubljani so se v desetletju več kot podvojile** (2015: ~1.800 €/m² → 2024: 4.026 €/m²)
- **Razlika med najdražjo in najcenejšo občino se je več kot podvojila** (~950 €/m² leta 2015 → ~2.000 €/m² leta 2024) — slovenski trg postaja vedno bolj geografsko razslojen
- **Regionalno različen odziv na dvige obresti ECB:** Ljubljana je doživela le zmeren upad obsega poslov (–6,4 % 2022→2023, hitro okrevanje), Maribor pa hujši udarec (–32,7 % v dveh letih)
- **Padec obsega ni bil korekcija trga, temveč zamrznitev** — cene niso padle, prodajalci in kupci so se preprosto umaknili in čakali na nižje obresti
- **Leto 2025 prinaša znake okrevanja v vseh občinah** — sovpada z znižanjem ECB obresti

## Znane omejitve

- Analiza zajema samo top 10 občin po volumnu transakcij
- 2025 podatki niso zaključeni (ETN zamik 3–6 mesecev)
- Hexbin geolokacija: ~15 % transakcij brez koordinat ali z napačnimi koordinati
- Prophet napovedi temeljijo na le 10 letnih učnih točkah — visoko tveganje prenaučenosti; napovedi so ilustrativne, ne deterministične
- Kalkulator ne upošteva notarskih stroškov, davka in agencijskih provizij (+4–6 %)
- Trg hiš ima manjši vzorec (~20 % transakcij) in večjo volatilnost zaradi heterogenosti — interpretacije se osredotočamo predvsem na stanovanja
