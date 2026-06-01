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

df = load_data()
wages = load_wages()
ecb = load_ecb_rates()
inflation = load_inflation()

# --- Prophet model (module-level so @st.cache_data key stays stable) ---
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


@st.cache_data
def run_prophet(obcina_key, tip_key, ecb_2030_val, wage_growth_val, inflacija_val,
                _df, _wages, _ecb, _inflation):
    """Fit Prophet on 2015–2024 data and forecast 2025–2030.

    _-prefixed args are excluded from the cache key (not hashable / stable by identity).
    """
    sub = _df[(_df["OBCINA"] == obcina_key) & (_df["TIP"] == tip_key) & _df["LETO"].between(2015, 2024)]
    ym = sub.groupby("LETO")["CENA_M2"].median()

    tdf = pd.DataFrame({
        "ds":        pd.to_datetime([f"{y}-07-01" for y in ym.index]),
        "y":         ym.values,
        "ecb_rate":  [_ecb.get(y, 0.0) for y in ym.index],
        "inflation": [_inflation.get(y, 2.0) for y in ym.index],
        "wage":      [_wages.get(y, 1500) for y in ym.index],
    })

    # n_changepoints=2: default 25 diverges with only ~9 yearly points
    m = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,
        n_changepoints=2,
        changepoint_prior_scale=0.05,
    )
    m.add_regressor("ecb_rate")
    m.add_regressor("inflation")
    m.add_regressor("wage")
    m.fit(tdf, algorithm="LBFGS")

    future_years = list(range(2025, 2031))
    ecb_future = np.linspace(_ecb.get(2025, 2.65), ecb_2030_val, len(future_years))
    wage_2025 = _wages.get(2025, 1750)
    wage_future = [wage_2025 * (1 + wage_growth_val / 100) ** i for i in range(len(future_years))]

    future_df = pd.DataFrame({
        "ds":        pd.to_datetime([f"{y}-07-01" for y in future_years]),
        "ecb_rate":  ecb_future,
        "inflation": [inflacija_val] * len(future_years),
        "wage":      wage_future,
    })

    all_rows = pd.concat([tdf[["ds", "ecb_rate", "inflation", "wage"]], future_df]).reset_index(drop=True)
    forecast = m.predict(all_rows)
    return forecast, tdf


# --- Data check ---
sub_check = df[(df["OBCINA"] == obcina) & (df["TIP"] == tip) & df["LETO"].between(2015, 2024)]
yearly_med = sub_check.groupby("LETO")["CENA_M2"].median()

if len(yearly_med) < 5:
    st.error(f"Premalo podatkov za {obcina.title()} ({tip}) za zanesljivo napoved.")
    st.stop()

# --- Run model ---
forecast = None
PROPHET_OK = False

if PROPHET_AVAILABLE:
    try:
        with st.spinner("Treniram Prophet model..."):
            forecast, tdf = run_prophet(
                obcina, tip, ecb_2030, wage_growth, inflacija,
                df, wages, ecb, inflation,
            )
        PROPHET_OK = True
    except Exception as e:
        st.warning(f"Prophet model ni uspel ({type(e).__name__}): {e}", icon="⚠️")

