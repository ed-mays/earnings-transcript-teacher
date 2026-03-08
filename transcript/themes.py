"""Theme extraction using NMF (Non-negative Matrix Factorisation).

Discovers the major discussion topics in an earnings transcript by:
1. Segmenting the text into speaker turns (sub-documents).
2. Vectorising turns with TF-IDF.
3. Applying NMF to uncover latent topic clusters.

Each topic is represented as a ranked list of related terms, giving the
user a high-level thematic map of the call.
"""

import re
from dataclasses import dataclass

from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from transcript.keywords import ALL_STOP_WORDS

# Extra stop words for theme extraction — structural / boilerplate language
# that adds noise when NMF tries to form coherent topic clusters.
_THEME_EXTRA_STOPS: list[str] = [
    "proceed", "comes", "line", "ahead", "instructions",
    "conference", "earnings", "corporation",
    "answer", "repeat", "respect",
    "question", "questions",
    "calling", "atif", "steps", "down",  # common operator fragments
]

_THEME_STOP_WORDS: list[str] = sorted(
    set(ALL_STOP_WORDS) | set(_THEME_EXTRA_STOPS)
)

# Matches "First Last: text..." at the start of a line.
# Mirrors _TURN_PATTERN in sections.py but is kept local to avoid a
# circular-import risk if sections.py ever imports from this module.
_TURN_PATTERN: re.Pattern = re.compile(
    r"^(?P<speaker>[A-Z][a-zA-Z\-'.]+(?:\s+[A-Z][a-zA-Z\-'.]+)*)\s*:\s*(?P<text>.+?)(?=\n[A-Z]|\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class Topic:
    """A single discovered theme."""

    label: int  # 0-indexed topic number
    terms: list[str]  # top terms for this topic, most relevant first
    weight: float  # relative prominence (sum of document loadings)


def extract_themes(
    transcript_text: str,
    n_topics: int = 5,
    terms_per_topic: int = 8,
) -> list[Topic]:
    """Discover major themes in a transcript using NMF topic modelling.

    The transcript is split into individual speaker turns, each treated
    as a sub-document.  TF-IDF vectors are computed across all turns and
    then decomposed via NMF to reveal latent topic clusters.

    Args:
        transcript_text: Raw transcript text.
        n_topics: Number of topics to extract.
        terms_per_topic: Number of representative terms per topic.

    Returns:
        List of :class:`Topic` objects sorted by weight (most prominent
        topic first).  Returns an empty list if there are too few
        speaker turns for meaningful decomposition.
    """
    # --- 1. Segment into speaker turns ---------------------------------
    turns = [
        m.group("text").strip()
        for m in _TURN_PATTERN.finditer(transcript_text)
        if (
            m.group("speaker").strip().lower() != "operator"
            and len(m.group("text").strip()) > 50  # skip very short turns
        )
    ]

    if len(turns) < n_topics + 1:
        return []

    # --- 2. Vectorise ---------------------------------------------------
    vectorizer = TfidfVectorizer(
        stop_words=_THEME_STOP_WORDS,
        ngram_range=(1, 2),
        max_features=3000,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#]{1,}\b",
    )

    tfidf_matrix = vectorizer.fit_transform(turns)
    feature_names = vectorizer.get_feature_names_out()

    # --- 3. NMF decomposition -------------------------------------------
    model = NMF(
        n_components=n_topics,
        random_state=42,
        max_iter=400,
    )

    # W = document-topic matrix (turns × topics)
    doc_topic = model.fit_transform(tfidf_matrix)
    # H = topic-term matrix  (topics × features)

    # --- 4. Build Topic objects -----------------------------------------
    topics: list[Topic] = []
    for topic_idx, component in enumerate(model.components_):
        top_indices = component.argsort()[::-1][:terms_per_topic]
        terms = [str(feature_names[i]) for i in top_indices]
        weight = float(doc_topic[:, topic_idx].sum())
        topics.append(Topic(label=topic_idx, terms=terms, weight=weight))

    # Sort by prominence (highest weight first).
    topics.sort(key=lambda t: t.weight, reverse=True)

    return topics
