import logging
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from prophet import Prophet

from utils.data_loader import load_data, load_wages, load_ecb_rates, load_inflation

st.set_page_config(page_title="Napovedi", page_icon="🔮", layout="wide")

TOP5 = ["LJUBLJANA", "MARIBOR", "CELJE", "KOPER", "KRANJ"]

SCENARIJI = [
    {
        "ime": "Optimistični<br>(ECB pada, rast plač)",
        "color": "#27AE60",
        "fillcolor": "rgba(39,174,96,0.13)",
        "ecb_2030": 1.5,
        "wage_growth": 5.0,
        "inflacija": 1.5,
    },
    {
        "ime": "Osnovna napoved<br>(status quo)",
        "color": "#2980B9",
        "fillcolor": "rgba(41,128,185,0.13)",
        "ecb_2030": 2.5,
        "wage_growth": 3.0,
        "inflacija": 2.0,
    },
    {
        "ime": "Pesimistični<br>(recesija, stagflacija)",
        "color": "#E74C3C",
        "fillcolor": "rgba(231,76,60,0.13)",
        "ecb_2030": 4.5,
        "wage_growth": 1.0,
        "inflacija": 5.0,
    },
]

with st.sidebar:
    st.markdown("### 🔮 Napovedi 2026–2030")
    obcina = st.selectbox("Občina (top 5)", TOP5, index=0)
    tip = st.selectbox("Tip", ["Stanovanje", "Hiša"], index=0)

st.title("🔮 Napoved cen nepremičnin 2026–2030")

st.info(
    "**Filtri** so dostopni v levem stranskem meniju — izberite občino in tip nepremičnine. "
    "Graf prikazuje tri scenarije razvoja cen glede na različne makroekonomske pogoje."
)
st.warning(
    "**Opozorilo:** Napoved nepremičninskih cen je notorično težka. "
    "To so ilustracije scenarijev, **ne predikcije**. "
    "Model je kalibriran na 10 zgodovinskih točkah in ne pozna bodočih šokov. "
    "Glej omejitve spodaj."
)

df = load_data()
wages = load_wages()
ecb = load_ecb_rates()
inflation_data = load_inflation()

sub_check = df[(df["OBCINA"] == obcina) & (df["TIP"] == tip) & df["LETO"].between(2015, 2024)]
ym_check = sub_check.groupby("LETO")["CENA_M2"].median()
if len(ym_check) < 5:
    st.error(f"Premalo podatkov za {obcina.title()} ({tip}) za zanesljivo napoved.")
    st.stop()


@st.cache_data
def fit_prophet(obcina_key, tip_key, _df, _wages, _ecb, _inflation):
    sub = _df[(_df["OBCINA"] == obcina_key) & (_df["TIP"] == tip_key) & _df["LETO"].between(2015, 2024)]
    ym = sub.groupby("LETO")["CENA_M2"].median()

    train = pd.DataFrame({
        "ds": pd.to_datetime([f"{int(y)}-07-01" for y in ym.index]),
        "y": ym.values.astype(float),
        "ecb": [float(_ecb.get(int(y), 0.0)) for y in ym.index],
        "inflacija": [float(_inflation.get(int(y), 2.0)) for y in ym.index],
        "wage": [float(_wages.get(int(y), 1500)) for y in ym.index],
    })

    m = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,
        changepoint_prior_scale=0.05,
    )
    m.add_regressor("ecb")
    m.add_regressor("inflacija")
    m.add_regressor("wage")
    m.fit(train)
    return m, train


def make_forecast(model, sc, _ecb, _wages):
    future_years = list(range(2025, 2031))
    ecb_vals = np.linspace(_ecb.get(2025, 2.65), sc["ecb_2030"], len(future_years))
    wage_start = float(_wages.get(2025, 1750))
    wage_vals = [wage_start * (1 + sc["wage_growth"] / 100) ** i for i in range(len(future_years))]

    future = pd.DataFrame({
        "ds": pd.to_datetime([f"{y}-07-01" for y in future_years]),
        "ecb": ecb_vals,
        "inflacija": [float(sc["inflacija"])] * len(future_years),
        "wage": wage_vals,
    })
    fc = model.predict(future)
    fc["year"] = future_years
    return fc[["year", "ds", "yhat", "yhat_lower", "yhat_upper"]]


with st.spinner("Treniram Prophet model…"):
    prophet_model, train_df = fit_prophet(obcina, tip, df, wages, ecb, inflation_data)

forecasts = [make_forecast(prophet_model, sc, ecb, wages) for sc in SCENARIJI]

last_ds = train_df["ds"].iloc[-1]
last_y = float(train_df["y"].iloc[-1])

fig = go.Figure()

