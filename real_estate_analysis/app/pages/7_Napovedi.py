import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.data_loader import load_data, load_wages, load_ecb_rates, load_inflation

st.set_page_config(page_title="Napovedi", page_icon="🔮", layout="wide")

TOP5 = ["LJUBLJANA", "MARIBOR", "CELJE", "KOPER", "KRANJ"]

with st.sidebar:
    st.markdown("### 🔮 Napovedi 2026–2030")
    obcina = st.selectbox("Občina (top 5)", TOP5, index=0)
    tip = st.selectbox("Tip", ["Stanovanje", "Hiša"], index=0)
    st.divider()
    st.markdown("**Scenarij regresorjev 2025–2030**")
    ecb_2030 = st.slider("ECB obrestna mera 2030 (%)", 0.5, 6.0, 2.5, step=0.25)
    wage_growth = st.slider("Letna rast plač 2025–2030 (%)", -2.0, 8.0, 3.0, step=0.5)
    inflacija = st.slider("Inflacija 2025–2030 (%)", 0.0, 8.0, 2.0, step=0.25)

st.title("🔮 Napoved cen nepremičnin 2026–2030")

st.info(
    "👈 **Filtri** so dostopni v levem stranskem meniju — izberite občino in tip nepremičnine, "
    "ter nastavite scenarij regresorjev: ECB obrestno mero, letno rast plač in inflacijo za obdobje 2025–2030.",
    icon="ℹ️",
)

st.warning(
    "⚠️ **Opozorilo:** Napoved nepremičninskih cen je notorično težka. "
    "To so ilustracije scenarijev, **ne predikcije**. "
    "Model je kalibriran na zgodovinskih podatkih in ne pozna bodočih šokov. "
    "Glej omejitve spodaj.",
    icon="⚠️",
)

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

df = load_data()
wages = load_wages()
ecb = load_ecb_rates()
inflation = load_inflation()


@st.cache_data
def run_forecast(obcina_key, tip_key, ecb_2030_val, wage_growth_val, inflacija_val,
                 _df, _wages, _ecb, _inflation):
    """Fit Ridge regression on 2015–2024 and forecast 2025–2030 with scenario regressors."""
    sub = _df[(_df["OBCINA"] == obcina_key) & (_df["TIP"] == tip_key) & _df["LETO"].between(2015, 2024)]
    ym = sub.groupby("LETO")["CENA_M2"].median()

    hist_years = ym.index.values.astype(float)
    hist_y = ym.values.astype(float)

    X_hist = np.column_stack([
        hist_years - 2015,
        [_ecb.get(int(y), 0.0) for y in hist_years],
        [_inflation.get(int(y), 2.0) for y in hist_years],
        [_wages.get(int(y), 1500) for y in hist_years],
    ])

    scaler = StandardScaler()
    X_hist_s = scaler.fit_transform(X_hist)

    model = Ridge(alpha=1.0)
    model.fit(X_hist_s, hist_y)

    # Residual std for uncertainty bands
    sigma = np.std(hist_y - model.predict(X_hist_s))

    future_years = np.arange(2025, 2031, dtype=float)
    ecb_future = np.linspace(_ecb.get(2025, 2.65), ecb_2030_val, len(future_years))
    wage_2025 = _wages.get(2025, 1750)
    wage_future = [wage_2025 * (1 + wage_growth_val / 100) ** i for i in range(len(future_years))]

    X_future = np.column_stack([
        future_years - 2015,
        ecb_future,
        [inflacija_val] * len(future_years),
        wage_future,
    ])
    X_future_s = scaler.transform(X_future)
    yhat = model.predict(X_future_s)

    # Widen uncertainty with horizon (extrapolation penalty)
    horizon_factor = 1 + 0.15 * np.arange(len(future_years))
    yhat_upper = yhat + 1.28 * sigma * horizon_factor
    yhat_lower = yhat - 1.28 * sigma * horizon_factor

    future_df = pd.DataFrame({
        "year": future_years.astype(int),
        "ds": pd.to_datetime([f"{int(y)}-07-01" for y in future_years]),
        "yhat": yhat,
        "yhat_upper": yhat_upper,
        "yhat_lower": yhat_lower,
    })

    hist_df = pd.DataFrame({
        "ds": pd.to_datetime([f"{int(y)}-07-01" for y in hist_years]),
        "y": hist_y,
    })

    return future_df, hist_df


# --- Data check ---
sub_check = df[(df["OBCINA"] == obcina) & (df["TIP"] == tip) & df["LETO"].between(2015, 2024)]
yearly_med = sub_check.groupby("LETO")["CENA_M2"].median()

