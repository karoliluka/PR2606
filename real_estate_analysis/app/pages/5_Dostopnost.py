import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.data_loader import load_data, OBCINE, BARVE, load_wages, load_ecb_rates
from utils.calculations import (
    mortgage_payment, mortgage_burden_pct, affordability_verdict,
    price_growth_decomposition, years_to_pay_salary_fraction,
)
st.set_page_config(page_title="Dostopnost", page_icon="💶", layout="wide")

BANK_MARGIN = 1.5  # ECB rate + this margin

with st.sidebar:
    st.markdown("### 💶 Dostopnost stanovanj")
    scenarij = st.selectbox(
        "Scenarij",
        [
            "S1: 100 % plače (referenčna meja)",
            "S2: Bančno priporočilo (33 % plače za obrok)",
            "S3: Trenutni hipotekarni obrok (ECB + pribitek)",
        ],
        index=0,
    )
    obcine_sel = st.multiselect("Občine", OBCINE,
                                default=["LJUBLJANA", "MARIBOR", "CELJE", "KOPER", "KRANJ"])
    povrsina = st.slider("Površina stanovanja (m²)", 30, 150, 60, step=5)
    compare_all = st.toggle("Primerjaj vse 3 scenarije (izb. občino)", value=False)
    if compare_all:
        obcina_cmp = st.selectbox("Občina za primerjavo", OBCINE, index=0)

YEARS = list(range(2015, 2025))

df = load_data()
wages = load_wages()
ecb = load_ecb_rates()


def get_median(obcina, leto):
    sub = df[(df["OBCINA"] == obcina) & (df["TIP"] == "Stanovanje") & (df["LETO"] == leto)]
    return sub["CENA_M2"].median()


st.title("💶 Dostopnost stanovanj — 3 scenariji")

st.info(
    "**Na levi strani** izberite scenarij, občine in površino stanovanja ter primerjajte rezultate.",
)

st.markdown("""
**Kaj prikazuje ta stran?**
Zanima nas, kako dostopna so stanovanja za povprečnega kupca — torej koliko časa ali plače mora
nameniti za nakup stanovanja. Ker je to odvisno od tega, *kako* financira nakup, ponujamo
**3 različne scenarije**:

| Scenarij | Opis |
|---|---|
| **S1 — 100 % plače** | Koliko let bi trajalo, da s *celotno* neto plačo odplačaš stanovanje. Mednarodna referenčna metrika (Price-to-Income Ratio). Nihče v resnici ne porabi 100 % plače za stanovanje — gre za primerjalno mero. |
| **S2 — 33 % plače** | Bančno priporočilo: mesečni obrok ne sme preseči tretjine neto plače. Prikazuje, koliko let bi trajalo odplačilo ob tej omejitvi. |
| **S3 — pravi hipotekarni obrok** | Simulacija realnega 20-letnega hipotekarnega kredita: 20 % lastni vložek, obrestna mera = ECB + 1,5 % bančni pribitek. Prikazuje, kolikšen delež mesečne neto plače odpade na obrok. |

**Ključni pojmi:**
- **Hipotekarni obrok** = mesečno plačilo banki za stanovanjski kredit (sestavljen iz vračila glavnice in obresti).
- **ECB obrestna mera** = osnovna obrestna mera Evropske centralne banke, od katere banke izračunajo ceno kredita (ECB + bančni pribitek ≈ vaša dejanska obrestna mera).
- **LTV 80 %** = razmerje med kreditom in vrednostjo nepremičnine; 20 % mora kupec prispevati sam (polog).
""")

if not obcine_sel:
    st.warning("Izberite vsaj eno občino.")
    st.stop()


