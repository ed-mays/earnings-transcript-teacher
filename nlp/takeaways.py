"""Key takeaway extraction using TextRank.

Surfaces the most important statements from an earnings transcript by:
1. Parsing speaker turns and splitting into sentences.
2. Building a cosine-similarity graph over TF-IDF sentence vectors.
3. Running iterative PageRank to rank sentences by centrality.

Sentences that share vocabulary with many other sentences score
highest — these tend to be summary-level, high-signal statements.
"""

import re
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from nlp.keywords import ALL_STOP_WORDS
from parsing.sections import TURN_PATTERN

# Sentence boundary: split on period/question-mark/exclamation followed by
# whitespace and a capital letter.  Simple but effective for transcript prose.
_SENTENCE_SPLIT: re.Pattern = re.compile(
    r"[.!?]\s+(?=[A-Z])",
)


@dataclass
class Takeaway:
    """A single key statement extracted from the transcript."""

    speaker: str  # who said it
    text: str  # the sentence
    score: float  # TextRank centrality score


def _split_sentences(text: str) -> list[str]:
    """Split a block of text into sentences, filtering out short fragments."""
    raw = _SENTENCE_SPLIT.split(text)
    return [s.strip() for s in raw if len(s.strip()) >= 40]


def _pagerank(
    similarity_matrix: np.ndarray,
    damping: float = 0.85,
    max_iter: int = 30,
    tol: float = 1e-6,
) -> np.ndarray:
    """Compute PageRank scores over a similarity graph.

    Args:
        similarity_matrix: Square matrix of pairwise similarities.
        damping: Probability of following an edge (vs. random jump).
        max_iter: Maximum iterations.
        tol: Convergence tolerance.

    Returns:
        1-D array of scores, one per node (sentence).
    """
    n = similarity_matrix.shape[0]
    if n == 0:
        return np.array([])

    # Row-normalise: each row sums to 1 (transition probabilities).
    row_sums = similarity_matrix.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # avoid division by zero
    transition = similarity_matrix / row_sums

    scores = np.ones(n) / n

    for _ in range(max_iter):
        prev = scores.copy()
        scores = (1 - damping) / n + damping * transition.T @ scores
        if np.abs(scores - prev).sum() < tol:
            break

    return scores


def extract_takeaways(
    transcript_text: str,
    top_n: int = 10,
) -> list[Takeaway]:
    """Extract key statements from a transcript using TextRank.

    Args:
        transcript_text: Raw transcript text.
        top_n: Number of takeaways to return.

    Returns:
        List of :class:`Takeaway` objects sorted by TextRank score
        (most central statement first).
    """
    # --- 1. Parse speaker turns, split into attributed sentences --------
    attributed: list[tuple[str, str]] = []  # (speaker, sentence)

    for m in TURN_PATTERN.finditer(transcript_text):
        speaker = m.group("speaker").strip()
        if speaker.lower() == "operator":
            continue
        sentences = _split_sentences(m.group("text").strip())
        for sent in sentences:
            attributed.append((speaker, sent))

    if len(attributed) < 3:
        return []

    speakers = [a[0] for a in attributed]
    sentences = [a[1] for a in attributed]

    # --- 2. Vectorise sentences -----------------------------------------
    vectorizer = TfidfVectorizer(
        stop_words=ALL_STOP_WORDS,
        max_features=3000,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#]{1,}\b",
    )

    tfidf_matrix = vectorizer.fit_transform(sentences)

    # --- 3. Build similarity graph & run PageRank -----------------------
    sim_matrix = cosine_similarity(tfidf_matrix)
    # Zero out self-similarity to avoid self-loops.
    np.fill_diagonal(sim_matrix, 0)

    scores = _pagerank(sim_matrix)

    # --- 4. Rank and return top N ---------------------------------------
    ranked_indices = scores.argsort()[::-1][:top_n]

    return [
        Takeaway(
            speaker=speakers[i],
            text=sentences[i],
            score=float(scores[i]),
        )
        for i in ranked_indices
    ]
