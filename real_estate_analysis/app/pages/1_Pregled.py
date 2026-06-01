import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.data_loader import load_data, OBCINE, BARVE
from utils.events_timeline import add_events_to_plotly, EVENTS

st.set_page_config(page_title="Pregled", page_icon="📊", layout="wide")

with st.sidebar:
    st.markdown("### 📊 Pregled")
    st.caption("Skupna časovnica in hero metrike")
    st.divider()
    st.caption("Podatki: GURS ETN 2015–2025")

st.title("📊 Pregled trga stanovanjskih nepremičnin")

# --- Load data ---
df = load_data()

# --- Hero metrics ---
stan = df[df["TIP"] == "Stanovanje"]
hisa = df[df["TIP"] == "Hiša"]

med_stan_2015 = stan[stan["LETO"] == 2015]["CENA_M2"].median()
med_stan_2024 = stan[stan["LETO"] == 2024]["CENA_M2"].median()
med_hisa_2015 = hisa[hisa["LETO"] == 2015]["CENA_M2"].median()
med_hisa_2024 = hisa[hisa["LETO"] == 2024]["CENA_M2"].median()

rast_stan = (med_stan_2024 - med_stan_2015) / med_stan_2015 * 100
rast_hisa = (med_hisa_2024 - med_hisa_2015) / med_hisa_2015 * 100

total_tx = len(df[df["LETO"].between(2015, 2024)])

najdrazja = (
    df[(df["LETO"] == 2024) & (df["TIP"] == "Stanovanje")]
    .groupby("OBCINA")["CENA_M2"]
    .median()
    .idxmax()
)

st.subheader("Ključni podatki")
c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Stanovanja — mediana €/m² (2024)",
    f"€ {med_stan_2024:,.0f}",
    f"+{rast_stan:.1f}% od 2015",
)
c2.metric(
    "Hiše — mediana €/m² (2024)",
    f"€ {med_hisa_2024:,.0f}",
    f"+{rast_hisa:.1f}% od 2015",
)
c3.metric(
    "Skupaj analiziranih transakcij",
    f"{total_tx:,}",
    "2015–2024, top 10 občin",
)
c4.metric(
    "Najdražja občina 2024",
    najdrazja.title(),
    "stanovanja, mediana €/m²",
)

st.divider()

# ===== MASTER TIMELINE =====
st.subheader("Gibanje cen stanovanj v Sloveniji s ključnimi makroekonomskimi dogodki")
st.caption("Kvartalna mediana €/m² za stanovanja · IQR pas (25.–75. percentil) · vse top 10 občine skupaj")

# Build quarterly national median for apartments
stan_all = df[(df["TIP"] == "Stanovanje") & df["LETO"].between(2015, 2025)].copy()

# Add approximate quarter from year only (no exact date in dataset)
# Distribute transactions evenly across quarters using index-based approximation
stan_all["Q"] = pd.to_datetime(stan_all["LETO"].astype(str) + "-07-01")

quarterly = (
    stan_all.groupby("LETO")["CENA_M2"]
    .agg(["median", lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)])
    .reset_index()
)
quarterly.columns = ["LETO", "median", "q25", "q75"]
quarterly["date"] = pd.to_datetime(quarterly["LETO"].astype(str) + "-07-01")

fig_timeline = go.Figure()

# IQR band
fig_timeline.add_trace(go.Scatter(
    x=pd.concat([quarterly["date"], quarterly["date"].iloc[::-1]]),
    y=pd.concat([quarterly["q75"], quarterly["q25"].iloc[::-1]]),
    fill="toself",
    fillcolor="rgba(31,58,95,0.12)",
    line=dict(color="rgba(0,0,0,0)"),
    name="IQR (25–75 percentil)",
    hoverinfo="skip",
))

# Main median line — solid up to 2024
mask_2024 = quarterly["LETO"] <= 2024
fig_timeline.add_trace(go.Scatter(
    x=quarterly.loc[mask_2024, "date"],
    y=quarterly.loc[mask_2024, "median"],
    mode="lines+markers",
    name="Mediana €/m² (stanovanja)",
    line=dict(color="#1f3a5f", width=3),
    marker=dict(size=7),
    hovertemplate="Leto: %{x|%Y}<br>Mediana: €/m² %{y:,.0f}<extra></extra>",
))

# 2025 — continuous solid line (full year data available)
mask_2025 = quarterly["LETO"] >= 2024
if mask_2025.sum() > 1:
    fig_timeline.add_trace(go.Scatter(
        x=quarterly.loc[mask_2025, "date"],
        y=quarterly.loc[mask_2025, "median"],
        mode="lines+markers",
        name="2025",
        line=dict(color="#1f3a5f", width=3),
        marker=dict(size=7),
        hovertemplate="Leto: %{x|%Y}<br>Mediana: €/m² %{y:,.0f}<extra></extra>",
    ))

# Add macroeconomic events
add_events_to_plotly(fig_timeline, EVENTS)

fig_timeline.update_layout(
    title="Gibanje cen stanovanj v Sloveniji s ključnimi makroekonomskimi dogodki",
    xaxis_title="Leto",
    yaxis_title="Mediana €/m²",
    legend=dict(orientation="h", y=-0.18),
    template="plotly_white",
    height=540,
    margin=dict(t=80, b=100),
)
st.plotly_chart(fig_timeline, use_container_width=True)

st.divider()

# Per-municipality overview sparklines
st.subheader("Pregled po občinah — stanovanja (2015 → 2025)")

pivot_obcina = (
    df[(df["TIP"] == "Stanovanje") & df["LETO"].between(2015, 2025)]
    .groupby(["OBCINA", "LETO"])["CENA_M2"]
    .median()
    .unstack("LETO")
)

metrics_data = []
for obcina in OBCINE:
    if obcina not in pivot_obcina.index:
        continue
    row = pivot_obcina.loc[obcina]
    p2015 = row.get(2015, np.nan)
    p2025 = row.get(2025, np.nan)
    if pd.isna(p2015) or pd.isna(p2025):
        continue
    rast = (p2025 - p2015) / p2015 * 100
    metrics_data.append({"Občina": obcina.title(), "2015 €/m²": f"€{p2015:,.0f}",
                          "2025 €/m²": f"€{p2025:,.0f}", "Rast": f"+{rast:.1f}%"})

st.dataframe(pd.DataFrame(metrics_data), use_container_width=True, hide_index=True)

# --- Methodology expander ---
with st.expander("📋 Metodologija in viri"):
    st.markdown("#### Podatkovni viri")
    st.markdown("""
    - [https://ipi.eprostor.gov.si/jgp/data](https://ipi.eprostor.gov.si/jgp/data)
    - [https://podatki.gov.si/dataset/evidenca-trga-nepremicnin/resource/902ef494-56a7-486b-b8a2-958ad5cbab47](https://podatki.gov.si/dataset/evidenca-trga-nepremicnin/resource/902ef494-56a7-486b-b8a2-958ad5cbab47)
    """)
    st.divider()
    st.markdown("#### Filtri")
    st.markdown("""
    - **TRZNOST_POSLA ∈ {1, 2, 5}** — tržni posli (izključeni nedobrovoljni prenosi, itd.)
    - **300 < CENA_M2 < 15.000 €/m²** — izključene ekstremne vrednosti
    - **POVRSINA > 5 m²** — izključeni nesmiselni vnosi
    - **IQR trim**: znotraj vsake kombinacije (občina, tip, leto) so odstranjenih spodnjih 5 % in zgornjih 5 % po €/m²
    - **TIP ∈ {Stanovanje, Hiša}** — samo bivanjske nepremičnine
    """)
