"""
visualization.py
----------------
Plotly figure factories for Cognitive Drift.

Every public function receives plain data (lists, dicts) and returns a
``plotly.graph_objects.Figure``.  There is no Streamlit or I/O code here —
the calling layer (app.py) passes figures to ``st.plotly_chart``.

Dark theme
~~~~~~~~~~
All figures share a base layout defined in :data:`_BASE_LAYOUT`.  The colour
palette is imported from :mod:`utils` so the whole app uses consistent tokens.
"""

from __future__ import annotations

from typing import Optional

import plotly.graph_objects as go

from utils import PALETTE, CognitiveShift, JournalEntry

# ─────────────────────────────────────────────────────────────────────────────
# Shared layout base
# ─────────────────────────────────────────────────────────────────────────────

_FONT_FAMILY = "Georgia, 'Times New Roman', serif"

_BASE_LAYOUT = dict(
    paper_bgcolor=PALETTE["surface"],
    plot_bgcolor=PALETTE["surface"],
    font=dict(
        color=PALETTE["text"],
        family=_FONT_FAMILY,
        size=12,
    ),
    xaxis=dict(
        showgrid=True,
        gridcolor=PALETTE["grid"],
        zeroline=False,
        linecolor=PALETTE["border"],
        tickfont=dict(size=11),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor=PALETTE["grid"],
        zeroline=False,
        linecolor=PALETTE["border"],
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(0,0,0,0)",
        font=dict(size=11),
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    margin=dict(l=48, r=24, t=54, b=48),
    hoverlabel=dict(
        bgcolor=PALETTE["bg"],
        bordercolor=PALETTE["border"],
        font_color=PALETTE["text"],
        font_family=_FONT_FAMILY,
    ),
)


def _base_figure(title: str) -> go.Figure:
    """Return a new :class:`~plotly.graph_objects.Figure` with the dark theme applied."""
    fig = go.Figure()
    layout = dict(_BASE_LAYOUT)
    layout["title"] = dict(
        text=title,
        font=dict(size=15, color=PALETTE["accent1"], family=_FONT_FAMILY),
        x=0.0,
        xanchor="left",
        pad=dict(l=4),
    )
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Public figure factories
# ─────────────────────────────────────────────────────────────────────────────


def emotional_trend_chart(
    entries: list[JournalEntry],
    shifts: list[CognitiveShift],
) -> go.Figure:
    """
    Plot sentiment polarity over time with shift markers.

    The area between the polarity line and zero is shaded amber (positive
    territory) or rose (negative territory) to give an instant visual read
    of emotional history.  Detected cognitive shifts are overlaid as
    star-shaped markers.

    Parameters
    ----------
    entries : list[JournalEntry]
        All journal entries, chronologically sorted.
    shifts : list[CognitiveShift]
        Detected cognitive shifts (from :func:`analysis.detect_shifts`).

    Returns
    -------
    plotly.graph_objects.Figure
    """
    dates      = [e["date"] for e in entries]
    polarities = [e["analysis"]["sentiment"] for e in entries]

    fig = _base_figure("Emotional Trend")

    # Positive-area fill
    fig.add_trace(go.Scatter(
        x=dates,
        y=[max(0.0, p) for p in polarities],
        fill="tozeroy",
        fillcolor="rgba(232,201,126,0.14)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
        name="_pos_fill",
    ))

    # Negative-area fill
    fig.add_trace(go.Scatter(
        x=dates,
        y=[min(0.0, p) for p in polarities],
        fill="tozeroy",
        fillcolor="rgba(232,126,158,0.12)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
        name="_neg_fill",
    ))

    # Main polarity line
    fig.add_trace(go.Scatter(
        x=dates,
        y=polarities,
        mode="lines+markers",
        name="Sentiment",
        line=dict(color=PALETTE["accent1"], width=2.5),
        marker=dict(size=7, color=PALETTE["accent1"]),
        hovertemplate="<b>%{x}</b><br>Polarity: %{y:+.3f}<extra></extra>",
    ))

    # Shift markers
    if shifts:
        sx = [entries[s["index"]]["date"] for s in shifts]
        sy = [entries[s["index"]]["analysis"]["sentiment"] for s in shifts]
        sr = ["<br>".join(s["reasons"]) for s in shifts]
        fig.add_trace(go.Scatter(
            x=sx,
            y=sy,
            mode="markers",
            name="Cognitive Shift",
            marker=dict(
                size=16,
                color=PALETTE["accent3"],
                symbol="star",
                line=dict(width=1.5, color="white"),
            ),
            hovertemplate="<b>⚡ Shift on %{x}</b><br>%{customdata}<extra></extra>",
            customdata=sr,
        ))

    # Zero-line
    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color=PALETTE["muted"],
        line_width=1,
    )

    fig.update_yaxes(range=[-1.15, 1.15], title_text="Polarity")
    fig.update_xaxes(title_text="Date")
    return fig


