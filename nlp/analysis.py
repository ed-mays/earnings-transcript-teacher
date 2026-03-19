import string


# Common English function words to exclude from content-word analysis.
STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "nor", "so", "yet", "for", "of",
    "in", "on", "at", "to", "by", "up", "as", "is", "it", "its", "be",
    "am", "are", "was", "were", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "shall", "should", "may",
    "might", "must", "can", "could", "that", "this", "these", "those",
    "i", "we", "you", "he", "she", "they", "me", "us", "him", "her",
    "them", "my", "our", "your", "his", "their", "what", "which", "who",
    "whom", "when", "where", "why", "how", "if", "than", "then", "not",
    "no", "from", "with", "about", "into", "through", "during", "before",
    "after", "above", "below", "between", "each", "both", "all", "more",
    "also", "just", "very", "too", "well", "out", "over", "such", "own",
})

_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def clean_text(text: str) -> str:
    """Converts text to lowercase and removes punctuation."""
    return text.lower().translate(_PUNCT_TABLE)


def tokenize(text: str) -> list[str]:
    """Splits cleaned text into a list of word tokens."""
    return text.split()


def count_word_frequency(
    words: list[str],
    stop_words: frozenset[str] = STOP_WORDS,
) -> list[tuple[str, int]]:
    """Returns content words ranked by frequency, excluding stop words.

    Args:
        words: List of tokens (from `tokenize`).
        stop_words: Set of function words to exclude. Defaults to STOP_WORDS.

    Returns:
        List of (word, count) tuples sorted descending by count.
    """
    counts: dict[str, int] = {}
    for word in words:
        if word not in stop_words:
            counts[word] = counts.get(word, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)
