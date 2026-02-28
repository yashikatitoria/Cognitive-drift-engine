# 🜄 Cognitive Drift

> *Track how your mind moves through time.*

Cognitive Drift is a local-first journal analysis tool built with Streamlit.
Write daily entries, and the app quietly measures how your vocabulary, emotions,
and topics shift over time — surfacing **cognitive shifts** when a change is
large enough to be meaningful.

No accounts.  No cloud.  All data lives in a single JSON file on your machine.

---

## Quick Start

```bash
# 1. Clone / download the project
cd cognitive_drift

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional but recommended) Download TextBlob corpora
python -m textblob.download_corpora

# 4. Run
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Project Architecture

```
cognitive_drift/
├── app.py              ← Streamlit UI: layout, state, user interactions
├── analysis.py         ← NLP layer: all metric computation & shift detection
├── storage.py          ← Persistence: load / save / upsert / validate JSON
├── visualization.py    ← Plotly figure factories (no UI code)
├── utils.py            ← Constants, type aliases, shared helpers
├── requirements.txt
└── README.md
```

### Dependency graph

```
app.py
 ├── analysis.py  ──→  utils.py
 ├── storage.py   ──→  utils.py
 ├── visualization.py  ──→  utils.py
 └── utils.py
```

Each module has a **single responsibility**:

| Module | Owns | Never touches |
|---|---|---|
| `utils.py` | Constants, TypedDicts, pure helpers | I/O, Streamlit, NLP |
| `analysis.py` | NLP metrics, shift detection | I/O, Streamlit |
| `storage.py` | JSON read/write, validation | NLP, Streamlit |
| `visualization.py` | Plotly figures | I/O, Streamlit |
| `app.py` | UI layout, session state | Business logic |

---

## Feature Overview

| Feature | Description |
|---|---|
| **Write tab** | Compose or edit an entry for any date; live analysis updates as you type |
| **Trends tab** | Three time-series charts: emotional arc, complexity evolution, topic drift |
| **Shifts tab** | Configurable shift detection with sentiment / lexical / sentence-length thresholds |
| **Entry Detail** | Per-entry deep dive: full text, topic radar, keyword tags, delete button |
| **Sidebar** | Chronological entry list with emoji sentiment indicators |

---

## Mathematical Explanation of Metrics

### 1. Lexical Diversity — Type-Token Ratio (TTR)

$$\text{TTR} = \frac{|V|}{N}$$

- $|V|$ = vocabulary size: number of **unique** word types in the text  
- $N$ = total number of word tokens (all words, including repeats)

**Range:** $(0, 1]$.  A score of $1.0$ means every word was used exactly once.
Longer texts naturally score lower because common words accumulate faster than
unique ones.

**Interpretation:**
- High TTR ($> 0.70$) → rich, varied vocabulary
- Low TTR ($< 0.40$) → repetitive or simple language

---

### 2. Average Sentence Length

$$\overline{L} = \frac{1}{S}\sum_{i=1}^{S} w_i$$

- $S$ = number of sentences (split on `.`, `!`, `?`)
- $w_i$ = word count of sentence $i$

**Interpretation:**
- Short sentences ($\overline{L} < 10$) → direct, clipped, possibly anxious writing
- Long sentences ($\overline{L} > 25$) → complex, reflective, flowing prose
- Sharp increases may indicate a move from bullet-point thinking to deeper reflection

---

### 3. Sentiment Polarity

**With TextBlob** (recommended):  
Pattern-based NLP that scores phrases in $[-1, +1]$, accounting for simple
valence shifters like *"not bad"* → positive.

**Fallback lexicon method:**

$$\text{polarity} = \frac{|P| - |N|}{|P| + |N| + 1}$$

- $|P|$ = count of positive-lexicon matches  
- $|N|$ = count of negative-lexicon matches  
- The $+1$ denominator prevents division-by-zero

**Clamped** to $[-1, +1]$.

---

### 4. Topic Seed Scoring

For each predefined topic cluster $T_k$ (e.g., *work*, *health*):

$$\text{score}(T_k) = \sum_{w \in T_k} \text{freq}(w, \text{entry})$$

Frequency is counted **with** repetition, so writing about sleep three times
scores higher on *health* than writing about it once.  The scores are then
used both as raw values in the Topic Drift chart and as proportional inputs
for the Topic Radar visualisation.

---

### 5. Cognitive Shift Detection

A shift is flagged when **any** of the following exceed their respective
thresholds between entries $i-1$ and $i$:

$$|\Delta \text{polarity}| = |\text{polarity}_i - \text{polarity}_{i-1}| \geq \theta_s$$

$$|\Delta \text{TTR}| = |\text{TTR}_i - \text{TTR}_{i-1}| \geq \theta_\ell$$

$$|\Delta \overline{L}| = |\overline{L}_i - \overline{L}_{i-1}| \geq \theta_w$$

Default thresholds: $\theta_s = 0.40$, $\theta_\ell = 0.12$, $\theta_w = 5.0$.
All are tunable via sliders in the Shifts tab.

---

### 6. Sentiment Trend Classification

To smooth noise, the journal history is split into two halves and the mean
sentiment of each half is compared:

$$\text{trend} = \begin{cases}
\text{improving} & \text{if } \bar{s}_{\text{second}} - \bar{s}_{\text{first}} > 0.10 \\
\text{declining} & \text{if } \bar{s}_{\text{first}} - \bar{s}_{\text{second}} > 0.10 \\
\text{stable}    & \text{otherwise}
\end{cases}$$

This requires at least 4 entries; below that a simpler first-vs-last
comparison is used.

---

## Storage Format

Entries are stored in `cognitive_drift_journal.json` as a JSON array,
sorted chronologically.

```json
[
  {
    "date": "2025-06-01",
    "timestamp": "2025-06-01T09:14:33",
    "text": "Today I felt …",
    "analysis": {
      "sentiment": 0.312,
      "lexical_div": 0.6842,
      "avg_sent_len": 14.5,
      "word_count": 203,
      "topics": { "work": 4, "health": 1, "emotions": 6, … },
      "keywords": [["felt", 4], ["idea", 3], …]
    }
  }
]
```

The storage layer validates this schema on load and silently drops malformed
entries, so a corrupted file will never crash the app.

---

## Future Scope

| Idea | Notes |
|---|---|
| **Moving-average smoothing** | Apply a rolling window to polarity/TTR charts to reduce day-to-day noise |
| **LIWC-style category expansion** | Expand topic seeds into proper psychological word categories (e.g., Cognitive Processes, Social Processes) |
| **Export to CSV / PDF** | Let users download their full analysis history |
| **Writing style fingerprinting** | Use punctuation cadence, paragraph length, and function-word ratios as a stylometric signature |
| **Weekly summaries** | Auto-generate a prose recap of the week's emotional and thematic arc |
| **Spacy / NLTK integration** | Replace regex tokenisation with a proper NLP pipeline for better lemmatisation and sentence detection |
| **Streak / habit tracking** | Track consecutive writing days and surface streaks in the sidebar |
| **Multi-user support** | Namespace storage files per user for shared installations |
| **Readability scores** | Add Flesch–Kincaid or Gunning Fog index as additional complexity metrics |
| **Anomaly detection** | Replace threshold-based shifts with a simple z-score or IQR outlier test over the rolling history |

---

## Dependencies

| Package | Purpose | Required? |
|---|---|---|
| `streamlit` | Web UI framework | ✅ Yes |
| `plotly` | Interactive charts | ✅ Yes |
| `textblob` | Sentiment analysis | ⚡ Optional (fallback included) |

Python ≥ 3.9 required.

---

## Licence

MIT — do whatever you like with it.
