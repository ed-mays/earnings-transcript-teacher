"""Keyword extraction using TF-IDF scoring.

Surfaces the most salient terms (single words and bigrams) from a transcript
by computing TF-IDF scores. This is Increment 1 of the concept-analysis
pipeline; future increments will add domain-dictionary boosting, topic
modelling, and extractive summarisation.
"""

from sklearn.feature_extraction.text import TfidfVectorizer

from transcript.analysis import STOP_WORDS

# Additional stop words common in earnings-call boilerplate that add noise
# to keyword results.  These supplement the general-purpose STOP_WORDS set
# defined in analysis.py.
_EARNINGS_STOP_WORDS: frozenset[str] = frozenset({
    "thank", "thanks", "question", "yeah", "yes", "okay", "ok",
    "going", "think", "said", "say", "know", "want", "look",
    "like", "got", "get", "go", "let", "right", "really",
    "thing", "things", "sure", "good", "great", "lot",
    "year", "quarter", "years", "quarters",
    "people", "guys", "bit", "way", "kind",
    "dont", "didnt", "thats", "youre", "weve", "theyre", "youve",
    "hes", "shes", "wasnt", "werent", "isnt", "arent", "wont",
    "doesnt", "havent", "hasnt", "couldnt", "wouldnt", "shouldnt",
    "ive", "im", "ill", "id", "hell", "shed", "theyd", "whats",
    # Contractions fragments left after punctuation stripping
    "re", "ll", "ve", "didn", "doesn", "isn", "aren", "wasn",
    "weren", "won", "couldn", "wouldn", "shouldn", "hasn", "haven",
    # Transcript-specific noise
    "operator", "please", "maybe", "there", "time", "new",
    "continue", "see", "well", "make", "take", "come", "back",
    "first", "second", "third", "next", "last",
    "call", "today", "morning", "afternoon",
})

ALL_STOP_WORDS: list[str] = sorted(STOP_WORDS | _EARNINGS_STOP_WORDS)


def extract_keywords(
    transcript_text: str,
    top_n: int = 20,
) -> list[tuple[str, float]]:
    """Extract salient keywords from a transcript using TF-IDF.

    Scores every unigram and bigram in the text and returns the highest-
    scoring terms.  Stop words (general English + earnings-call boilerplate)
    are excluded automatically.

    Args:
        transcript_text: Cleaned / normalised transcript body.
        top_n: Number of keywords to return.

    Returns:
        List of ``(term, tfidf_score)`` tuples sorted descending by score.
    """
    vectorizer = TfidfVectorizer(
        stop_words=ALL_STOP_WORDS,
        ngram_range=(1, 2),
        max_features=5000,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#]{1,}\b",  # 2+ char alpha tokens
    )

    tfidf_matrix = vectorizer.fit_transform([transcript_text])
    feature_names = vectorizer.get_feature_names_out()
    scores = tfidf_matrix.toarray()[0]

    # Pair each term with its score, sort descending, and take the top N.
    ranked = sorted(
        zip(feature_names, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    return [(term, float(score)) for term, score in ranked[:top_n]]
