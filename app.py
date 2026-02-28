"""
app.py
------
Cognitive Drift — Streamlit entry point.

Run with::

    streamlit run app.py

This file owns all Streamlit state and UI layout.  It delegates to:

- :mod:`analysis` for NLP computation
- :mod:`storage`  for JSON persistence
- :mod:`visualization` for Plotly figure construction
- :mod:`utils`    for constants and helpers
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import streamlit as st

import analysis
import storage
import visualization
from utils import PALETTE, JournalEntry, polarity_label

# ─────────────────────────────────────────────────────────────────────────────
# Page config  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cognitive Drift",
    page_icon="🜄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS injection
# ─────────────────────────────────────────────────────────────────────────────

def _inject_css() -> None:
    """Inject global CSS that establishes the editorial dark-amber aesthetic."""
    p = PALETTE
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Lora:ital@0;1&family=Fira+Mono:wght@400;500&display=swap');

/* ── Root reset ───────────────────────────── */
html, body, [class*="css"], [class*="stMarkdown"] {{
    background-color: {p['bg']};
    color: {p['text']};
}}

/* ── Main content ─────────────────────────── */
.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}}

/* ── Hero ─────────────────────────────────── */
.cd-hero {{
    text-align: left;
    padding: 1.8rem 0 1.2rem;
    border-bottom: 1px solid {p['border']};
    margin-bottom: 1.8rem;
}}
.cd-hero-title {{
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.8rem;
    font-weight: 600;
    color: {p['accent1']};
    letter-spacing: 0.02em;
    margin: 0;
    text-shadow: 0 2px 24px rgba(232,201,126,0.25);
}}
.cd-hero-sub {{
    font-family: 'Lora', Georgia, serif;
    font-style: italic;
    color: {p['muted']};
    font-size: 1rem;
    margin-top: 0.35rem;
}}

/* ── Metric cards ─────────────────────────── */
.cd-metric {{
    background: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 6px;
    padding: 1rem 1.15rem 0.9rem;
    margin-bottom: 0.8rem;
}}
.cd-metric-label {{
    font-family: 'Fira Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: {p['muted']};
    margin-bottom: 0.3rem;
}}
.cd-metric-value {{
    font-family: 'Playfair Display', serif;
    font-size: 1.7rem;
    color: {p['accent1']};
    line-height: 1;
}}
.cd-metric-sub {{
    font-family: 'Lora', serif;
    font-style: italic;
    font-size: 0.82rem;
    color: {p['muted']};
    margin-top: 0.2rem;
}}

/* ── Section headings ─────────────────────── */
.cd-section {{
    font-family: 'Fira Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: {p['muted']};
    border-bottom: 1px solid {p['border']};
    padding-bottom: 0.4rem;
    margin: 1.6rem 0 1rem;
}}

/* ── Shift alert ──────────────────────────── */
.cd-shift {{
    background: linear-gradient(135deg,
        rgba(232,126,158,0.1) 0%,
        rgba(232,126,158,0.03) 100%);
    border: 1px solid rgba(232,126,158,0.3);
    border-left: 3px solid {p['accent3']};
    border-radius: 5px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.75rem;
}}
.cd-shift-date {{
    font-family: 'Fira Mono', monospace;
    font-size: 0.76rem;
    color: {p['accent3']};
    letter-spacing: 0.1em;
    margin-bottom: 0.35rem;
}}
.cd-shift-reason {{
    font-family: 'Lora', serif;
    font-style: italic;
    color: #c0909a;
    font-size: 0.9rem;
    line-height: 1.5;
}}

/* ── Keyword tags ─────────────────────────── */
.cd-kw {{
    display: inline-block;
    background: rgba(126,184,232,0.1);
    border: 1px solid rgba(126,184,232,0.22);
    color: {p['accent2']};
    border-radius: 3px;
    padding: 2px 9px;
    font-size: 0.78rem;
    margin: 2px 2px;
    font-family: 'Fira Mono', monospace;
}}

/* ── Sidebar ──────────────────────────────── */
[data-testid="stSidebar"] {{
    background: {p['surface']};
    border-right: 1px solid {p['border']};
}}
[data-testid="stSidebar"] * {{
    font-family: 'Fira Mono', monospace;
}}

/* ── Textarea ─────────────────────────────── */
textarea {{
    background: {p['surface']} !important;
    border: 1px solid {p['border']} !important;
    color: {p['text']} !important;
    font-family: 'Lora', Georgia, serif !important;
    font-size: 1rem !important;
    line-height: 1.7 !important;
}}
textarea:focus {{
    border-color: {p['accent1']} !important;
    box-shadow: 0 0 0 2px rgba(232,201,126,0.12) !important;
}}

/* ── Primary button ───────────────────────── */
.stButton > button {{
    background: transparent !important;
    border: 1px solid {p['accent1']} !important;
    color: {p['accent1']} !important;
    font-family: 'Fira Mono', monospace !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.1em !important;
    padding: 0.45rem 1.5rem !important;
    border-radius: 3px !important;
    transition: background 0.2s !important;
}}
.stButton > button:hover {{
    background: rgba(232,201,126,0.1) !important;
}}

/* ── Tabs ─────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background: {p['surface']};
    border-bottom: 1px solid {p['border']};
    gap: 0;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Fira Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.1em;
    color: {p['muted']};
    padding: 0.5rem 1.2rem;
}}
.stTabs [aria-selected="true"] {{
    color: {p['accent1']} !important;
    border-bottom: 2px solid {p['accent1']} !important;
}}

/* ── Selectbox ────────────────────────────── */
[data-baseweb="select"] > div {{
    background: {p['surface']} !important;
    border-color: {p['border']} !important;
}}

/* ── Sliders ──────────────────────────────── */
[data-testid="stSlider"] div[role="slider"] {{
    background-color: {p['accent1']} !important;
}}

/* ── Footer ───────────────────────────────── */
.cd-footer {{
    text-align: center;
    padding: 2.5rem 0 0.5rem;
    color: {p['border']};
    font-family: 'Fira Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    border-top: 1px solid {p['border']};
    margin-top: 3rem;
}}

/* ── Entry list item ──────────────────────── */
.cd-entry-chip {{
    font-family: 'Fira Mono', monospace;
    font-size: 0.76rem;
    color: {p['muted']};
    border-bottom: 1px solid {p['border']};
    padding: 0.3rem 0;
    cursor: pointer;
}}

/* ── Topic bar ────────────────────────────── */
.cd-bar-wrap {{
    margin-bottom: 0.5rem;
}}
.cd-bar-label {{
    display: flex;
    justify-content: space-between;
    font-family: 'Fira Mono', monospace;
    font-size: 0.72rem;
    color: {p['muted']};
    margin-bottom: 3px;
}}
.cd-bar-track {{
    background: {p['border']};
    border-radius: 2px;
    height: 5px;
}}
.cd-bar-fill {{
    background: {p['accent1']};
    border-radius: 2px;
    height: 5px;
    transition: width 0.4s ease;
}}

/* ── Warn banner ──────────────────────────── */
.cd-warn {{
    background: rgba(232,201,126,0.08);
    border: 1px solid rgba(232,201,126,0.25);
    border-radius: 4px;
    padding: 0.6rem 0.9rem;
    font-family: 'Lora', serif;
    font-style: italic;
    font-size: 0.88rem;
    color: {p['accent1']};
    margin-bottom: 0.8rem;
}}
</style>
""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Session-state initialisation
# ─────────────────────────────────────────────────────────────────────────────

def _init_state() -> None:
    """Initialise all ``st.session_state`` keys on first run."""
    if "entries" not in st.session_state:
        st.session_state.entries = storage.load_entries()
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = None


# ─────────────────────────────────────────────────────────────────────────────
# Reusable UI components
# ─────────────────────────────────────────────────────────────────────────────

def _metric_card(label: str, value: str, sub: str = "") -> str:
    """Return HTML for a single metric card."""
    sub_html = f'<div class="cd-metric-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="cd-metric">'
        f'<div class="cd-metric-label">{label}</div>'
        f'<div class="cd-metric-value">{value}</div>'
        f'{sub_html}'
        f"</div>"
    )


def _topic_bars(topics: dict[str, int]) -> str:
    """Return HTML for a mini topic breakdown bar chart."""
    total = sum(topics.values()) or 1
    items = sorted(topics.items(), key=lambda x: -x[1])
    html_parts = []
    for topic, score in items[:6]:
        if score == 0:
            continue
        pct = score / total * 100
        html_parts.append(
            f'<div class="cd-bar-wrap">'
            f'<div class="cd-bar-label">'
            f'<span>{topic}</span><span>{score}</span>'
            f"</div>"
            f'<div class="cd-bar-track">'
            f'<div class="cd-bar-fill" style="width:{pct:.0f}%"></div>'
            f"</div>"
            f"</div>"
        )
    return "\n".join(html_parts)


def _keyword_tags(keywords: list[tuple[str, int]]) -> str:
    """Return HTML spans for keyword tags."""
    return "".join(
        f'<span class="cd-kw">{w}</span>' for w, _ in keywords[:12]
    )


def _section(label: str) -> None:
    """Render a section divider heading."""
    st.markdown(f'<p class="cd-section">{label}</p>', unsafe_allow_html=True)


def _render_live_analysis(text: str) -> None:
    """
    Render the live analysis panel for the write tab.

    Parameters
    ----------
    text : str
        Current textarea content (may be empty / short).
    """
    if len(text.strip()) < 10:
        st.markdown(
            '<p style="color:#2a2820;font-style:italic;padding:0.5rem 0">'
            "Begin writing to see live analysis…</p>",
            unsafe_allow_html=True,
        )
        return

    a = analysis.analyze_entry(text)

    st.markdown(
        _metric_card("Sentiment", f"{a['sentiment']:+.3f}", polarity_label(a["sentiment"]))
        + _metric_card("Lexical Diversity (TTR)", f"{a['lexical_div']:.2%}", f"{a['word_count']} words")
        + _metric_card("Avg Sentence Length", f"{a['avg_sent_len']:.1f}", "words / sentence"),
        unsafe_allow_html=True,
    )

    _section("Topic Preview")
    st.markdown(_topic_bars(a["topics"]), unsafe_allow_html=True)

    _section("Top Keywords")
    st.markdown(_keyword_tags(a["keywords"]), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def _render_sidebar(entries: list[JournalEntry]) -> None:
    """
    Render the sidebar: entry list, counts, and danger-zone controls.

    Parameters
    ----------
    entries : list[JournalEntry]
        Current journal entries (sorted, oldest first).
    """
    with st.sidebar:
        st.markdown(
            '<p style="font-size:0.95rem;color:#6a6460;margin-bottom:0.3rem">'
            "📖 Journal</p>",
            unsafe_allow_html=True,
        )

        if not entries:
            st.markdown(
                '<p style="color:#2a2820;font-style:italic;font-size:0.82rem">'
                "No entries yet.  Begin writing.</p>",
                unsafe_allow_html=True,
            )
        else:
            for entry in reversed(entries):
                sentiment = entry["analysis"]["sentiment"]
                icon = "😊" if sentiment >= 0.25 else ("😔" if sentiment <= -0.25 else "😐")
                label = f"{icon}  {entry['date']}"
                if st.button(label, key=f"sb_{entry['date']}", use_container_width=True):
                    st.session_state.selected_date = entry["date"]
                    st.rerun()

        st.markdown("---")
        st.caption(f"{len(entries)} entr{'y' if len(entries)==1 else 'ies'}")

        if entries:
            if st.button("🗑 Clear All", use_container_width=True):
                storage.clear_all()
                st.session_state.entries = []
                st.session_state.selected_date = None
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Tab: Write
# ─────────────────────────────────────────────────────────────────────────────

def _tab_write(entries: list[JournalEntry]) -> None:
    """Render the Write tab: entry form + live analysis pane."""
    col_form, col_live = st.columns([3, 2], gap="large")

    with col_form:
        _section("Today's Entry")

        entry_date = st.date_input(
            "Date",
            value=date.today(),
            label_visibility="collapsed",
        )
        date_str = str(entry_date)

        # Pre-fill if editing existing entry
        existing = storage.get_entry(entries, date_str)
        default_text = existing["text"] if existing else ""

        entry_text: str = st.text_area(
            "Write here",
            value=default_text,
            height=300,
            placeholder="Begin writing.  Let the words drift…",
            label_visibility="collapsed",
        )

        if not analysis.textblob_available():
            st.markdown(
                '<div class="cd-warn">⚠ TextBlob not found. '
                'Sentiment uses a basic lexicon fallback. '
                'Run <code>pip install textblob</code> for better accuracy.</div>',
                unsafe_allow_html=True,
            )

        _, btn_col = st.columns([4, 1])
        with btn_col:
            save = st.button("Save", use_container_width=True)

        if save:
            _handle_save(entry_text, date_str)

    with col_live:
        _section("Live Analysis")
        _render_live_analysis(entry_text)


def _handle_save(text: str, date_str: str) -> None:
    """
    Validate, analyse, persist a new/updated entry, then rerun.

    Parameters
    ----------
    text : str
        Raw journal text from the textarea.
    date_str : str
        ISO-8601 date string for this entry.
    """
    if len(text.strip()) < 15:
        st.warning("Entry is too short to analyse meaningfully (need ≥ 15 chars).")
        return

    new_entry: JournalEntry = {
        "date":      date_str,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "text":      text,
        "analysis":  analysis.analyze_entry(text),
    }

    is_update = storage.entry_exists(st.session_state.entries, date_str)
    st.session_state.entries = storage.upsert_entry(
        st.session_state.entries, new_entry
    )

    verb = "updated" if is_update else "saved"
    st.success(f"Entry {verb} for {date_str}.")
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Tab: Trends
# ─────────────────────────────────────────────────────────────────────────────

def _tab_trends(entries: list[JournalEntry]) -> None:
    """Render the Trends tab: three main time-series charts."""
    if len(entries) < 2:
        _empty_state(
            "∿",
            "Add at least two entries to see trends emerge.",
        )
        return

    shifts = analysis.detect_shifts(entries)

    st.plotly_chart(
        visualization.emotional_trend_chart(entries, shifts),
        use_container_width=True,
    )

    col_l, col_r = st.columns(2, gap="medium")
    with col_l:
        st.plotly_chart(
            visualization.complexity_evolution_chart(entries),
            use_container_width=True,
        )
    with col_r:
        st.plotly_chart(
            visualization.word_count_sparkline(entries),
            use_container_width=True,
        )

    st.plotly_chart(
        visualization.topic_drift_chart(entries),
        use_container_width=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tab: Shifts
# ─────────────────────────────────────────────────────────────────────────────

def _tab_shifts(entries: list[JournalEntry]) -> None:
    """Render the Shifts tab: sensitivity sliders, shift cards, summary stats."""
    if len(entries) < 2:
        _empty_state(
            "⚡",
            "Cognitive shifts appear between consecutive entries.  "
            "Write at least two to reveal them.",
        )
        return

    _section("Detection Sensitivity")
    col_s1, col_s2, col_s3 = st.columns(3, gap="medium")
    with col_s1:
        thresh_sent = st.slider(
            "Sentiment threshold",
            min_value=0.05, max_value=1.0, value=0.40, step=0.05,
            help="|Δpolarity| required to flag a shift",
        )
    with col_s2:
        thresh_lex = st.slider(
            "Lexical threshold",
            min_value=0.02, max_value=0.50, value=0.12, step=0.01,
            help="|ΔTTR| required to flag a shift",
        )
    with col_s3:
        thresh_asl = st.slider(
            "Sentence-length threshold",
            min_value=1.0, max_value=15.0, value=5.0, step=0.5,
            help="Δ avg words/sentence required to flag a shift",
        )

    shifts = analysis.detect_shifts(entries, thresh_sent, thresh_lex, thresh_asl)

    _section("Detected Shifts")
    if not shifts:
        st.markdown(
            '<p style="color:#3a3830;font-style:italic;padding:1rem 0">'
            "No significant shifts at this sensitivity.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<p style="color:{PALETTE["accent3"]};font-style:italic;margin-bottom:0.8rem">'
            f"✦ {len(shifts)} cognitive shift{'s' if len(shifts)>1 else ''} detected</p>",
            unsafe_allow_html=True,
        )
        for s in shifts:
            reasons_html = "".join(
                f'<div class="cd-shift-reason">· {r}</div>' for r in s["reasons"]
            )
            prev_sent = entries[s["index"]-1]["analysis"]["sentiment"]
            curr_sent = entries[s["index"]]["analysis"]["sentiment"]
            arrow = "↑" if curr_sent > prev_sent else "↓"
            st.markdown(
                f'<div class="cd-shift">'
                f'<div class="cd-shift-date">'
                f"✦ {s['to_date']}  "
                f"<span style='color:{PALETTE['muted']}'>"
                f"({s['from_date']} {arrow} {s['to_date']}  "
                f"{prev_sent:+.3f} → {curr_sent:+.3f})"
                f"</span></div>"
                f"{reasons_html}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Summary stats ────────────────────────────────────────────────────────
    _section("Journal Summary")
    stats = analysis.summarise_entries(entries)

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        st.markdown(
            _metric_card(
                "Avg Sentiment",
                f"{stats['avg_sentiment']:+.3f}",
                polarity_label(stats["avg_sentiment"]),
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _metric_card(
                "Avg Lexical Div",
                f"{stats['avg_lexical_div']:.2%}",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _metric_card(
                "Emotional Arc",
                stats["sentiment_trend"].capitalize(),
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            _metric_card(
                "Total Words Written",
                f"{stats['total_words']:,}",
                f"dominant topic: {stats['dominant_topic']}",
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tab: Entry Detail
# ─────────────────────────────────────────────────────────────────────────────

def _tab_detail(entries: list[JournalEntry]) -> None:
    """Render the Entry Detail tab: full text + per-entry deep analysis."""
    if not entries:
        _empty_state("✦", "No entries saved yet.  Begin writing.")
        return

    available_dates = [e["date"] for e in reversed(entries)]
    default_idx = 0
    if st.session_state.selected_date in available_dates:
        default_idx = available_dates.index(st.session_state.selected_date)

    chosen_date = st.selectbox(
        "Select entry",
        available_dates,
        index=default_idx,
        label_visibility="collapsed",
    )

    entry = storage.get_entry(entries, chosen_date)
    if entry is None:
        st.error("Entry not found.")
        return

    a = entry["analysis"]

    col_text, col_meta = st.columns([3, 2], gap="large")

    with col_text:
        _section(f"Entry — {chosen_date}")
        formatted = entry["text"].replace("\n", "<br>")
        st.markdown(
            f'<div style="background:{PALETTE["surface"]};border:1px solid {PALETTE["border"]};'
            f"border-radius:5px;padding:1.3rem 1.5rem;font-family:'Lora',serif;"
            f"font-style:italic;line-height:1.78;color:#b0a898;font-size:0.96rem;"
            f'max-height:340px;overflow-y:auto">{formatted}</div>',
            unsafe_allow_html=True,
        )

        _section("Keywords")
        st.markdown(_keyword_tags(a["keywords"]), unsafe_allow_html=True)

        _section("Delete Entry")
        if st.button("🗑 Delete this entry", key="delete_entry"):
            st.session_state.entries = storage.delete_entry(
                entries, chosen_date
            )
            st.session_state.selected_date = None
            st.rerun()

    with col_meta:
        _section("Metrics")
        st.markdown(
            _metric_card("Sentiment", f"{a['sentiment']:+.3f}", polarity_label(a["sentiment"]))
            + _metric_card("Lexical Diversity", f"{a['lexical_div']:.2%}", f"{a['word_count']} total words")
            + _metric_card("Avg Sentence Length", f"{a['avg_sent_len']:.1f} words"),
            unsafe_allow_html=True,
        )

        _section("Topic Breakdown")
        st.markdown(_topic_bars(a["topics"]), unsafe_allow_html=True)

        _section("Topic Radar")
        st.plotly_chart(
            visualization.topic_radar_chart(entry),
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _empty_state(icon: str, message: str) -> None:
    """Render a centred empty-state placeholder."""
    st.markdown(
        f'<div style="text-align:center;padding:4rem 0;color:{PALETTE["muted"]}">'
        f'<p style="font-size:2.4rem;margin:0">{icon}</p>'
        f'<p style="font-style:italic;margin-top:0.6rem">{message}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Application entry point."""
    _inject_css()
    _init_state()

    entries: list[JournalEntry] = st.session_state.entries

    # ── Hero ─────────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="cd-hero">'
        '<h1 class="cd-hero-title">🜄 Cognitive Drift</h1>'
        '<p class="cd-hero-sub">track how your mind moves through time</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    _render_sidebar(entries)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_write, tab_trends, tab_shifts, tab_detail = st.tabs([
        "✍  Write",
        "📈  Trends",
        "⚡  Shifts",
        "🔍  Entry Detail",
    ])

    with tab_write:
        _tab_write(entries)

    with tab_trends:
        _tab_trends(entries)

    with tab_shifts:
        _tab_shifts(entries)

    with tab_detail:
        _tab_detail(entries)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="cd-footer">'
        "COGNITIVE DRIFT · entries stored locally · your words, your patterns"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
