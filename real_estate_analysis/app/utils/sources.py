import streamlit as st

SOURCES = {
    "etn": {
        "name": "GURS — Evidenca trga nepremičnin (ETN)",
        "url": "https://www.e-prostor.gov.si/",
        "opsi_url": "https://podatki.gov.si/dataset/evidenca-trga-nepremicnin",
        "description": "Uradni register kupoprodajnih poslov z nepremičninami v Sloveniji. Vir vseh transakcijskih podatkov (cene, lokacije, površine, tip nepremičnine).",
        "license": "Odprti podatki Slovenije (CC BY)",
        "filter_note": "Filtrirano na tržne posle (TRZNOST_POSLA ∈ {1, 2, 5}), bivanjske nepremičnine, 300 < €/m² < 15.000, površina > 5 m².",
    },
    "surs_place": {
        "name": "SURS — Povprečne mesečne neto plače",
        "url": "https://pxweb.stat.si/",
        "table": "Povprečne mesečne plače po dejavnostih (SKD 2008), Slovenija",
        "description": "Povprečna mesečna neto plača v Sloveniji za vsako leto 2015-2025.",
        "note": "Za regionalne razlike: SURS objavlja tudi povprečne plače po statističnih regijah (12 regij).",
    },
    "surs_populacija": {
        "name": "SURS — Število prebivalcev po občinah",
        "url": "https://pxweb.stat.si/pxweb/sl/stat/stat__05__prebivalstvo__10__stevilo_preb__05__05C40__/05C4002S.px/",
        "table": "05C4002S — Prebivalstvo po starosti in spolu, občine, 1. januar",
        "description": "Število prebivalcev na 1. januar vsako leto, uporabljeno za izračun intenzitete trga (transakcije na 1.000 prebivalcev).",
    },
    "ecb_rate": {
        "name": "ECB — Key ECB interest rates (Main refinancing operations)",
        "url": "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html",
        "description": "Glavna refinanciranje obrestna mera ECB za vsako leto (povprečje veljavnih stopenj). Uporabljeno kot baza za hipotekarne obresti.",
        "note": "Bančni pribitek (margin) na obrestno mero ECB predpostavljamo +1,5 do +2,0 odstotne točke, kar je tipično za stanovanjske kredite v Sloveniji.",
    },
    "bs_obresti": {
        "name": "Banka Slovenije — Statistika obrestnih mer",
        "url": "https://www.bsi.si/statistika/financne-institucije-in-trgi/obrestne-mere",
        "description": "Povprečne obrestne mere za stanovanjske kredite v Sloveniji. Uporabljeno za umeritev kalkulatorja in primerjavo z modelom ECB+pribitek.",
    },
    "bs_makroprev": {
        "name": "Banka Slovenije — Makrobonitetni ukrepi (LTV omejitev)",
        "url": "https://www.bsi.si/financna-stabilnost/makrobonitetna-politika",
        "description": "Banka Slovenije omejuje razmerje LTV (loan-to-value) na največ 80 % za stanovanjske kredite, kar pomeni minimalni polog 20 %. Naša predpostavka 20 % pologa izhaja iz tega regulativnega okvira.",
        "note": "Veljavni makrobonitetni okvir od 2023 dalje. Pred tem so banke imele bolj prilagodljive standarde.",
    },
    "eurostat_hicp": {
        "name": "Eurostat — Harmonised Index of Consumer Prices (HICP)",
        "url": "https://ec.europa.eu/eurostat/web/hicp",
        "description": "Letna stopnja inflacije za Slovenijo (HICP). Uporabljeno kot regresor v Prophet modelu napovedi cen.",
        "note": "Tudi SURS objavlja indeks cen življenjskih potrebščin (ICŽP), ki je metodološko zelo blizu HICP.",
    },
    "eurostat_burden": {
        "name": "Eurostat — Housing cost overburden rate",
        "url": "https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07a",
        "description": "Delež gospodinjstev, ki za bivanje porabi več kot 40 % razpoložljivega dohodka. V Sloveniji 2015-2024 je bil med 4-7 %, znatno pod EU povprečjem.",
        "note": "Eurostat referenca za 'housing cost burden' scenarij na strani Dostopnost.",
    },
}


def render_source_box(source_key: str):
    """Render a styled st.info box for a single source. Use in methodology expanders."""
    s = SOURCES[source_key]
    st.markdown(f"**{s['name']}**")
    st.markdown(f"*{s['description']}*")
    if "table" in s:
        st.markdown(f"📊 Tabela: `{s['table']}`")
    if "license" in s:
        st.markdown(f"📄 Licenca: {s['license']}")
    if "filter_note" in s:
        st.caption(f"🔍 {s['filter_note']}")
    st.markdown(f"🔗 [{s['url']}]({s['url']})")
    if "opsi_url" in s:
        st.markdown(f"🔗 OPSI: [{s['opsi_url']}]({s['opsi_url']})")
    if "note" in s:
        st.caption(s["note"])