for sc, fc in zip(SCENARIJI, forecasts):
    fc_main = fc[fc["year"] >= 2026].reset_index(drop=True)

    # Confidence band (2024 anchor → 2030)
    band_ds = pd.concat([pd.Series([last_ds]), fc_main["ds"]], ignore_index=True)
    band_upper = pd.concat([pd.Series([last_y]), fc_main["yhat_upper"]], ignore_index=True)
    band_lower = pd.concat([pd.Series([last_y]), fc_main["yhat_lower"]], ignore_index=True)

    fig.add_trace(go.Scatter(
        x=pd.concat([band_ds, band_ds.iloc[::-1].reset_index(drop=True)]),
        y=pd.concat([band_upper, band_lower.iloc[::-1].reset_index(drop=True)]),
        fill="toself",
        fillcolor=sc["fillcolor"],
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Dashed bridge: 2024 → 2025
    fc_2025 = fc[fc["year"] == 2025]
    if not fc_2025.empty:
        fig.add_trace(go.Scatter(
            x=[last_ds, fc_2025["ds"].iloc[0]],
            y=[last_y, float(fc_2025["yhat"].iloc[0])],
            mode="lines",
            line=dict(color=sc["color"], width=2, dash="dash"),
            showlegend=False,
            hoverinfo="skip",
        ))

    # Forecast line 2026–2030
    line_ds = pd.concat([pd.Series([last_ds]), fc_main["ds"]], ignore_index=True)
    line_y = pd.concat([pd.Series([last_y]), fc_main["yhat"]], ignore_index=True)

    fig.add_trace(go.Scatter(
        x=line_ds,
        y=line_y,
        mode="lines+markers",
        line=dict(color=sc["color"], width=2.5),
        marker=dict(size=8, symbol="square"),
        name=sc["ime"],
        hovertemplate=sc["ime"].replace("<br>", " ") + "<br>Leto: %{x|%Y}<br>€/m²: %{y:,.0f}<extra></extra>",
    ))

# Historical data (drawn last = on top)
fig.add_trace(go.Scatter(
    x=train_df["ds"],
    y=train_df["y"],
    mode="lines+markers",
    line=dict(color="#111111", width=3),
    marker=dict(size=9, symbol="circle"),
    name="Dejanska mediana (stanovanja)",
    hovertemplate="Dejanska cena<br>Leto: %{x|%Y}<br>€/m²: %{y:,.0f}<extra></extra>",
))

# Vertical dotted line at 2025
fig.add_vline(x="2025-01-01", line_dash="dot", line_color="#888", line_width=1.5)
fig.add_annotation(
    x="2025-04-01", y=0.04,
    xref="x", yref="paper",
    text="napoved →",
    showarrow=False,
    font=dict(size=11, color="#888"),
    xanchor="left",
)

fig.update_layout(
    title=dict(
        text=(
            f"Napoved mediane cen/m² za {tip.lower()} — 3 scenariji (2026–2030)<br>"
            "<sup>Model: Prophet + regresiji (ECB, inflacija, plača)</sup>"
        ),
        font=dict(size=16),
    ),
    xaxis_title="Leto",
    yaxis_title="Mediana €/m²",
    template="plotly_white",
    height=560,
    legend=dict(
        orientation="v", x=0.01, y=0.99,
        xanchor="left", yanchor="top",
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor="#ccc", borderwidth=1,
    ),
    hovermode="x unified",
    yaxis=dict(tickformat=",.0f €"),
    margin=dict(b=60),
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "△ Omejitev: 10 učnih točk, visoko tveganje prenaučenosti. Napovedi so ilustrativne.  \n"
    "Interval zaupanja: 80 %. Vir: GURS ETN | SURS (plače) | Eurostat (inflacija) | ECB SDW"
)

# Summary table
st.divider()
st.subheader("📋 Napovedi po scenarijih (2026–2030)")

table_rows = {"Leto": list(range(2026, 2031))}
for sc, fc in zip(SCENARIJI, forecasts):
    fc_main = fc[fc["year"] >= 2026]
    label = sc["ime"].replace("<br>", " ")
    table_rows[label] = [f"€ {v:,.0f}" for v in fc_main["yhat"]]

st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

st.divider()
st.subheader("⚠️ Omejitve modela")
st.markdown("""
- **Nepremičninski trg je odvisen od zunanjih šokov, ki jih ni mogoče napovedati** (finančne krize, pandemije, geopolitika).
- **Model predpostavlja, da bodo regresijski vplivi v prihodnosti podobni preteklim** — to je v turbulentnem obdobju vprašljivo.
- **Manjše občine imajo manjše vzorce in višjo variabilnost** — zato je napoved omejena na top 5 občin.
- **Letni podatki** (ne mesečni) omejujejo sezonsko analizo.
- Model je treniran na 2015–2024 (~10 podatkovnih točk) — visoka negotovost pri daljših horizontih.
""")

with st.expander("📋 Viri"):
    st.markdown("""
    - **ETN/GURS** — transakcijski podatki: [e-prostor.gov.si](https://www.e-prostor.gov.si/) · [podatki.gov.si](https://podatki.gov.si/dataset/evidenca-trga-nepremicnin)
    - **ECB** — obrestne mere: [ecb.europa.eu](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html)
    - **Eurostat HICP** — inflacija: [ec.europa.eu/eurostat](https://ec.europa.eu/eurostat/web/hicp)
    - **SURS** — povprečne neto plače: [pxweb.stat.si](https://pxweb.stat.si/)
    """)
