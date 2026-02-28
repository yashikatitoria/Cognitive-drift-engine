"""
storage.py
----------
All file-system I/O for Cognitive Drift lives here.

Responsibilities
~~~~~~~~~~~~~~~~
- Load journal entries from a JSON file.
- Persist new or updated entries back to disk.
- Validate the stored structure and recover gracefully from corruption.
- Provide a thin upsert API so callers never have to think about duplicates.

The storage format is a single JSON array of :class:`~utils.JournalEntry`
objects, sorted chronologically by the ``"date"`` field.

Example file layout::

    [
      {
        "date": "2025-06-01",
        "timestamp": "2025-06-01T09:14:33",
        "text": "Today I …",
        "analysis": { … }
      },
      …
    ]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from utils import JournalEntry

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_PATH = Path("cognitive_drift_journal.json")


def load_entries(path: Path = DEFAULT_PATH) -> list[JournalEntry]:
    """
    Load journal entries from *path*.

    If the file does not exist an empty list is returned (first-run case).
    If the file exists but contains malformed JSON, a warning is logged and
    an empty list is returned — **no exception is raised** so the app stays
    usable after accidental corruption.

    Parameters
    ----------
    path : Path
        Location of the JSON storage file.

    Returns
    -------
    list[JournalEntry]
        Chronologically sorted entries.  Never ``None``.
    """
    if not path.exists():
        return []

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Storage file %s contains invalid JSON (%s). "
            "Starting with empty journal.",
            path,
            exc,
        )
        return []
    except OSError as exc:
        logger.warning("Could not read storage file %s: %s", path, exc)
        return []

    if not isinstance(data, list):
        logger.warning(
            "Storage file %s has unexpected top-level type %s. "
            "Expected a list.  Starting fresh.",
            path,
            type(data).__name__,
        )
        return []

    validated = _validate_entries(data)
    return _sort_entries(validated)


def save_entries(entries: list[JournalEntry], path: Path = DEFAULT_PATH) -> bool:
    """
    Write *entries* to *path* as pretty-printed JSON.

    Parameters
    ----------
    entries : list[JournalEntry]
        Entries to persist.  They are sorted before writing.
    path : Path
        Destination file.  Parent directories are created if necessary.

    Returns
    -------
    bool
        ``True`` on success, ``False`` if an ``OSError`` occurred (e.g.,
        read-only filesystem).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_sort_entries(entries), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except OSError as exc:
        logger.error("Failed to write storage file %s: %s", path, exc)
        return False


def upsert_entry(
    entries: list[JournalEntry],
    new_entry: JournalEntry,
    path: Path = DEFAULT_PATH,
) -> list[JournalEntry]:
    """
    Insert *new_entry* or replace the existing entry with the same date.

    The updated list is persisted to *path* automatically.

    Parameters
    ----------
    entries : list[JournalEntry]
        Current in-memory list (will not be mutated; a new list is returned).
    new_entry : JournalEntry
        Entry to add or replace.
    path : Path
        Storage file to update.

    Returns
    -------
    list[JournalEntry]
        Updated, chronologically sorted list.
    """
    updated = [e for e in entries if e["date"] != new_entry["date"]]
    updated.append(new_entry)
    updated = _sort_entries(updated)
    save_entries(updated, path)
    return updated


def delete_entry(
    entries: list[JournalEntry],
    date_str: str,
    path: Path = DEFAULT_PATH,
) -> list[JournalEntry]:
    """
    Remove the entry with *date_str* from *entries* and persist.

    Parameters
    ----------
    entries : list[JournalEntry]
        Current in-memory list.
    date_str : str
        ISO-8601 date string identifying the entry to remove.
    path : Path
        Storage file to update.

    Returns
    -------
    list[JournalEntry]
        Updated list with the target entry removed.  If no entry matched,
        the original list is returned unchanged.
    """
    updated = [e for e in entries if e["date"] != date_str]
    if len(updated) < len(entries):
        save_entries(updated, path)
    return updated


def clear_all(path: Path = DEFAULT_PATH) -> None:
    """
    Delete *all* entries by writing an empty array to *path*.

    Parameters
    ----------
    path : Path
        Storage file to truncate.
    """
    save_entries([], path)


def entry_exists(entries: list[JournalEntry], date_str: str) -> bool:
    """
    Return ``True`` if an entry for *date_str* already exists.

    Parameters
    ----------
    entries : list[JournalEntry]
        Current in-memory list.
    date_str : str
        ISO-8601 date string to look up.
    """
    return any(e["date"] == date_str for e in entries)


def get_entry(
    entries: list[JournalEntry], date_str: str
) -> Optional[JournalEntry]:
    """
    Retrieve the entry for *date_str*, or ``None`` if absent.

    Parameters
    ----------
    entries : list[JournalEntry]
        Current in-memory list.
    date_str : str
        ISO-8601 date string to look up.
    """
    for e in entries:
        if e["date"] == date_str:
            return e
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────


def _sort_entries(entries: list[JournalEntry]) -> list[JournalEntry]:
    """Return *entries* sorted chronologically by the ``date`` field."""
    return sorted(entries, key=lambda e: e["date"])


_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"date", "timestamp", "text", "analysis"}
)
_REQUIRED_ANALYSIS_KEYS: frozenset[str] = frozenset(
    {"sentiment", "lexical_div", "avg_sent_len", "word_count", "topics", "keywords"}
)


def _validate_entries(raw: list) -> list[JournalEntry]:
    """
    Filter *raw* to entries that have the expected structure.

    Malformed items are skipped with a logged warning so the rest of the
    journal is still usable.

    Parameters
    ----------
    raw : list
        Parsed JSON data (expected to be a list of dicts).

    Returns
    -------
    list[JournalEntry]
        Only structurally valid entries.
    """
    valid: list[JournalEntry] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            logger.warning("Entry %d is not a dict — skipping.", i)
            continue
        missing = _REQUIRED_KEYS - item.keys()
        if missing:
            logger.warning(
                "Entry %d missing keys %s — skipping.", i, missing
            )
            continue
        analysis = item.get("analysis", {})
        if not isinstance(analysis, dict):
            logger.warning("Entry %d has non-dict 'analysis' — skipping.", i)
            continue
        missing_a = _REQUIRED_ANALYSIS_KEYS - analysis.keys()
        if missing_a:
            logger.warning(
                "Entry %d analysis missing keys %s — skipping.", i, missing_a
            )
            continue
        valid.append(item)  # type: ignore[arg-type]
    return valid