if len(yearly_med) < 5:
    st.error(f"Premalo podatkov za {obcina.title()} ({tip}) za zanesljivo napoved.")
    st.stop()

# --- Run model ---
with st.spinner("Računam napoved..."):
    forecast, tdf = run_forecast(
        obcina, tip, ecb_2030, wage_growth, inflacija,
        df, wages, ecb, inflation,
    )
PROPHET_OK = True

# --- Forecast chart ---
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=tdf["ds"], y=tdf["y"],
    name="Dejanske cene", mode="lines+markers",
    line=dict(color="#1f3a5f", width=3),
    marker=dict(size=8),
    hovertemplate="Dejanska cena<br>Leto: %{x|%Y}<br>€/m²: %{y:,.0f}<extra></extra>",
))

fig.add_trace(go.Scatter(
    x=pd.concat([forecast["ds"], forecast["ds"].iloc[::-1]]),
    y=pd.concat([forecast["yhat_upper"], forecast["yhat_lower"].iloc[::-1]]),
    fill="toself",
    fillcolor="rgba(31,58,95,0.15)",
    line=dict(color="rgba(0,0,0,0)"),
    name="80% interval zaupanja",
    hoverinfo="skip",
))

fig.add_trace(go.Scatter(
    x=forecast["ds"], y=forecast["yhat"],
    name=f"Napoved (ECB→{ecb_2030}%, plače+{wage_growth}%/leto, inflacija {inflacija}%)",
    line=dict(color="#E53935", width=3, dash="dash"),
    mode="lines+markers",
    marker=dict(size=7),
    hovertemplate="Napoved<br>Leto: %{x|%Y}<br>€/m²: %{y:,.0f}<extra></extra>",
))

val_2030 = forecast[forecast["year"] == 2030]["yhat"].values
if len(val_2030):
    fig.add_annotation(
        x="2030-07-01", y=val_2030[0],
        text=f"2030: €{val_2030[0]:,.0f}/m²",
        showarrow=True, arrowhead=2,
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#E53935", borderwidth=1,
        font=dict(color="#E53935", size=12),
    )

fig.update_layout(
    title=f"Napoved cen — {obcina.title()}, {tip}, 2026–2030",
    xaxis_title="Leto", yaxis_title="€/m²",
    template="plotly_white", height=500,
    legend=dict(orientation="h", y=-0.2),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

future_table = forecast[forecast["year"] >= 2026][
    ["year", "yhat", "yhat_lower", "yhat_upper"]
].copy()
future_table = future_table.rename(columns={
    "year": "Leto",
    "yhat": "Napoved €/m²",
    "yhat_lower": "Spodnja meja (80%)",
    "yhat_upper": "Zgornja meja (80%)",
})
future_table[["Napoved €/m²", "Spodnja meja (80%)", "Zgornja meja (80%)"]] = (
    future_table[["Napoved €/m²", "Spodnja meja (80%)", "Zgornja meja (80%)"]].round(0).astype(int)
)
st.dataframe(future_table, use_container_width=True, hide_index=True)

# --- Limitations ---
st.divider()
st.subheader("⚠️ Omejitve modela")
st.markdown("""
- **Nepremičninski trg je odvisen od zunanjih šokov, ki jih ni mogoče napovedati** (finančne krize, pandemije, geopolitika).
- **Model predpostavlja, da bodo regresijski vplivi v prihodnosti podobni preteklim** — to je v turbulentnem obdobju vprašljivo.
- **Manjše občine imajo manjše vzorce in višjo variabilnost** — zato je napoved omejena na top 5 občin.
- **Letni podatki** (ne mesečni) omejujejo sezonsko analizo.
- Model je treniran na 2015–2024 (~9 podatkovnih točk) — visoka negotovost pri daljših horizontih.
""")

with st.expander("📋 Viri"):
    st.markdown("""
    - **ETN/GURS** — transakcijski podatki: [e-prostor.gov.si](https://www.e-prostor.gov.si/) · [podatki.gov.si](https://podatki.gov.si/dataset/evidenca-trga-nepremicnin)
    - **ECB** — obrestne mere: [ecb.europa.eu](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html)
    - **Eurostat HICP** — inflacija: [ec.europa.eu/eurostat](https://ec.europa.eu/eurostat/web/hicp)
    - **SURS** — povprečne neto plače: [pxweb.stat.si](https://pxweb.stat.si/)
    """)
