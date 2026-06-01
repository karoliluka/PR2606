import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from utils.data_loader import BARVE


def make_price_trend_chart(
    pivot: pd.DataFrame,
    title: str,
    y_label: str = "Mediana €/m²",
    highlight_2025: bool = True,
) -> go.Figure:
    """Build a multi-line price trend chart from a pivot (index=LETO, cols=OBCINA)."""
    fig = go.Figure()
    for obcina in pivot.columns:
        color = BARVE.get(obcina, "#888888")
        y_all = pivot[obcina]
        years = pivot.index

        # Solid line 2015-2024
        mask_solid = years <= 2024
        fig.add_trace(go.Scatter(
            x=years[mask_solid], y=y_all[mask_solid],
            name=obcina, line=dict(color=color, width=2),
            mode="lines+markers",
            hovertemplate=f"<b>{obcina}</b><br>Leto: %{{x}}<br>€/m²: %{{y:,.0f}}<extra></extra>",
        ))

        # Dashed line for 2025 if available
        if highlight_2025 and 2025 in years:
            mask_25 = years >= 2024
            fig.add_trace(go.Scatter(
                x=years[mask_25], y=y_all[mask_25],
                name=f"{obcina} (2025*)",
                line=dict(color=color, width=2, dash="dot"),
                mode="lines+markers",
                showlegend=False,
                hovertemplate=f"<b>{obcina} (2025 — delni)</b><br>€/m²: %{{y:,.0f}}<extra></extra>",
            ))

    fig.update_layout(
        title=title,
        xaxis_title="Leto",
        yaxis_title=y_label,
        hovermode="x unified",
        legend=dict(orientation="v", x=1.02, y=1),
        template="plotly_white",
        height=480,
    )
    return fig


def make_yoy_heatmap(
    yoy_df: pd.DataFrame,
    title: str = "Letne spremembe cen po občinah (%)",
    zmax: float = 30,
) -> go.Figure:
    """Build a YoY heatmap: rows=municipalities, cols=years."""
    fig = go.Figure(data=go.Heatmap(
        z=yoy_df.values,
        x=[str(c) for c in yoy_df.columns],
        y=yoy_df.index.tolist(),
        colorscale=[
            [0.0, "#27AE60"],
            [0.5, "#FFFFFF"],
            [1.0, "#E53935"],
        ],
        zmid=0,
        zmin=-zmax,
        zmax=zmax,
        text=np.round(yoy_df.values, 1),
        texttemplate="%{text}%",
        hovertemplate="<b>%{y}</b><br>Leto: %{x}<br>Sprememba: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="% YoY"),
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Leto",
        yaxis_title="Občina",
        template="plotly_white",
        height=420,
    )
    return fig


def make_bar_chart(
    data: pd.Series,
    title: str,
    x_label: str = "",
    y_label: str = "",
    color_map: dict = None,
    horizontal: bool = False,
) -> go.Figure:
    """Simple bar chart from a Series."""
    colors = [color_map.get(k, "#1f3a5f") if color_map else "#1f3a5f" for k in data.index]
    if horizontal:
        fig = go.Figure(go.Bar(
            x=data.values, y=data.index,
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
        ))
    else:
        fig = go.Figure(go.Bar(
            x=data.index, y=data.values,
            marker_color=colors,
            hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
        ))
    fig.update_layout(
        title=title, xaxis_title=x_label, yaxis_title=y_label,
        template="plotly_white", height=400,
    )
    return fig