# --- Compare all 3 scenarios mode ---
if compare_all:
    st.subheader(f"Primerjava vseh 3 scenarijev — {obcina_cmp.title()}, {povrsina} m²")

    data_s1, data_s2, data_s3 = [], [], []
    for yr in YEARS:
        med = get_median(obcina_cmp, yr)
        wage = wages.get(yr, None)
        rate = ecb.get(yr, 0.0) + BANK_MARGIN
        if pd.isna(med) or wage is None:
            continue
        total_price = med * povrsina
        annual_wage = wage * 12

        # S1
        s1_years = total_price / annual_wage
        data_s1.append({"LETO": yr, "value": s1_years, "Scenarij": "S1: 100% plače"})

        # S2
        s2_years = years_to_pay_salary_fraction(med, povrsina, wage, 0.333)
        data_s2.append({"LETO": yr, "value": s2_years, "Scenarij": "S2: 33% plače"})

        # S3 burden %
        principal = total_price * 0.80
        monthly_pay = mortgage_payment(principal, rate, 20)
        burden = mortgage_burden_pct(monthly_pay, wage)
        data_s3.append({"LETO": yr, "value": burden, "Scenarij": "S3: ECB + pribitek (%plače)"})

    fig_cmp = go.Figure()
    for data, color in [(data_s1, "#1E88E5"), (data_s2, "#FB8C00"), (data_s3, "#E53935")]:
        if not data:
            continue
        df_s = pd.DataFrame(data)
        fig_cmp.add_trace(go.Scatter(
            x=df_s["LETO"], y=df_s["value"],
            name=df_s["Scenarij"].iloc[0],
            mode="lines+markers",
            line=dict(color=color, width=2),
            hovertemplate=f"<b>{df_s['Scenarij'].iloc[0]}</b><br>Leto: %{{x}}<br>Vrednost: %{{y:.1f}}<extra></extra>",
        ))
    fig_cmp.update_layout(
        title=f"Dostopnost stanovanj — {obcina_cmp.title()}, {povrsina} m²",
        xaxis_title="Leto", yaxis_title="Vrednost (leta ali % plače)",
        template="plotly_white", height=450,
        hovermode="x unified",
    )
    st.plotly_chart(fig_cmp, use_container_width=True)
    st.caption("S1/S2 = leta za odplačilo, S3 = % mesečne plače za obrok")

    st.divider()


# --- Main scenario view ---
st.subheader(scenarij)

