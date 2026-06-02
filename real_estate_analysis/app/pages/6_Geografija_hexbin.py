import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.data_loader import load_data, OBCINE
from utils.geo import convert_coordinates, hexbin_aggregate
from utils.sources import render_source_box

HEX_COLORSCALE = [
    [0.0, "#2044a2"],
    [0.2, "#47a5bd"],
    [0.4, "#b7dc90"],
    [0.6, "#fdf6a7"],
    [0.8, "#f6b35f"],
    [1.0, "#c82233"],
]


def _hex_geojson(hex_df: pd.DataFrame, radius_m: float) -> dict:
    """Build GeoJSON FeatureCollection of flat-top hexagon polygons."""
    DEG_LAT = 1 / 111_000
    features = []
    for i, (_, row) in enumerate(hex_df.iterrows()):
        clat, clon = row["hex_lat"], row["hex_lon"]
        deg_lon_m = 1 / (111_000 * np.cos(np.radians(clat)))
        r_lat = radius_m * DEG_LAT
        r_lon = radius_m * deg_lon_m
        coords = []
        for k in range(6):
            angle = np.radians(60 * k)
            coords.append([clon + r_lon * np.cos(angle), clat + r_lat * np.sin(angle)])
        coords.append(coords[0])
        features.append({
            "type": "Feature",
            "id": str(i),
            "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": {},
        })
    return {"type": "FeatureCollection", "features": features}

st.set_page_config(page_title="Geografija — hexbin", page_icon="🗺️", layout="wide")

with st.sidebar:
    st.markdown("### 🗺️ Geografija — hexbin")
    obcina_sel = st.selectbox("Občina", OBCINE, index=0)
    compare_mode = st.checkbox("Primerjalni način (dve občini)", value=False)
    if compare_mode:
        obcina_sel2 = st.selectbox("Primerjalna občina", OBCINE, index=1)

    leto_range = st.slider("Leto (od–do)", 2015, 2024, (2022, 2024))
    tip_sel = st.radio("Tip nepremičnine", ["Stanovanje", "Hiša", "Obe"], index=0)
    hex_size = st.slider("Hex velikost (m)", 50, 500, 150, step=25)
    min_count = st.slider("Min. poslov v hexu", 1, 20, 1, step=1)

st.title("🗺️ Geografija cen nepremičnin — hexbin")

st.info(
    "**Na levi strani** izberite občino, primerjalni način (dve občini), "
    "leto, tip nepremičnine ter velikost in gostoto hexbinov.",
)

df_all = load_data()


@st.cache_data
def prepare_geo(obcina, tip_filter, leto_from, leto_to):
    sub = df_all[
        (df_all["OBCINA"] == obcina) &
        (df_all["TIP"].isin(tip_filter)) &
        (df_all["LETO"].between(leto_from, leto_to))
    ].copy()
    return convert_coordinates(sub)


tip_filter = ["Stanovanje", "Hiša"] if tip_sel == "Obe" else [tip_sel]
leto_from, leto_to = leto_range


