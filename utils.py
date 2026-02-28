"""
utils.py
--------
Shared constants, type aliases, and small helpers used across the
Cognitive Drift project.  Nothing in here should import from sibling
modules — this is the bottom of the dependency tree.
"""

from __future__ import annotations

import re
from typing import TypedDict

# ─────────────────────────────────────────────────────────────────────────────
# Type definitions
# ─────────────────────────────────────────────────────────────────────────────


class EntryAnalysis(TypedDict):
    """Structured result produced by analysis.py for one journal entry."""

    sentiment: float          # polarity in [-1, +1]
    lexical_div: float        # unique words / total words  ∈ (0, 1]
    avg_sent_len: float       # mean words per sentence
    word_count: int           # total word tokens
    topics: dict[str, int]    # topic_name → keyword-hit count
    keywords: list[tuple[str, int]]  # [(word, freq), …] top N content words


class JournalEntry(TypedDict):
    """One complete journal entry as stored in JSON."""

    date: str           # ISO-8601 date string  "2025-06-01"
    timestamp: str      # ISO-8601 datetime     "2025-06-01T09:14:00"
    text: str           # raw journal text
    analysis: EntryAnalysis


class CognitiveShift(TypedDict):
    """A detected discontinuity between two consecutive entries."""

    index: int          # index of the *later* entry in the sorted list
    from_date: str
    to_date: str
    delta_sentiment: float
    delta_lexical: float
    reasons: list[str]  # human-readable explanations


# ─────────────────────────────────────────────────────────────────────────────
# NLP constants
# ─────────────────────────────────────────────────────────────────────────────

#: English stopwords used when scoring content-word frequency.
STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "it", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "this", "that", "these", "those",
    "i", "my", "me", "we", "our", "you", "your", "he", "his", "she", "her",
    "they", "their", "them", "its", "as", "by", "from", "up", "about",
    "into", "through", "during", "before", "after", "above", "so", "if",
    "not", "no", "all", "just", "can", "more", "also", "then", "than",
    "very", "too", "some", "what", "when", "where", "who", "how", "why",
    "there", "which", "while", "am", "out", "well", "still", "even",
    "get", "got", "go", "going", "like", "know", "think", "said", "say",
    "make", "made", "want", "time", "day", "one", "two", "three", "now",
    "here", "us", "let", "over", "much", "many", "back", "see", "ve",
    "ll", "re", "s", "t", "d", "m",
})

#: Predefined keyword clusters for topic scoring.
TOPIC_SEEDS: dict[str, list[str]] = {
    "work": [
        "work", "job", "meeting", "project", "deadline", "boss", "office",
        "email", "client", "task", "career", "colleague", "manager", "salary",
        "productivity", "sprint", "feedback", "report", "presentation",
    ],
    "health": [
        "sleep", "tired", "energy", "exercise", "run", "eat", "food", "sick",
        "doctor", "health", "pain", "body", "gym", "rest", "diet", "water",
        "headache", "stress", "breath", "walk", "fatigue",
    ],
    "emotions": [
        "feel", "felt", "happy", "sad", "anxious", "angry", "excited",
        "worried", "scared", "love", "fear", "mood", "frustrated", "calm",
        "relief", "hope", "joy", "grief", "lonely", "proud", "shame",
        "guilt", "content", "overwhelmed",
    ],
    "social": [
        "friend", "family", "people", "talk", "conversation", "relationship",
        "together", "alone", "party", "date", "someone", "everyone", "group",
        "share", "listen", "support", "trust", "argue", "connect", "bond",
    ],
    "learning": [
        "learn", "read", "study", "book", "idea", "think", "understand",
        "curious", "discover", "research", "question", "knowledge", "skill",
        "practice", "improve", "concept", "explore", "realize", "insight",
    ],
    "nature": [
        "outside", "weather", "sun", "rain", "walk", "park", "sky", "nature",
        "cold", "warm", "morning", "night", "wind", "light", "dark", "tree",
        "water", "air", "quiet", "space", "season",
    ],
    "future": [
        "plan", "goal", "future", "hope", "dream", "want", "wish", "change",
        "start", "next", "tomorrow", "decide", "choice", "direction", "vision",
        "move", "build", "become", "grow",
    ],
    "past": [
        "remember", "memory", "used", "before", "yesterday", "ago", "past",
        "miss", "regret", "always", "never", "childhood", "old", "back",
        "once", "used", "used", "nostalgia", "then", "history",
    ],
}

