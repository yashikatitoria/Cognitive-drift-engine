"""
analysis.py
-----------
Pure-function NLP layer for Cognitive Drift.

All functions are stateless: given text (or a list of entries) they return
structured results.  No I/O, no Streamlit, no global state.

Sentiment backend
~~~~~~~~~~~~~~~~~
We try to import TextBlob at module load time.  If it is unavailable we fall
back to a simple lexicon-based approach using :data:`utils.POSITIVE_WORDS` and
:data:`utils.NEGATIVE_WORDS`.  The fallback is clearly labelled in the result
so callers can surface a warning if desired.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from utils import (
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    STOPWORDS,
    TOPIC_SEEDS,
    CognitiveShift,
    EntryAnalysis,
    JournalEntry,
    clamp,
    content_tokens,
    tokenize,
)

# ── optional TextBlob ─────────────────────────────────────────────────────────
try:
    from textblob import TextBlob as _TextBlob  # type: ignore

    _TEXTBLOB_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TEXTBLOB_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Metric functions
# ─────────────────────────────────────────────────────────────────────────────


def compute_lexical_diversity(text: str) -> float:
    """
    Compute the **Type-Token Ratio (TTR)** of *text*.

    .. math::

        \\text{TTR} = \\frac{|V|}{N}

    where :math:`|V|` is the vocabulary size (unique tokens) and :math:`N` is
    the total number of tokens.

    Parameters
    ----------
    text : str
        Raw journal text.

    Returns
    -------
    float
        TTR in the range ``(0, 1]``.  Returns ``0.0`` for empty/blank input.

    Notes
    -----
    TTR is sensitive to text length: longer texts naturally have lower TTR
    because common words accumulate.  For entries that are typically a few
    hundred words this is a meaningful proxy for vocabulary richness.
    """
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    return round(len(set(tokens)) / len(tokens), 4)


def compute_avg_sentence_length(text: str) -> float:
    """
    Return the mean number of word tokens per sentence.

    Sentences are delimited by ``.``, ``!``, or ``?``.  Empty segments
    (e.g., trailing punctuation) are ignored.

    Parameters
    ----------
    text : str
        Raw journal text.

    Returns
    -------
    float
        Average sentence length in words.  Returns ``0.0`` for empty input.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return 0.0
    lengths = [len(tokenize(s)) for s in sentences]
    return round(sum(lengths) / len(lengths), 2)


def compute_sentiment(text: str) -> float:
    """
    Estimate sentiment polarity of *text* in the range ``[-1, +1]``.

    Uses **TextBlob** when available (pattern-based; considers valence
    shifters such as "not bad").  Falls back to a raw lexicon count:

    .. math::

        \\text{polarity} = \\frac{|P| - |N|}{|P| + |N| + 1}

    where :math:`|P|` and :math:`|N|` are the counts of positive and negative
    content words respectively.

    Parameters
    ----------
    text : str
        Raw journal text.

    Returns
    -------
    float
        Polarity score.  Positive → positive sentiment; negative → negative.
    """
    if _TEXTBLOB_AVAILABLE:
        return round(_TextBlob(text).sentiment.polarity, 4)

    words = set(tokenize(text))
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    return round(clamp((pos - neg) / (pos + neg + 1), -1.0, 1.0), 4)


def compute_topic_scores(text: str) -> dict[str, int]:
    """
    Score how strongly *text* relates to each predefined topic cluster.

    For each topic, we count how many of its seed keywords appear in the
    text (with repetition — frequency matters).

    Parameters
    ----------
    text : str
        Raw journal text.

    Returns
    -------
    dict[str, int]
        Mapping of topic name → keyword hit count.  All topics in
        :data:`utils.TOPIC_SEEDS` are always present; value is ``0`` if no
        hits were found.
    """
    tokens = tokenize(text)
    freq = Counter(tokens)
    return {
        topic: sum(freq[kw] for kw in seeds)
        for topic, seeds in TOPIC_SEEDS.items()
    }


def compute_top_keywords(text: str, n: int = 10) -> list[tuple[str, int]]:
    """
    Return the top-*n* most frequent **content** words in *text*.

    Stopwords and single-character tokens are excluded (see
    :func:`utils.content_tokens`).

    Parameters
    ----------
    text : str
        Raw journal text.
    n : int
        Maximum number of keywords to return (default ``10``).

    Returns
    -------
    list[tuple[str, int]]
        ``[(word, frequency), …]`` sorted descending by frequency.
    """
    tokens = content_tokens(tokenize(text))
    return Counter(tokens).most_common(n)