if "S1" in scenarij:
    st.info("""
    **S1 je teoretična referenca** — nihče ne nameni 100 % plače za stanovanje.
    Uporablja se kot enotna mednarodno primerljiva metrika (blizu PIR — Price-to-Income Ratio).
    """)
    rows = []
    for yr in YEARS:
        for obcina in obcine_sel:
            med = get_median(obcina, yr)
            wage = wages.get(yr, None)
            if pd.isna(med) or wage is None:
                continue
            total = med * povrsina
            s1_val = total / (wage * 12)
            rows.append({"OBCINA": obcina, "LETO": yr, "VALUE": s1_val})

    df_plot = pd.DataFrame(rows)
    fig = go.Figure()
    for obcina in obcine_sel:
        sub = df_plot[df_plot["OBCINA"] == obcina].sort_values("LETO")
        fig.add_trace(go.Scatter(
            x=sub["LETO"], y=sub["VALUE"],
            name=obcina.title(),
            line=dict(color=BARVE.get(obcina, "#888"), width=2),
            mode="lines+markers",
            hovertemplate=f"<b>{obcina.title()}</b><br>Leto: %{{x}}<br>Leta: %{{y:.1f}}<extra></extra>",
        ))
    fig.add_hline(y=10, line_dash="dash", line_color="orange",
                  annotation_text="10 let (mednarodna meja)", annotation_position="right")
    fig.update_layout(
        title=f"S1: Leta za odplačilo (100 % plače) — {povrsina} m²",
        xaxis_title="Leto", yaxis_title="Leta za odplačilo",
        template="plotly_white", height=450, hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

elif "S2" in scenarij:
    st.info("""
    **S2:** Bančno priporočilo — mesečni obrok ne sme preseči 33 % neto plače.
    Izračun predpostavlja linearno odplačilo brez obresti (konzervativna spodnja meja za leta).
    """)
    rows = []
    for yr in YEARS:
        for obcina in obcine_sel:
            med = get_median(obcina, yr)
            wage = wages.get(yr, None)
            if pd.isna(med) or wage is None:
                continue
            s2_val = years_to_pay_salary_fraction(med, povrsina, wage, 0.333)
            rows.append({"OBCINA": obcina, "LETO": yr, "VALUE": s2_val})

    df_plot = pd.DataFrame(rows)
    fig = go.Figure()
    for obcina in obcine_sel:
        sub = df_plot[df_plot["OBCINA"] == obcina].sort_values("LETO")
        fig.add_trace(go.Scatter(
            x=sub["LETO"], y=sub["VALUE"],
            name=obcina.title(),
            line=dict(color=BARVE.get(obcina, "#888"), width=2),
            mode="lines+markers",
            hovertemplate=f"<b>{obcina.title()}</b><br>Leto: %{{x}}<br>Leta: %{{y:.1f}}<extra></extra>",
        ))
    fig.update_layout(
        title=f"S2: Leta za odplačilo (33 % plače) — {povrsina} m²",
        xaxis_title="Leto", yaxis_title="Leta za odplačilo",
        template="plotly_white", height=450, hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

else:  # S3
    st.info("""
    **S3: Realni hipotekarni obrok** — 20-letni kredit, 20 % polog (LTV 80 %),
    obrestna mera = ECB + 1,5 % bančni pribitek.
    """)
    rows = []
    for yr in YEARS:
        for obcina in obcine_sel:
            med = get_median(obcina, yr)
            wage = wages.get(yr, None)
            rate = ecb.get(yr, 0.0) + BANK_MARGIN
            if pd.isna(med) or wage is None:
                continue
            total = med * povrsina
            principal = total * 0.80
            monthly = mortgage_payment(principal, rate, 20)
            burden = mortgage_burden_pct(monthly, wage)
            rows.append({
                "OBCINA": obcina, "LETO": yr,
                "BURDEN": burden, "MONTHLY": monthly, "PRICE": total,
                "RATE": rate,
            })

    df_plot = pd.DataFrame(rows)

    # Main burden chart
    fig = go.Figure()
    for obcina in obcine_sel:
        sub = df_plot[df_plot["OBCINA"] == obcina].sort_values("LETO")
        fig.add_trace(go.Scatter(
            x=sub["LETO"], y=sub["BURDEN"],
            name=obcina.title(),
            line=dict(color=BARVE.get(obcina, "#888"), width=2),
            mode="lines+markers",
            hovertemplate=(
                f"<b>{obcina.title()}</b><br>Leto: %{{x}}<br>"
                "Obrok kot % plače: %{y:.1f}%<extra></extra>"
            ),
        ))

    fig.add_hline(y=30, line_dash="dash", line_color="#27AE60",
                  annotation_text="30% — priporočena meja", annotation_position="right")
    fig.add_hline(y=40, line_dash="dash", line_color="#E74C3C",
                  annotation_text="40% — kritična meja", annotation_position="right")
    fig.add_vrect(x0=2021.5, x1=2022.5, fillcolor="rgba(231,76,60,0.08)", line_width=0)
    fig.add_annotation(x=2022, y=1.04, yref="paper",
                       text="ECB dvigi obresti", showarrow=False,
                       font=dict(size=10, color="#E74C3C"))

    fig.update_layout(
        title=f"S3: Hipotekarni obrok kot % neto plače — {povrsina} m², ECB+1,5%",
        xaxis_title="Leto", yaxis_title="% mesečne neto plače",
        template="plotly_white", height=480, hovermode="x unified",
        yaxis=dict(ticksuffix="%"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Decomposition: price vs rate effect for selected municipalities
    st.subheader("Razdelitev rasti obroka 2015 → 2024: cene vs. obresti")
    st.markdown(
        "Graf prikazuje, za koliko € na mesec se je povečal hipotekarni obrok med letoma 2015 in 2024 "
        "in kaj je k temu prispevalo: **rast cen nepremičnin** (modro), **dvig ECB obresti** (rdeče) "
        "ter **interakcija** (oranžno) — del rasti, ki nastane, ker sta se *hkrati* dvignila tako cena "
        "kot obrestna mera (ju ni mogoče pripisati samo enemu dejavniku)."
    )

    decomp_rows = []
    for obcina in obcine_sel:
        med15 = get_median(obcina, 2015)
        med24 = get_median(obcina, 2024)
        if pd.isna(med15) or pd.isna(med24):
            continue
        rate15 = ecb.get(2015, 0.05) + BANK_MARGIN
        rate24 = ecb.get(2024, 3.65) + BANK_MARGIN
        dec = price_growth_decomposition(
            med15 * povrsina, med24 * povrsina, rate15, rate24, years=20, polog_pct=0.20
        )
        decomp_rows.append({
            "obcina": obcina,
            "Rast cen (€/mes)": dec["price_contribution"],
            "Rast obresti (€/mes)": dec["rate_contribution"],
            "Interakcija (€/mes)": dec["interaction"],
        })

    if decomp_rows:
        df_dec = pd.DataFrame(decomp_rows)
        fig_dec = go.Figure()
        fig_dec.add_trace(go.Bar(
            x=[o.title() for o in df_dec["obcina"]],
            y=df_dec["Rast cen (€/mes)"],
            name="Rast cen",
            marker_color="#1E88E5",
            hovertemplate="<b>%{x}</b><br>Rast cen: +€%{y:,.0f}/mes<extra></extra>",
        ))
        fig_dec.add_trace(go.Bar(
            x=[o.title() for o in df_dec["obcina"]],
            y=df_dec["Rast obresti (€/mes)"],
            name="Dvig obresti (ECB)",
            marker_color="#E53935",
            hovertemplate="<b>%{x}</b><br>Dvig ECB obresti: +€%{y:,.0f}/mes<extra></extra>",
        ))
        fig_dec.add_trace(go.Bar(
            x=[o.title() for o in df_dec["obcina"]],
            y=df_dec["Interakcija (€/mes)"],
            name="Interakcija cene+obresti",
            marker_color="#FB8C00",
            hovertemplate="<b>%{x}</b><br>Interakcija (hkratni dvig cen in obresti): +€%{y:,.0f}/mes<extra></extra>",
        ))
        fig_dec.update_layout(
            barmode="stack",
            title="Razdelitev rasti mesečnega obroka 2015→2024 (€/mes)",
            xaxis_title="Občina", yaxis_title="€/mesec (rast)",
            template="plotly_white", height=400,
        )
        st.plotly_chart(fig_dec, use_container_width=True)

# Comparison table 2015 vs 2024
st.subheader("Primerjalna tabela 2015 vs. 2024")
table_rows = []
for obcina in obcine_sel:
    med15 = get_median(obcina, 2015)
    med24 = get_median(obcina, 2024)
    if pd.isna(med15) or pd.isna(med24):
        continue
    w15, w24 = wages.get(2015, 1013), wages.get(2024, 1680)
    r15 = ecb.get(2015, 0.05) + BANK_MARGIN
    r24 = ecb.get(2024, 3.65) + BANK_MARGIN
    p15 = mortgage_payment(med15 * povrsina * 0.8, r15, 20)
    p24 = mortgage_payment(med24 * povrsina * 0.8, r24, 20)
    table_rows.append({
        "Občina": obcina.title(),
        "Cena €/m² 2015": f"€ {med15:,.0f}",
        "Cena €/m² 2024": f"€ {med24:,.0f}",
        "Rast cene": f"+{(med24-med15)/med15*100:.1f}%",
        "Obrok 2015": f"€ {p15:,.0f}/mes",
        "Obrok 2024": f"€ {p24:,.0f}/mes",
        "% plače 2015": f"{p15/w15*100:.1f}%",
        "% plače 2024": f"{p24/w24*100:.1f}%",
    })
if table_rows:
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

with st.expander("📋 Metodologija in viri"):
    st.markdown("#### Podatkovni viri")
    st.markdown("""
    - **ETN (GURS):** [https://ipi.eprostor.gov.si/jgp/data](https://ipi.eprostor.gov.si/jgp/data)
    - **ETN (OPSI):** [https://podatki.gov.si/dataset/evidenca-trga-nepremicnin/resource/902ef494-56a7-486b-b8a2-958ad5cbab47](https://podatki.gov.si/dataset/evidenca-trga-nepremicnin/resource/902ef494-56a7-486b-b8a2-958ad5cbab47)
    - **SURS — povprečne mesečne neto plače po letih:** [https://pxweb.stat.si/](https://pxweb.stat.si/)
    - **ECB — glavna refinancirna obrestna mera:** [https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html)
    - **Banka Slovenije — obrestne mere za stanovanjske kredite in makrobonitetni ukrepi (LTV 80 %):** [https://www.bsi.si/statistika](https://www.bsi.si/statistika/financne-institucije-in-trgi/obrestne-mere)
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
    st.divider()
    st.markdown(f"""
    #### Predpostavke modela S3
    - Polog: 20 % (LTV 80 %, skladno z makrobonitetnim okvirom Banke Slovenije)
    - Doba kredita: 20 let
    - Obrestna mera: ECB main refi rate + {BANK_MARGIN} % bančni pribitek
    - Površina: {povrsina} m²
    - Mesečna plača: nacionalno povprečje (SURS)
    """)