# --- Prophet chart ---
if PROPHET_OK and forecast is not None:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=tdf["ds"], y=tdf["y"],
        name="Dejanske cene", mode="lines+markers",
        line=dict(color="#1f3a5f", width=3),
        marker=dict(size=8),
        hovertemplate="Dejanska cena<br>Leto: %{x|%Y}<br>€/m²: %{y:,.0f}<extra></extra>",
    ))

    future_mask = forecast["ds"] >= "2024-07-01"
    fc_future = forecast[future_mask]

    fig.add_trace(go.Scatter(
        x=pd.concat([fc_future["ds"], fc_future["ds"].iloc[::-1]]),
        y=pd.concat([fc_future["yhat_upper"], fc_future["yhat_lower"].iloc[::-1]]),
        fill="toself",
        fillcolor="rgba(31,58,95,0.15)",
        line=dict(color="rgba(0,0,0,0)"),
        name="80% interval zaupanja",
        hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=fc_future["ds"], y=fc_future["yhat"],
        name=f"Napoved (ECB→{ecb_2030}%, plače+{wage_growth}%/leto, inflacija {inflacija}%)",
        line=dict(color="#E53935", width=3, dash="dash"),
        mode="lines+markers",
        marker=dict(size=7),
        hovertemplate="Napoved<br>Leto: %{x|%Y}<br>€/m²: %{y:,.0f}<extra></extra>",
    ))

    val_2030 = fc_future[fc_future["ds"].dt.year == 2030]["yhat"].values
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

    future_table = fc_future[fc_future["ds"].dt.year >= 2026][
        ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].copy()
    future_table["Leto"] = future_table["ds"].dt.year
    future_table = future_table.rename(columns={
        "yhat": "Napoved €/m²",
        "yhat_lower": "Spodnja meja (80%)",
        "yhat_upper": "Zgornja meja (80%)",
    })[["Leto", "Napoved €/m²", "Spodnja meja (80%)", "Zgornja meja (80%)"]]
    future_table[["Napoved €/m²", "Spodnja meja (80%)", "Zgornja meja (80%)"]] = (
        future_table[["Napoved €/m²", "Spodnja meja (80%)", "Zgornja meja (80%)"]].round(0).astype(int)
    )
    st.dataframe(future_table, use_container_width=True, hide_index=True)

else:
    # Fallback: simple linear extrapolation
    st.info("Prikazujem enostavno linearno napoved (trend + negotovost).")

    x = yearly_med.index.values.astype(float)
    y = yearly_med.values.astype(float)
    coefs = np.polyfit(x - 2015, y, 1)
    future_years = np.arange(2025, 2031)
    y_pred = np.polyval(coefs, future_years - 2015)
    residuals = y - np.polyval(coefs, x - 2015)
    sigma = np.std(residuals)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, name="Dejanske cene",
                             mode="lines+markers", line=dict(color="#1f3a5f", width=2)))
    fig.add_trace(go.Scatter(
        x=np.concatenate([future_years, future_years[::-1]]),
        y=np.concatenate([y_pred + 1.5 * sigma, (y_pred - 1.5 * sigma)[::-1]]),
        fill="toself", fillcolor="rgba(229,57,53,0.12)",
        line=dict(color="rgba(0,0,0,0)"), name="Ocena negotovosti (±1,5σ)",
    ))
    fig.add_trace(go.Scatter(x=future_years, y=y_pred,
                             name="Linearna napoved", mode="lines+markers",
                             line=dict(color="#E53935", width=2, dash="dash")))
    fig.update_layout(
        title=f"Linearna napoved — {obcina.title()}, {tip}",
        xaxis_title="Leto", yaxis_title="€/m²",
        template="plotly_white", height=450, hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Limitations ---
st.divider()
st.subheader("⚠️ Omejitve modela")
st.markdown("""
- **Nepremičninski trg je odvisen od zunanjih šokov, ki jih ni mogoče napovedati** (finančne krize, pandemije, geopolitika).
- **Prophet model predpostavlja, da bodo regresijski vplivi v prihodnosti podobni preteklim** — to je v turbulentnem obdobju vprašljivo.
- **Manjše občine imajo manjše vzorce in višjo variabilnost** — zato je napoved omejena na top 5 občin.
- **Letni podatki** (ne mesečni) omejujejo sezonsko analizo.
- Model je treniran na 2015–2024 (9 podatkovnih točk) — visoka negotovost.
""")

with st.expander("📋 Viri"):
    st.markdown("""
    - **ETN/GURS** — transakcijski podatki: [e-prostor.gov.si](https://www.e-prostor.gov.si/) · [podatki.gov.si](https://podatki.gov.si/dataset/evidenca-trga-nepremicnin)
    - **ECB** — obrestne mere: [ecb.europa.eu](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html)
    - **Eurostat HICP** — inflacija: [ec.europa.eu/eurostat](https://ec.europa.eu/eurostat/web/hicp)
    - **SURS** — povprečne neto plače: [pxweb.stat.si](https://pxweb.stat.si/)
    """)
