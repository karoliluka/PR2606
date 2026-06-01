import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.data_loader import load_data, OBCINE, load_wages, load_ecb_rates
from utils.calculations import mortgage_payment, mortgage_burden_pct, affordability_verdict

st.set_page_config(page_title="Kalkulator dostopnosti", page_icon="🧮", layout="wide")

BANK_MARGIN = 1.5

st.title("🧮 Kalkulator dostopnosti stanovanj")
st.caption("Personalizirani izračun hipotekarnega obroka in primerjava po občinah")

df = load_data()
wages = load_wages()
ecb = load_ecb_rates()

# --- Input form ---
st.subheader("⚙️ Vhodni parametri")
col_a, col_b, col_c = st.columns(3)
with col_a:
    placa = st.number_input("Neto mesečna plača (€)", min_value=500, max_value=10_000, value=1_680, step=50)
    obcina_sel = st.selectbox("Občina", OBCINE, index=0)
    povrsina = st.slider("Površina (m²)", 30, 150, 60, step=5)
with col_b:
    polog_pct = st.slider("Delež pologa (%)", 10, 50, 20, step=5)
    doba = st.selectbox("Doba kredita (let)", [15, 20, 25, 30], index=1)
with col_c:
    obrestna_mera = st.number_input(
        "Obrestna mera (% letno)",
        min_value=0.1, max_value=15.0, value=4.0, step=0.1,
        help="Tipično: ECB ~2,65% + bančni pribitek ~1,5% = ~4,0% (2025)"
    )

# Fetch 2024 median price for selected municipality
sub_2024 = df[(df["OBCINA"] == obcina_sel) & (df["TIP"] == "Stanovanje") & (df["LETO"] == 2024)]
med_m2_2024 = sub_2024["CENA_M2"].median()

sub_2015 = df[(df["OBCINA"] == obcina_sel) & (df["TIP"] == "Stanovanje") & (df["LETO"] == 2015)]
med_m2_2015 = sub_2015["CENA_M2"].median()

if pd.isna(med_m2_2024):
    st.error(f"Ni podatkov o stanovanjih za občino {obcina_sel.title()} za leto 2024.")
    st.stop()

total_price = med_m2_2024 * povrsina
polog_eur = total_price * polog_pct / 100
kredit = total_price - polog_eur
monthly_pay = mortgage_payment(kredit, obrestna_mera, doba)
burden = mortgage_burden_pct(monthly_pay, placa)
verdict_label, verdict_color = affordability_verdict(burden)
total_paid = monthly_pay * doba * 12
total_interest = total_paid - kredit

st.divider()

# --- 3-column output cards ---
st.subheader(f"📊 Rezultati za {obcina_sel.title()} — {povrsina} m² stanovanje (2024)")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("#### 🏠 Cena nepremičnine")
    st.metric("Skupna cena", f"€ {total_price:,.0f}", f"Mediana {obcina_sel.title()} 2024")
    st.metric("Polog", f"€ {polog_eur:,.0f}", f"{polog_pct}%")
    st.metric("Kredit (glavnica)", f"€ {kredit:,.0f}", f"LTV {100-polog_pct}%")
    st.metric("Mediana €/m²", f"€ {med_m2_2024:,.0f}")

