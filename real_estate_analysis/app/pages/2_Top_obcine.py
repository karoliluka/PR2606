import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.data_loader import load_data, OBCINE, BARVE
st.set_page_config(page_title="Top 10 občin", page_icon="🏙️", layout="wide")

with st.sidebar:
    st.markdown("### 🏙️ Top 10 občin")
    tip_sel = st.radio("Tip nepremičnine", ["Stanovanje", "Hiša", "Obe"], index=0)
    obcine_sel = st.multiselect(
        "Občine",
        options=OBCINE,
        default=["LJUBLJANA", "MARIBOR", "KOPER"],
    )
    show_national = st.checkbox("Prikaži nacionalno povprečje", value=True)
    use_median = st.toggle("Mediana (izklopljeno = povprečje)", value=True)

st.title("🏙️ Primerjava cen po top 10 občinah")

st.info(
    "👈 **Filtri** so dostopni v levem stranskem meniju — izberite tip nepremičnine, "
    "določite občine za primerjavo ter preklopite med mediano in povprečjem.",
    icon="ℹ️",
)

if not obcine_sel:
    st.warning("Izberite vsaj eno občino v stranskem meniju.")
    st.stop()

df = load_data()
agg_fn = "median" if use_median else "mean"
metric_label = "Mediana €/m²" if use_median else "Povprečje €/m²"


def build_pivot(tip: str) -> pd.DataFrame:
    sub = df[(df["TIP"] == tip) & df["OBCINA"].isin(obcine_sel) & df["LETO"].between(2015, 2025)]
    return sub.groupby(["OBCINA", "LETO"])["CENA_M2"].agg(agg_fn).unstack("OBCINA")


def build_national(tip: str) -> pd.Series:
    sub = df[(df["TIP"] == tip) & df["LETO"].between(2015, 2025)]
    return sub.groupby("LETO")["CENA_M2"].agg(agg_fn)


def draw_trend_chart(pivot: pd.DataFrame, national: pd.Series, title: str) -> go.Figure:
    fig = go.Figure()

    for obcina in pivot.columns:
        color = BARVE.get(obcina, "#888")
        fig.add_trace(go.Scatter(
            x=pivot.index, y=pivot[obcina],
            name=obcina.title(), line=dict(color=color, width=2),
            mode="lines+markers",
            hovertemplate=f"<b>{obcina.title()}</b><br>Leto: %{{x}}<br>€/m²: %{{y:,.0f}}<extra></extra>",
        ))

    if show_national and national is not None:
        fig.add_trace(go.Scatter(
            x=national.index, y=national.values,
            name="Nacionalno povprečje",
            line=dict(color="black", width=2, dash="dash"),
            mode="lines",
            hovertemplate="<b>Slovenija</b><br>Leto: %{x}<br>€/m²: %{y:,.0f}<extra></extra>",
        ))

    fig.update_layout(
        title=title, xaxis_title="Leto", yaxis_title=metric_label,
        hovermode="x unified", template="plotly_white", height=480,
        legend=dict(orientation="v", x=1.02, y=1),
    )
    return fig


# --- Main chart(s) ---
if tip_sel == "Obe":
    pivot_stan = build_pivot("Stanovanje")
    pivot_hisa = build_pivot("Hiša")
    nat_stan = build_national("Stanovanje") if show_national else None
    nat_hisa = build_national("Hiša") if show_national else None

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=["Stanovanja", "Hiše"], vertical_spacing=0.12)

    def add_traces_to_subplot(pivot, national, row):
        for obcina in pivot.columns:
            color = BARVE.get(obcina, "#888")
            fig.add_trace(go.Scatter(
                x=pivot.index, y=pivot[obcina],
                name=obcina.title(), line=dict(color=color, width=2),
                mode="lines+markers", showlegend=(row == 1),
                hovertemplate=f"<b>{obcina.title()}</b><br>€/m²: %{{y:,.0f}}<extra></extra>",
            ), row=row, col=1)
        if national is not None:
            fig.add_trace(go.Scatter(
                x=national.index, y=national.values,
                name="Nacionalno" if row == 1 else "Nacionalno (hiše)",
                line=dict(color="black", width=2, dash="dash"),
                showlegend=(row == 1),
                hovertemplate="<b>Slovenija</b><br>€/m²: %{y:,.0f}<extra></extra>",
            ), row=row, col=1)

    add_traces_to_subplot(pivot_stan, nat_stan, 1)
    add_traces_to_subplot(pivot_hisa, nat_hisa, 2)
    fig.update_layout(
        height=800, hovermode="x unified", template="plotly_white",
        title="Primerjava cen stanovanj in hiš po občinah",
        legend=dict(orientation="v", x=1.02, y=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    for label, pivot in [("Stanovanja", pivot_stan), ("Hiše", pivot_hisa)]:
        st.markdown(f"#### Primerjalna tabela — {label}")
        rows = []
        for obcina in pivot.columns:
            p15 = pivot[obcina].get(2015, np.nan)
            p24 = pivot[obcina].get(2024, np.nan)
            if pd.isna(p15) or pd.isna(p24):
                continue
            rast = (p24 - p15) / p15 * 100
            cagr = ((p24 / p15) ** (1 / 9) - 1) * 100
            rows.append({
                "Občina": obcina.title(),
                f"{metric_label} 2015": f"€ {p15:,.0f}",
                f"{metric_label} 2024": f"€ {p24:,.0f}",
                "Rast 2015→2024": f"+{rast:.1f}%",
                "CAGR": f"{cagr:.1f}%/leto",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

else:
    pivot = build_pivot(tip_sel)
    national = build_national(tip_sel) if show_national else None
    fig = draw_trend_chart(pivot, national, f"Trend cen — {tip_sel.lower()}a po občinah")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Primerjalna tabela")
    rows = []
    for obcina in pivot.columns:
        p15 = pivot[obcina].get(2015, np.nan)
        p24 = pivot[obcina].get(2024, np.nan)
        if pd.isna(p15) or pd.isna(p24):
            continue
        rast = (p24 - p15) / p15 * 100
        cagr = ((p24 / p15) ** (1 / 9) - 1) * 100
        rows.append({
            "Občina": obcina.title(),
            f"{metric_label} 2015": f"€ {p15:,.0f}",
            f"{metric_label} 2024": f"€ {p24:,.0f}",
            "Rast 2015→2024": f"+{rast:.1f}%",
            "CAGR (9 let)": f"{cagr:.1f}%/leto",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("ℹ️ Zakaj ločeno stanovanja in hiše?"):
    st.markdown("""
    **Stanovanja in hiše imata različno tržno dinamiko:**
    - **Stanovanja** so pogostejša in likvidnejša; bolj odzivna na demografske trende in hipotekarno dostopnost.
    - **Hiše** imajo manjšo ponudbo, so vezane na podeželje/predmestja in so manj standardizirana.
    - Skupna analiza bi mešala dve različni distribuciji in zakrivala trende.
    - Mednarodne primerjave (npr. Eurostat) pogosto ločijo med transakcijami v večstanovanjskih in individualnih stavbah.
    """)

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
