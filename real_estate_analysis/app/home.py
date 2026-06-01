import streamlit as st

with st.sidebar:
    st.image("https://www.fri.uni-lj.si/sites/default/files/FRI_logo_2015.png", width=140)
    st.markdown("### 🏠 Nepremičninski trg SLO")
    st.markdown("**Predmet:** Podatkovno rudarjenje")
    st.markdown("**Letnik:** 2025/26, FRI")
    st.markdown("**Podatki:** ETN/GURS 2015–2025")
    st.divider()
    st.caption("Navigacija → strani v meniju levo")

st.title("🏠 Analiza slovenskega nepremičninskega trga (2015–2025)")
st.subheader("Podatkovno rudarjenje — FRI 2025/26")

st.markdown("""
Cene nepremičnin v Sloveniji so v zadnjem desetletju doživele eno najburnejših obdobij v zgodovini trga.
Med letoma 2015 in 2025 se je mediana cene stanovanj na kvadratni meter po celotni Sloveniji več kot podvojila,
hkrati pa je trg prešel skozi več makroekonomskih šokov: pandemijo COVID-19, vojno v Ukrajini, energetsko krizo
in najhitrejši cikel dvigov obrestnih mer ECB v zgodovini evroobmočja.

V tej projektni nalogi smo analizirali evidenco trga nepremičnin (ETN) Geodetske uprave RS za obdobje 2015–2025,
s poudarkom na desetih slovenskih občinah z največjim obsegom poslov, osredotočili pa smo se na bivanjske
nepremičnine (stanovanja in hiše). Iščemo odgovore na štiri ključna vprašanja: kako se je gibanje cen razlikovalo
med občinami in tipi nepremičnin; kdaj so se zgodili največji preobrati in s katerimi makroekonomskimi dogodki
sovpadajo; kakšna je dostopnost stanovanj za povprečnega prebivalca v različnih scenarijih financiranja; in kaj
lahko pričakujemo v naslednjih petih letih. Cilj je prepoznati ključne vzorce v podatkih in jih kontekstualizirati
z makroekonomskimi gibanji, ne pa zgolj opisati gibanja cen.
""")

st.info(
    "👈 **Izberite stran** v levem meniju za analizo.\n\n"
    "Za začetek priporočamo **Pregled** — skupno časovnico z makroekonomskimi dogodki.",
    icon="ℹ️",
)

# Quick navigation cards
st.divider()
st.subheader("Pregled vsebine")

st.markdown("""
<style>
div[data-testid="stButton"] > button {
    width: 100%;
    margin-top: 0;
    margin-bottom: 12px;
    background: #1f3a5f;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 0.85rem;
    padding: 6px 0;
}
div[data-testid="stButton"] > button:hover {
    background: #2e5491;
    color: white;
}
</style>
""", unsafe_allow_html=True)

cols = st.columns(4)
nav_items = [
    ("📊", "1 — Pregled", "Skupna časovnica, hero metrike, makroekonomski kontekst", "pages/1_Pregled.py"),
    ("🏙️", "2 — Top 10 občin", "Interaktivna primerjava trendov cen po občinah", "pages/2_Top_obcine.py"),
    ("📈", "3 — Obseg trga", "Število transakcij, intenziteta trga", "pages/3_Obseg_trga.py"),
    ("🗓️", "4 — Letne spremembe", "Heatmap YoY sprememb cen", "pages/4_Letne_spremembe.py"),
    ("💶", "5 — Dostopnost", "3 scenariji hipotekarnega bremena", "pages/5_Dostopnost.py"),
    ("🗺️", "6 — Geografija", "Hexbin zemljevidi po občinah", "pages/6_Geografija_hexbin.py"),
    ("🔮", "7 — Napovedi", "Prophet model 2026–2030", "pages/7_Napovedi.py"),
    ("🧮", "8 — Kalkulator", "Personalizirani hipotekarni kalkulator", "pages/8_Kalkulator.py"),
]

for i, (icon, title, desc, page_path) in enumerate(nav_items):
    with cols[i % 4]:
        st.markdown(f"""
        <div style="background:#f5f7fa;border-radius:10px;padding:16px;margin-bottom:8px;
                    border-left:4px solid #1f3a5f;min-height:110px;">
            <div style="font-size:1.5rem">{icon}</div>
            <div style="font-weight:700;font-size:0.95rem;color:#1f3a5f">{title}</div>
            <div style="font-size:0.82rem;color:#555;margin-top:4px">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Odpri →", key=page_path):
            st.switch_page(page_path)

st.divider()

st.markdown(
    "📄 Končno poročilo in vsi rezultati so dostopni na "
    "[GitHub repozitoriju projekta](https://github.com/karoliluka/PR2606/tree/main)."
)

st.caption(
    "Podatki: GURS ETN 2015–2025 · SURS · ECB · Eurostat | "
    "Projekt: Podatkovno rudarjenje, FRI Ljubljana, 2025/26"
)