with c2:
    st.markdown("#### 💳 Mesečni obrok")
    st.metric("Obrok", f"€ {monthly_pay:,.0f}/mes")

    burden_str = f"{burden:.1f}%"
    st.markdown(
        f"""
        <div style="background:{verdict_color}22;border:2px solid {verdict_color};
                    border-radius:10px;padding:16px;text-align:center;margin-top:8px;">
            <div style="font-size:2rem;font-weight:bold;color:{verdict_color}">
                {burden_str}
            </div>
            <div style="font-size:1.1rem;color:{verdict_color};font-weight:600">
                {verdict_label}
            </div>
            <div style="font-size:0.82rem;color:#555;margin-top:4px">
                plače namenjene za obrok
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("< 30%: dostopno · 30–40%: obremenjujoče · > 40%: nevzdržno")

with c3:
    st.markdown("#### 📈 Skupaj plačano v dobi kredita")
    st.metric(f"Skupaj v {doba} letih", f"€ {total_paid:,.0f}")
    st.metric("Plačane obresti", f"€ {total_interest:,.0f}", f"{total_interest/kredit*100:.1f}% od kredita")
    st.metric("Obrestna mera", f"{obrestna_mera:.2f}%")

st.divider()

# --- 2015 vs 2024 comparison ---
st.subheader("📅 Primerjava: 2015 vs. 2024")

if not pd.isna(med_m2_2015):
    price_2015 = med_m2_2015 * povrsina
    polog_2015 = price_2015 * polog_pct / 100
    kredit_2015 = price_2015 - polog_2015
    rate_2015 = ecb.get(2015, 0.05) + BANK_MARGIN
    pay_2015 = mortgage_payment(kredit_2015, rate_2015, doba)
    wage_2015 = wages.get(2015, 1013)
    burden_2015 = mortgage_burden_pct(pay_2015, wage_2015)
    total_paid_2015 = pay_2015 * doba * 12

    diff_pay = monthly_pay - pay_2015
    diff_pct = diff_pay / pay_2015 * 100

    comp_data = {
        "": ["2015", "2024", "Sprememba"],
        f"Mediana €/m² ({obcina_sel.title()})": [
            f"€ {med_m2_2015:,.0f}", f"€ {med_m2_2024:,.0f}",
            f"+{(med_m2_2024-med_m2_2015)/med_m2_2015*100:.1f}%"
        ],
        f"Cena {povrsina}m²": [
            f"€ {price_2015:,.0f}", f"€ {total_price:,.0f}",
            f"+{(total_price-price_2015)/price_2015*100:.1f}%"
        ],
        "Obrestna mera (ECB+pribitek)": [f"{rate_2015:.2f}%", f"{obrestna_mera:.2f}%", ""],
        "Mesečni obrok": [f"€ {pay_2015:,.0f}", f"€ {monthly_pay:,.0f}", f"+{diff_pct:.1f}%"],
        "Obrok kot % plače": [f"{burden_2015:.1f}%", f"{burden:.1f}%",
                               f"+{burden-burden_2015:.1f}pp"],
        f"Skupaj plačano ({doba} let)": [
            f"€ {total_paid_2015:,.0f}", f"€ {total_paid:,.0f}",
            f"+{(total_paid-total_paid_2015)/total_paid_2015*100:.1f}%"
        ],
    }
    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

    # Decomposition bar chart
    price_effect = mortgage_payment(kredit, rate_2015, doba) - pay_2015
    rate_effect = mortgage_payment(kredit_2015, obrestna_mera, doba) - pay_2015
    interaction = diff_pay - price_effect - rate_effect


st.divider()

# --- Affordability across all municipalities ---
st.subheader("🗺️ Dostopnost po vseh občinah")
st.caption(f"Obrok kot % vaše neto plače ({placa:,} €/mes) za {povrsina} m² stanovanje v 2024")

map_rows = []
for obcina in OBCINE:
    sub = df[(df["OBCINA"] == obcina) & (df["TIP"] == "Stanovanje") & (df["LETO"] == 2024)]
    med = sub["CENA_M2"].median()
    if pd.isna(med):
        continue
    p = med * povrsina
    k = p * (1 - polog_pct / 100)
    monthly = mortgage_payment(k, obrestna_mera, doba)
    b = mortgage_burden_pct(monthly, placa)
    label, color = affordability_verdict(b)
    map_rows.append({
        "OBCINA": obcina, "BURDEN": b, "MONTHLY": monthly, "PRICE": p,
        "LABEL": label, "COLOR": color,
    })

if map_rows:
    map_df = pd.DataFrame(map_rows).sort_values("BURDEN")
    fig_map = go.Figure(go.Bar(
        x=map_df["BURDEN"],
        y=[o.title() for o in map_df["OBCINA"]],
        orientation="h",
        marker_color=map_df["COLOR"].tolist(),
        text=[f"{b:.1f}% — {label}" for b, label in zip(map_df["BURDEN"], map_df["LABEL"])],
        textposition="outside",
        hovertemplate="%{y}: %{x:.1f}% plače<extra></extra>",
    ))
    fig_map.add_vline(x=30, line_dash="dash", line_color="#27AE60",
                      annotation_text="30% meja", annotation_position="top")
    fig_map.add_vline(x=40, line_dash="dash", line_color="#E74C3C",
                      annotation_text="40% meja", annotation_position="top")
    fig_map.update_layout(
        title=f"Obrok kot % plače ({placa:,} €) — {povrsina} m², {obrestna_mera}%, {doba}-letni kredit",
        xaxis_title="% neto plače", yaxis_title="",
        template="plotly_white", height=450,
        xaxis=dict(ticksuffix="%"),
    )
    st.plotly_chart(fig_map, use_container_width=True)

# --- Methodology ---
st.divider()
st.subheader("📚 Viri in predpostavke kalkulatorja")

col_src1, col_src2 = st.columns(2)
with col_src1:
    st.markdown("#### 📊 Cene nepremičnin")
    st.markdown(
        "**GURS — Evidenca trga nepremičnin (ETN)**  \n"
        "Uradni register kupoprodajnih poslov z nepremičninami v Sloveniji.  \n"
        "🔗 [e-prostor.gov.si](https://www.e-prostor.gov.si/) · "
        "[podatki.gov.si](https://podatki.gov.si/dataset/evidenca-trga-nepremicnin)"
    )
    st.markdown(f"Uporabljena vrednost: mediana €/m² za {obcina_sel.title()}, 2024.")

    st.divider()
    st.markdown("#### 💶 Povprečne neto plače")
    st.markdown(
        "**SURS — Povprečne mesečne neto plače**  \n"
        "🔗 [pxweb.stat.si](https://pxweb.stat.si/)"
    )
    st.markdown("- 2015: **€ 1.013/mes** · 2024: **€ 1.680/mes** · 2025: ~€ 1.750/mes")

with col_src2:
    st.markdown("#### 📉 Obrestna mera")
    st.markdown(
        "**ECB** — glavna refinancirna obrestna mera  \n"
        "🔗 [ecb.europa.eu](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html)  \n"
        "**Banka Slovenije** — statistika obrestnih mer kreditov  \n"
        "🔗 [bsi.si](https://www.bsi.si/statistika/financne-institucije-in-trgi/obrestne-mere)"
    )
    st.markdown(f"""
- ECB main refi rate (2025): ~2,65 %
- Bančni pribitek (tipično): +1,5–2,0 pp
- **Privzeta vrednost kalkulatorja: {obrestna_mera:.1f} %**
""")

    st.divider()
    st.markdown("#### 🏦 Polog (LTV)")
    st.markdown(
        "**Banka Slovenije — Makrobonitetni ukrepi**  \n"
        "LTV omejitev: največ 80 % (minimalni polog 20 %).  \n"
        "🔗 [bsi.si](https://www.bsi.si/financna-stabilnost/makrobonitetna-politika)"
    )
    st.markdown(f"Polog v kalkulatorju: **{polog_pct} %** (LTV {100-polog_pct} %)")

st.divider()
st.markdown("#### 📐 Formula za mesečni obrok (standardna anuiteta)")
st.latex(r"M = P \cdot \frac{r/12 \cdot (1 + r/12)^n}{(1 + r/12)^n - 1}")
st.caption("P = glavnica (kredit), r = letna obrestna mera, n = število mesecev odplačevanja")

st.warning("""
⚠️ **Omejitve kalkulatorja:**
- Ne upošteva notarskih stroškov, davka na promet nepremičnin in agencijskih provizij (tipično +4–6 % cene)
- Predpostavlja **fiksno** obrestno mero skozi celotno dobo kredita
- Uporablja **nacionalno povprečje** plač — regionalne razlike so znatne
- Mediana €/m² občine je groba ocena — dejanske cene se gibljejo v širokem razponu
- Kalkulator ne nadomešča strokovnega finančnega nasveta
""")