def make_hex_map(obcina: str, title_suffix: str = "", vmin: float = None, vmax: float = None):
    geo_df = prepare_geo(obcina, tuple(tip_filter), leto_from, leto_to)
    hex_df = hexbin_aggregate(geo_df, hex_size_m=hex_size, min_count=min_count)

    if hex_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5, xref="paper", yref="paper",
            text=f"Ni dovolj podatkov za {obcina.title()}<br>z izbranimi filtri.",
            showarrow=False, font=dict(size=14),
        )
        fig.update_layout(height=500)
        return fig, None, None

    cmin = vmin if vmin is not None else hex_df["median_cena_m2"].quantile(0.05)
    cmax = vmax if vmax is not None else hex_df["median_cena_m2"].quantile(0.95)

    center_lat = hex_df["hex_lat"].mean()
    center_lon = hex_df["hex_lon"].mean()

    # Circumradius = hex_size / √3 exactly fills the grid cell without overlap.
    # cell_lon = hex_size * (2/√3) → hex width = 2r = cell_lon → r = hex_size/√3
    geojson = _hex_geojson(hex_df, hex_size / np.sqrt(3))
    hover_texts = [
        f"Mediana: €{r['median_cena_m2']:,.0f}/m²<br>Transakcij: {r['count']}"
        for _, r in hex_df.iterrows()
    ]

    step = (cmax - cmin) / 5
    tick_vals = [cmin + i * step for i in range(6)]

    fig = go.Figure(go.Choroplethmapbox(
        geojson=geojson,
        locations=[str(i) for i in range(len(hex_df))],
        z=hex_df["median_cena_m2"].values,
        colorscale=HEX_COLORSCALE,
        zmin=cmin,
        zmax=cmax,
        marker_opacity=0.82,
        marker_line_width=0.8,
        marker_line_color="rgba(255,255,255,0.25)",
        colorbar=dict(
            title="€/m²",
            tickvals=tick_vals,
            ticktext=[f"€{v:,.0f}" for v in tick_vals],
            thickness=15,
            len=0.6,
        ),
        text=hover_texts,
        hovertemplate="%{text}<extra></extra>",
        name=obcina.title(),
    ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=11,
        ),
        title=f"{obcina.title()}{title_suffix} — {leto_from}–{leto_to}",
        height=520,
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return fig, cmin, cmax


def show_stats(obcina, tip_filter_list, leto_from, leto_to):
    geo_df = prepare_geo(obcina, tuple(tip_filter_list), leto_from, leto_to)
    valid = geo_df.dropna(subset=["lon", "lat"])
    total = len(geo_df)
    geo_count = len(valid)
    median_p = geo_df["CENA_M2"].median()
    return total, geo_count, median_p


# --- Main view ---
if compare_mode:
    # Compute shared color scale
    geo1 = prepare_geo(obcina_sel, tuple(tip_filter), leto_from, leto_to)
    geo2 = prepare_geo(obcina_sel2, tuple(tip_filter), leto_from, leto_to)
    combined = pd.concat([geo1, geo2])["CENA_M2"].dropna()
    shared_min = combined.quantile(0.05) if len(combined) else None
    shared_max = combined.quantile(0.95) if len(combined) else None

    col1, col2 = st.columns(2)
    with col1:
        total1, geo1_c, med1 = show_stats(obcina_sel, tip_filter, leto_from, leto_to)
        st.metric(f"{obcina_sel.title()} — transakcij", f"{total1:,}")
        st.metric("Mediana €/m²", f"€ {med1:,.0f}" if not np.isnan(med1) else "N/A")
        fig1, _, _ = make_hex_map(obcina_sel, vmin=shared_min, vmax=shared_max)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        total2, geo2_c, med2 = show_stats(obcina_sel2, tip_filter, leto_from, leto_to)
        st.metric(f"{obcina_sel2.title()} — transakcij", f"{total2:,}")
        st.metric("Mediana €/m²", f"€ {med2:,.0f}" if not np.isnan(med2) else "N/A")
        fig2, _, _ = make_hex_map(obcina_sel2, vmin=shared_min, vmax=shared_max)
        st.plotly_chart(fig2, use_container_width=True)

    # Comparison table
    if not (np.isnan(med1) or np.isnan(med2)):
        diff = (med1 - med2) / med2 * 100
        st.info(
            f"**{obcina_sel.title()}** je za **{abs(diff):.1f}%** "
            f"{'dražja' if diff > 0 else 'cenejša'} od **{obcina_sel2.title()}**"
        )

else:
    total, geo_count, med = show_stats(obcina_sel, tip_filter, leto_from, leto_to)
    c1, c2, c3 = st.columns(3)
    c1.metric("Skupaj transakcij", f"{total:,}")
    c2.metric("Z geolokacijo", f"{geo_count:,}")
    c3.metric("Mediana €/m²", f"€ {med:,.0f}" if not np.isnan(med) else "N/A")

    fig, cmin, cmax = make_hex_map(obcina_sel)
    st.plotly_chart(fig, use_container_width=True)

    if cmin is not None and cmax is not None:
        st.caption(
            f"Barvna lestvica: €{cmin:,.0f} (modra) → €{cmax:,.0f} (rdeča) | "
            f"Hex velikost: ~{hex_size} m | Razpon prilagojen mediani izbrane občine"
        )

with st.expander("📋 Metodologija"):
    st.markdown("""
    #### Koordinatni sistem
    Izvorni podatki ETN vsebujejo koordinate v slovenskem koordinatnem sistemu **D96/TM (EPSG:3794)**.
    Pretvorba v **WGS84 (EPSG:4326)** je izvedena z knjižnico `pyproj`.

    #### Hexbin agregacija
    Transakcije so združene v mrežo šestkotnih celic (hexagonov) s privzeto velikostjo ~150 m.
    Znotraj vsake celice je izračunana **mediana €/m²**. Celice z manj kot `min_count` transakcijami
    so skrite (premalo podatkov za zanesljivo oceno).

    #### Prednosti hexbin pred koropleto
    - Koropleta prikazuje povprečje po celotni občini — skrije prostorske razlike znotraj občine
    - Hexbin razkrije dražje in cenejše soseske, razlike center/obrobje, in lokalne outlierje

    #### Omejitve
    - ~15% transakcij v ETN nima geolokacije ali ima napačne koordinate
    - Hex velikost vpliva na gostoto: manjši hex = več detajlov, a bolj redko zapolnjeno
    - Primerjalni način uporablja skupno barvno lestvico za obe občini
    """)
    render_source_box("etn")