def analyze_entry(text: str) -> EntryAnalysis:
    """
    Run the full analysis pipeline on a single journal entry.

    This is the main public API of this module.  It calls all individual
    metric functions and bundles results into an :class:`~utils.EntryAnalysis`
    dict.

    Parameters
    ----------
    text : str
        Raw journal text (should be at least a few words long).

    Returns
    -------
    EntryAnalysis
        All computed metrics for the entry.
    """
    tokens = tokenize(text)
    return EntryAnalysis(
        sentiment=compute_sentiment(text),
        lexical_div=compute_lexical_diversity(text),
        avg_sent_len=compute_avg_sentence_length(text),
        word_count=len(tokens),
        topics=compute_topic_scores(text),
        keywords=compute_top_keywords(text),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cognitive shift detection
# ─────────────────────────────────────────────────────────────────────────────


def detect_shifts(
    entries: list[JournalEntry],
    sentiment_threshold: float = 0.40,
    lexical_threshold: float = 0.12,
    sentence_len_threshold: float = 5.0,
) -> list[CognitiveShift]:
    """
    Compare consecutive journal entries and flag large discontinuities as
    **cognitive shifts**.

    A shift is reported when *any* of the following conditions hold between
    entry *i-1* and entry *i*:

    - ``|Δsentiment|   ≥ sentiment_threshold``
    - ``|Δlexical_div| ≥ lexical_threshold``
    - ``|Δavg_sent_len| ≥ sentence_len_threshold``

    Parameters
    ----------
    entries : list[JournalEntry]
        Chronologically sorted entries (oldest first).
    sentiment_threshold : float
        Minimum absolute sentiment change to flag.  Default ``0.40``.
    lexical_threshold : float
        Minimum absolute lexical-diversity change to flag.  Default ``0.12``.
    sentence_len_threshold : float
        Minimum absolute average-sentence-length change to flag.
        Default ``5.0`` words.

    Returns
    -------
    list[CognitiveShift]
        One item per detected shift, in chronological order.
    """
    shifts: list[CognitiveShift] = []

    for i in range(1, len(entries)):
        prev_a = entries[i - 1]["analysis"]
        curr_a = entries[i]["analysis"]

        d_sentiment = curr_a["sentiment"] - prev_a["sentiment"]
        d_lexical   = curr_a["lexical_div"] - prev_a["lexical_div"]
        d_sent_len  = curr_a["avg_sent_len"] - prev_a["avg_sent_len"]

        reasons: list[str] = []

        if abs(d_sentiment) >= sentiment_threshold:
            direction = "more positive" if d_sentiment > 0 else "more negative"
            reasons.append(
                f"Emotional tone shifted {direction} "
                f"({_fmt_delta(d_sentiment)} polarity)"
            )

        if abs(d_lexical) >= lexical_threshold:
            direction = "richer" if d_lexical > 0 else "simpler"
            reasons.append(
                f"Vocabulary became {direction} "
                f"({_fmt_delta(d_lexical)} TTR)"
            )

        if abs(d_sent_len) >= sentence_len_threshold:
            direction = "longer" if d_sent_len > 0 else "shorter"
            reasons.append(
                f"Sentences became {direction} "
                f"({_fmt_delta(d_sent_len)} words / sentence)"
            )

        if reasons:
            shifts.append(
                CognitiveShift(
                    index=i,
                    from_date=entries[i - 1]["date"],
                    to_date=entries[i]["date"],
                    delta_sentiment=round(d_sentiment, 4),
                    delta_lexical=round(d_lexical, 4),
                    reasons=reasons,
                )
            )

    return shifts


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics
# ─────────────────────────────────────────────────────────────────────────────


def summarise_entries(entries: list[JournalEntry]) -> dict:
    """
    Compute aggregate statistics over the full journal history.

    Parameters
    ----------
    entries : list[JournalEntry]
        All stored journal entries (any order).

    Returns
    -------
    dict
        Keys: ``avg_sentiment``, ``avg_lexical_div``, ``avg_word_count``,
        ``total_words``, ``dominant_topic``, ``sentiment_trend``
        (``"improving"`` / ``"declining"`` / ``"stable"`` / ``"unknown"``).
        Returns an empty dict for an empty list.
    """
    if not entries:
        return {}

    sentiments = [e["analysis"]["sentiment"] for e in entries]
    lexicals   = [e["analysis"]["lexical_div"] for e in entries]
    wc         = [e["analysis"]["word_count"] for e in entries]

    # Dominant topic: summed across all entries
    topic_totals: Counter = Counter()
    for e in entries:
        topic_totals.update(e["analysis"]["topics"])
    dominant_topic = topic_totals.most_common(1)[0][0] if topic_totals else "—"

    # Trend: compare first-half mean vs second-half mean
    if len(sentiments) >= 4:
        mid = len(sentiments) // 2
        first_half  = sum(sentiments[:mid]) / mid
        second_half = sum(sentiments[mid:]) / (len(sentiments) - mid)
        if second_half - first_half > 0.10:
            trend = "improving"
        elif first_half - second_half > 0.10:
            trend = "declining"
        else:
            trend = "stable"
    elif len(sentiments) == 1:
        trend = "unknown"
    else:
        trend = "improving" if sentiments[-1] > sentiments[0] else (
                "declining" if sentiments[-1] < sentiments[0] else "stable"
        )

    return {
        "avg_sentiment":  round(sum(sentiments) / len(sentiments), 4),
        "avg_lexical_div": round(sum(lexicals) / len(lexicals), 4),
        "avg_word_count": round(sum(wc) / len(wc), 1),
        "total_words":    sum(wc),
        "dominant_topic": dominant_topic,
        "sentiment_trend": trend,
    }


def textblob_available() -> bool:
    """Return ``True`` if TextBlob was successfully imported."""
    return _TEXTBLOB_AVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_delta(value: float) -> str:
    """Format a signed float for human-readable shift reasons."""
    return f"{value:+.3f}"
