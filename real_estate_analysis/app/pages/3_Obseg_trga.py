import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.data_loader import load_data, OBCINE, BARVE, load_population

st.set_page_config(page_title="Obseg trga", page_icon="📈", layout="wide")

with st.sidebar:
    st.markdown("### 📈 Obseg trga")
    use_per1000 = st.toggle("Na 1.000 prebivalcev", value=False)
    obcine_sel = st.multiselect(
        "Občine",
        options=OBCINE,
        default=["LJUBLJANA", "MARIBOR", "CELJE", "KOPER", "KRANJ"],
    )

st.title("📈 Obseg trga — število transakcij")

st.info(
    "👈 **Na levi strani** lahko izberete občine in preklopite prikaz na transakcije na 1.000 prebivalcev.",
    icon="ℹ️",
)

st.markdown(
    "Obseg trga prikazuje število evidentiranih kupoprodajnih poslov z bivanjskimi nepremičninami "
    "(stanovanji in hišami) po posameznih občinah in letih. Vrednosti so izračunane iz surovih transakcij ETN "
    "po aplikaciji standardnih filtrov; opcijsko se normalizirajo s številom prebivalcev (SURS)."
)

if not obcine_sel:
    st.warning("Izberite vsaj eno občino.")
    st.stop()

df = load_data()
pop = load_population()

sub = df[df["OBCINA"].isin(obcine_sel) & df["LETO"].between(2015, 2025)]
counts = sub.groupby(["OBCINA", "LETO"]).size().reset_index(name="N")

if use_per1000:
    def get_pop(row):
        return pop.get(row["OBCINA"], {}).get(int(row["LETO"]), None)
    counts["POP"] = counts.apply(get_pop, axis=1)
    counts["VALUE"] = counts.apply(
        lambda r: r["N"] / r["POP"] * 1000 if r["POP"] and r["POP"] > 0 else None, axis=1
    )
    y_label = "Transakcije na 1.000 preb."
else:
    counts["VALUE"] = counts["N"]
    y_label = "Število transakcij"

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("Skupaj 2015–2025")
    total = counts.groupby("OBCINA")["VALUE"].sum().sort_values()
    fig_bar = go.Figure(go.Bar(
        x=total.values,
        y=[o.title() for o in total.index],
        orientation="h",
        marker_color=[BARVE.get(o, "#888") for o in total.index],
        hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
    ))
    fig_bar.update_layout(
        xaxis_title=y_label, yaxis_title="",
        template="plotly_white", height=420,
        margin=dict(l=10, r=10),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# RIGHT: yearly line chart
with col_right:
    st.subheader("Po letih")
    fig_line = go.Figure()
    for obcina in obcine_sel:
        sub_o = counts[counts["OBCINA"] == obcina].sort_values("LETO")
        color = BARVE.get(obcina, "#888")

        fig_line.add_trace(go.Scatter(
            x=sub_o["LETO"], y=sub_o["VALUE"],
            name=obcina.title(), line=dict(color=color, width=2),
            mode="lines+markers",
            hovertemplate=f"<b>{obcina.title()}</b><br>Leto: %{{x}}<br>Transakcij: %{{y:,.0f}}<extra></extra>",
        ))

    # Annotate 2022-2023 ECB effect
    fig_line.add_annotation(
        x=2022.5, y=1.0, yref="paper",
        text="Padec 2022–2023:<br>učinek dvigov ECB",
        showarrow=False, font=dict(size=10, color="#E74C3C"),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#E74C3C", borderwidth=1, borderpad=3,
        xanchor="center",
    )
    fig_line.update_layout(
        xaxis_title="Leto", yaxis_title=y_label,
        hovermode="x unified", template="plotly_white",
        height=420, legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig_line, use_container_width=True)

# Summary table
st.subheader("Pregled transakcij po občinah in letih")
pivot_table = counts.pivot(index="OBCINA", columns="LETO", values="VALUE").round(1)
pivot_table.index = [o.title() for o in pivot_table.index]
st.dataframe(pivot_table, use_container_width=True)

with st.expander("📋 Metodologija in viri"):
    st.markdown("#### Podatkovni viri")
    st.markdown("""
    - [https://ipi.eprostor.gov.si/jgp/data](https://ipi.eprostor.gov.si/jgp/data)
    - [https://podatki.gov.si/dataset/evidenca-trga-nepremicnin/resource/902ef494-56a7-486b-b8a2-958ad5cbab47](https://podatki.gov.si/dataset/evidenca-trga-nepremicnin/resource/902ef494-56a7-486b-b8a2-958ad5cbab47)
    - **SURS — Število prebivalcev po občinah:** [https://pxweb.stat.si/pxweb/sl/stat/stat__05__prebivalstvo__10__stevilo_preb__05__05C40__/05C4002S.px/](https://pxweb.stat.si/pxweb/sl/stat/stat__05__prebivalstvo__10__stevilo_preb__05__05C40__/05C4002S.px/)
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
