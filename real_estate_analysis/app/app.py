import streamlit as st

st.set_page_config(
    page_title="Analiza slovenskega nepremičninskega trga (2015–2025)",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("home.py", title="Uvod / Opis analize", icon="🏠"),
    st.Page("pages/1_Pregled.py", title="Pregled", icon="📊"),
    st.Page("pages/2_Top_obcine.py", title="Top 10 občin", icon="🏙️"),
    st.Page("pages/3_Obseg_trga.py", title="Obseg trga", icon="📈"),
    st.Page("pages/4_Letne_spremembe.py", title="Letne spremembe", icon="🗓️"),
    st.Page("pages/5_Dostopnost.py", title="Dostopnost", icon="💶"),
    st.Page("pages/6_Geografija_hexbin.py", title="Geografija", icon="🗺️"),
    st.Page("pages/7_Napovedi.py", title="Napovedi", icon="🔮"),
    st.Page("pages/8_Kalkulator.py", title="Kalkulator", icon="🧮"),
])
pg.run()