#: Simple positive / negative word lists used as a TextBlob fallback.
POSITIVE_WORDS: frozenset[str] = frozenset({
    "good", "great", "happy", "love", "wonderful", "excellent", "amazing",
    "fantastic", "joyful", "excited", "grateful", "calm", "peaceful",
    "hopeful", "inspired", "proud", "bright", "glad", "warm", "kind",
    "strong", "free", "clear", "open", "positive", "beautiful", "light",
    "fun", "playful", "confident", "fresh", "alive", "energised", "lucky",
    "thankful", "motivated", "creative", "productive", "safe", "better",
})

NEGATIVE_WORDS: frozenset[str] = frozenset({
    "bad", "sad", "hate", "terrible", "awful", "horrible", "angry", "fear",
    "anxious", "tired", "worried", "depressed", "lonely", "failed", "broken",
    "lost", "dark", "heavy", "empty", "stuck", "trapped", "bitter", "cold",
    "numb", "hurt", "pain", "struggle", "difficult", "hard", "worse",
    "weak", "confused", "guilty", "shame", "regret", "frustrated", "dread",
    "hopeless", "doubt", "afraid", "nervous", "sick",
})

# ─────────────────────────────────────────────────────────────────────────────
# Design tokens  (consumed by app.py for CSS injection)
# ─────────────────────────────────────────────────────────────────────────────

PALETTE: dict[str, str] = {
    "bg":       "#080b10",
    "surface":  "#0e1118",
    "border":   "#181d28",
    "accent1":  "#e8c97e",   # warm amber
    "accent2":  "#7eb8e8",   # steel blue
    "accent3":  "#e87e9e",   # dusty rose  (shift markers)
    "accent4":  "#7ee8b8",   # seafoam     (topic 4)
    "text":     "#c8c2b8",
    "muted":    "#4a4840",
    "grid":     "#12151e",
}


# ─────────────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────────────

def tokenize(text: str) -> list[str]:
    """
    Return a list of lowercase alphabetic tokens from *text*.

    Contractions are split on apostrophes so "don't" → ["don", "t"].
    Numbers and punctuation are discarded.

    Parameters
    ----------
    text : str
        Raw input string.

    Returns
    -------
    list[str]
        Ordered list of word tokens.
    """
    return re.findall(r"\b[a-zA-Z]+\b", text.lower())


def content_tokens(tokens: list[str]) -> list[str]:
    """
    Filter *tokens* to remove stopwords and single-character tokens.

    Parameters
    ----------
    tokens : list[str]
        Output of :func:`tokenize`.

    Returns
    -------
    list[str]
        Content words only.
    """
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def clamp(value: float, lo: float, hi: float) -> float:
    """Return *value* clamped to the closed interval [*lo*, *hi*]."""
    return max(lo, min(hi, value))


def polarity_label(polarity: float) -> str:
    """
    Convert a numeric sentiment polarity to a human-readable emoji label.

    Parameters
    ----------
    polarity : float
        Sentiment polarity in [-1, +1].

    Returns
    -------
    str
        One of ``"😊 Positive"``, ``"😔 Negative"``, or ``"😐 Neutral"``.
    """
    if polarity >= 0.25:
        return "😊 Positive"
    if polarity <= -0.25:
        return "😔 Negative"
    return "😐 Neutral"


def format_delta(value: float, precision: int = 3) -> str:
    """Return *value* formatted as a signed string, e.g. ``'+0.142'``."""
    return f"{value:+.{precision}f}"