def complexity_evolution_chart(entries: list[JournalEntry]) -> go.Figure:
    """
    Plot lexical diversity (TTR) and normalised average sentence length over
    time on a shared axis.

    Sentence length is divided by 40 so both metrics share a comparable
    ``[0, 1]`` scale without a secondary y-axis.  The legend label reflects
    this normalisation.

    Parameters
    ----------
    entries : list[JournalEntry]
        Chronologically sorted entries.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    dates  = [e["date"] for e in entries]
    ttr    = [e["analysis"]["lexical_div"] for e in entries]
    asl    = [e["analysis"]["avg_sent_len"] for e in entries]
    asl_n  = [v / 40.0 for v in asl]   # normalise

    fig = _base_figure("Vocabulary Complexity Evolution")

    fig.add_trace(go.Scatter(
        x=dates,
        y=ttr,
        mode="lines+markers",
        name="Lexical Diversity (TTR)",
        line=dict(color=PALETTE["accent2"], width=2.5),
        marker=dict(size=7),
        hovertemplate="<b>%{x}</b><br>TTR: %{y:.3f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=dates,
        y=asl_n,
        mode="lines+markers",
        name="Avg Sentence Length (÷ 40)",
        line=dict(color=PALETTE["accent1"], width=2, dash="dot"),
        marker=dict(size=6, symbol="diamond"),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Avg Sent Len: %{customdata:.1f} words<extra></extra>"
        ),
        customdata=asl,
    ))

    fig.update_yaxes(range=[0, 1.05], title_text="Score (normalised)")
    fig.update_xaxes(title_text="Date")
    return fig


def topic_drift_chart(entries: list[JournalEntry]) -> go.Figure:
    """
    Plot topic hit-counts per entry as stacked area curves.

    The stacked view makes it easy to see which topics dominate and how
    the balance shifts over time.

    Parameters
    ----------
    entries : list[JournalEntry]
        Chronologically sorted entries.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    from utils import TOPIC_SEEDS  # local import avoids circular-ish risk

    dates  = [e["date"] for e in entries]
    topics = list(TOPIC_SEEDS.keys())

    # Eight distinct colours drawn from / extending the palette
    colours = [
        PALETTE["accent1"],   # work
        PALETTE["accent2"],   # health
        PALETTE["accent3"],   # emotions
        PALETTE["accent4"],   # social
        "#b87ee8",            # learning
        "#e8b87e",            # nature
        "#7ee8d8",            # future
        "#e8e87e",            # past
    ]

    fig = _base_figure("Topic Drift")

    for idx, topic in enumerate(topics):
        scores = [e["analysis"]["topics"].get(topic, 0) for e in entries]
        colour = colours[idx % len(colours)]
        fig.add_trace(go.Scatter(
            x=dates,
            y=scores,
            mode="lines+markers",
            name=topic.capitalize(),
            line=dict(color=colour, width=2),
            marker=dict(size=5),
            hovertemplate=f"<b>{topic.capitalize()}</b><br>%{{x}}: %{{y}} hits<extra></extra>",
        ))

    fig.update_yaxes(title_text="Keyword Hits")
    fig.update_xaxes(title_text="Date")
    fig.update_layout(
        legend=dict(
            orientation="h",
            y=-0.28,
            x=0.5,
            xanchor="center",
            yanchor="top",
        )
    )
    return fig


def word_count_sparkline(entries: list[JournalEntry]) -> go.Figure:
    """
    Minimal bar chart of per-entry word counts.

    Useful as a compact sidebar widget to give writers a sense of their
    output volume trend.

    Parameters
    ----------
    entries : list[JournalEntry]
        Chronologically sorted entries.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    dates  = [e["date"] for e in entries]
    counts = [e["analysis"]["word_count"] for e in entries]

    fig = _base_figure("Words per Entry")
    fig.add_trace(go.Bar(
        x=dates,
        y=counts,
        marker_color=PALETTE["accent2"],
        marker_line_width=0,
        opacity=0.75,
        hovertemplate="<b>%{x}</b><br>%{y} words<extra></extra>",
        name="Word Count",
    ))
    fig.update_yaxes(title_text="Words")
    fig.update_layout(showlegend=False)
    return fig


def topic_radar_chart(entry: JournalEntry) -> go.Figure:
    """
    Radar (spider) chart of topic scores for a single entry.

    Gives a compact "personality fingerprint" of the entry's thematic content.

    Parameters
    ----------
    entry : JournalEntry
        The entry to visualise.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    topics = list(entry["analysis"]["topics"].keys())
    scores = list(entry["analysis"]["topics"].values())
    # Close the polygon
    topics_closed = topics + [topics[0]]
    scores_closed = scores + [scores[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores_closed,
        theta=[t.capitalize() for t in topics_closed],
        fill="toself",
        fillcolor=f"rgba(126,184,232,0.18)",
        line=dict(color=PALETTE["accent2"], width=2),
        marker=dict(size=6, color=PALETTE["accent2"]),
        name="Topics",
        hovertemplate="<b>%{theta}</b>: %{r} hits<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=PALETTE["surface"],
        plot_bgcolor=PALETTE["surface"],
        font=dict(color=PALETTE["text"], family=_FONT_FAMILY, size=11),
        polar=dict(
            bgcolor=PALETTE["surface"],
            radialaxis=dict(
                visible=True,
                showgrid=True,
                gridcolor=PALETTE["grid"],
                linecolor=PALETTE["border"],
                tickfont=dict(size=9),
            ),
            angularaxis=dict(
                gridcolor=PALETTE["grid"],
                linecolor=PALETTE["border"],
            ),
        ),
        title=dict(
            text=f"Topic Radar — {entry['date']}",
            font=dict(size=14, color=PALETTE["accent1"], family=_FONT_FAMILY),
            x=0.0,
            xanchor="left",
        ),
        margin=dict(l=32, r=32, t=54, b=32),
        showlegend=False,
        hoverlabel=dict(
            bgcolor=PALETTE["bg"],
            bordercolor=PALETTE["border"],
            font_color=PALETTE["text"],
            font_family=_FONT_FAMILY,
        ),
    )
    return fig
