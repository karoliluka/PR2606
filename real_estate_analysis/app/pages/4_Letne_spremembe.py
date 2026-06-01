import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.data_loader import load_data, OBCINE
st.set_page_config(page_title="Letne spremembe", page_icon="🗓️", layout="wide")

with st.sidebar:
    st.markdown("### 🗓️ Letne spremembe")
    tip_sel = st.radio("Tip nepremičnine", ["Stanovanje", "Hiša", "Obe"], index=0)

zmax = 25

st.title("🗓️ Letne spremembe cen (YoY heatmap)")
st.caption("Sprememba mediane €/m² glede na predhodno leto, po občinah")

st.info(
    "**Filtri** so dostopni v levem stranskem meniju — izberite tip nepremičnine "
    "(stanovanja, hiše ali obe skupaj).",
)

df = load_data()

YEARS = list(range(2016, 2025))


def compute_yoy(tip_filter):
    sub = df[df["TIP"].isin(tip_filter) & df["LETO"].between(2015, 2024)]
    med = sub.groupby(["OBCINA", "LETO"])["CENA_M2"].median().unstack("LETO")

    yoy = pd.DataFrame(index=med.index, columns=YEARS, dtype=float)
    for yr in YEARS:
        if yr in med.columns and (yr - 1) in med.columns:
            prev = med[yr - 1]
            curr = med[yr]
            yoy[yr] = ((curr - prev) / prev * 100).round(1)

    # Sort by 2024 median price descending
    if 2024 in med.columns:
        order = med[2024].sort_values(ascending=False).index
        yoy = yoy.reindex(order)

    return yoy


if tip_sel == "Obe":
    yoy_stan = compute_yoy(["Stanovanje"])
    yoy_hisa = compute_yoy(["Hiša"])

    for label, yoy_df in [("Stanovanja", yoy_stan), ("Hiše", yoy_hisa)]:
        st.subheader(f"YoY spremembe — {label}")
        fig = go.Figure(go.Heatmap(
            z=yoy_df.values,
            x=[str(c) for c in yoy_df.columns],
            y=[o.title() for o in yoy_df.index],
            colorscale=[[0.0, "#27AE60"], [0.5, "#FFFFFF"], [1.0, "#E53935"]],
            zmid=0, zmin=-zmax, zmax=zmax,
            text=np.where(np.isnan(yoy_df.values), "", np.round(yoy_df.values, 1).astype(str) + "%"),
            texttemplate="%{text}",
            hovertemplate="<b>%{y}</b><br>Leto: %{x}<br>Sprememba: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="% YoY"),
        ))
        fig.update_layout(
            title=f"YoY spremembe cen — {label}",
            xaxis_title="Leto", yaxis_title="Občina",
            template="plotly_white", height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    yoy_df = compute_yoy([tip_sel])

    fig = go.Figure(go.Heatmap(
        z=yoy_df.values,
        x=[str(c) for c in yoy_df.columns],
        y=[o.title() for o in yoy_df.index],
        colorscale=[[0.0, "#27AE60"], [0.5, "#FFFFFF"], [1.0, "#E53935"]],
        zmid=0, zmin=-zmax, zmax=zmax,
        text=np.where(
            np.isnan(yoy_df.values.astype(float)),
            "",
            np.round(yoy_df.values.astype(float), 1).astype(str) + "%",
        ),
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b><br>Leto: %{x}<br>Sprememba: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="% YoY", ticksuffix="%"),
    ))
    fig.update_layout(
        title=f"YoY spremembe cen — {tip_sel}",
        xaxis_title="Leto", yaxis_title="Občina",
        template="plotly_white", height=440,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Auto-generated interpretation
    vals = yoy_df.values.astype(float)
    flat_vals = vals[~np.isnan(vals)]
    if len(flat_vals):
        max_idx = np.unravel_index(np.nanargmax(vals), vals.shape)
        min_idx = np.unravel_index(np.nanargmin(vals), vals.shape)
        max_obcina = yoy_df.index[max_idx[0]].title()
        max_leto = yoy_df.columns[max_idx[1]]
        min_obcina = yoy_df.index[min_idx[0]].title()
        min_leto = yoy_df.columns[min_idx[1]]
        max_val = vals[max_idx]
        min_val = vals[min_idx]

        col1, col2 = st.columns(2)
        col1.success(f"**Največja rast:** {max_obcina} v {max_leto}: **+{max_val:.1f}%**")
        col2.error(f"**Največji padec:** {min_obcina} v {min_leto}: **{min_val:.1f}%**")

    # Average YoY by year (mini line chart)
    st.subheader("Povprečna YoY sprememba po letih (vse občine)")
    avg_by_year = yoy_df.mean(axis=0)
    fig_avg = go.Figure(go.Bar(
        x=[str(y) for y in avg_by_year.index],
        y=avg_by_year.values,
        marker_color=["#27AE60" if v >= 0 else "#E53935" for v in avg_by_year.values],
        hovertemplate="Leto: %{x}<br>Povprečna sprememba: %{y:.1f}%<extra></extra>",
    ))
    fig_avg.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig_avg.update_layout(
        xaxis_title="Leto", yaxis_title="Povprečna YoY (%)",
        template="plotly_white", height=300,
    )
    st.plotly_chart(fig_avg, use_container_width=True)

with st.expander("ℹ️ Zakaj heatmap?"):
    st.markdown("""
    **Prednosti heatmap prikaza pred 10 ločenimi linijskimi grafi:**
    - Omogoča pregled vseh 10 občin × 9 let v enem pogledu (~90 vrednosti naenkrat)
    - Vzorci (npr. splošna rast 2020–2022, padec 2023) so takoj vidni
    - Divergentna barvna lestvica (zelena = padec, rdeča = rast) izpostavi izjeme
    - Sortiranje po ceni 2024 omogoča primerjavo dražjih in cenejših občin
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
