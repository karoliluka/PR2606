EVENTS = [
    {"date": "2020-03-15", "label": "COVID-19 lockdown",            "color": "#E74C3C"},
    {"date": "2021-01-15", "label": "Val cepljenja (SLO)",          "color": "#27AE60"},
    {"date": "2022-02-24", "label": "Vojna v Ukrajini",             "color": "#E74C3C"},
    {"date": "2022-07-21", "label": "1. dvig ECB obresti",          "color": "#F39C12"},
    {"date": "2022-10-01", "label": "Vrh energetske krize",         "color": "#9B59B6"},
    {"date": "2022-11-01", "label": "Vrh inflacije SLO (10,8 %)",   "color": "#9B59B6"},
    {"date": "2024-06-06", "label": "ECB začne zniževati obresti",  "color": "#27AE60"},
    {"date": "2024-09-01", "label": "Inflacija pod 2 %",            "color": "#27AE60"},
]


def add_events_to_plotly(fig, events=None, y_annotation_position="top"):
    """Add vertical event lines + labels to a plotly time-series figure."""
    if events is None:
        events = EVENTS
    for ev in events:
        fig.add_vline(
            x=ev["date"], line_dash="dash", line_color=ev["color"], opacity=0.6
        )
        fig.add_annotation(
            x=ev["date"], y=1.02, yref="paper",
            text=ev["label"], showarrow=False,
            font=dict(color=ev["color"], size=10),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=ev["color"], borderwidth=1, borderpad=2,
            textangle=-30, xanchor="left",
        )
    return fig
