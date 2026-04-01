"""Factory for realistic VoyageAI embedding responses — no live API call.

voyage-finance-2 produces 1024-dimensional unit-normalized float vectors.
These factories return vectors with the correct shape and approximate statistics
(zero mean, unit norm) so consumers that do cosine similarity comparisons behave
realistically in tests.
"""

import math
import random
from typing import Iterator

VOYAGE_FINANCE_2_DIM = 1024


def embedding(dim: int = VOYAGE_FINANCE_2_DIM, seed: int | None = None) -> list[float]:
    """Return a single unit-normalized embedding vector.

    Args:
        dim: Dimensionality of the vector. Defaults to 1024 (voyage-finance-2).
        seed: Optional RNG seed for reproducible vectors.
    """
    rng = random.Random(seed)
    vec = [rng.gauss(0.0, 1.0) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec]


def embeddings(n: int, dim: int = VOYAGE_FINANCE_2_DIM, seed: int | None = None) -> list[list[float]]:
    """Return n unit-normalized embedding vectors.

    Args:
        n: Number of vectors to generate.
        dim: Dimensionality of each vector. Defaults to 1024.
        seed: Optional base seed; each vector uses seed+i for reproducibility.
    """
    return [
        embedding(dim, seed=(seed + i if seed is not None else None))
        for i in range(n)
    ]


def embed_result(texts: list[str], dim: int = VOYAGE_FINANCE_2_DIM, seed: int | None = None):
    """Return a mock that mimics a voyageai.EmbeddingsObject.

    The returned object has:
        .embeddings  — list of unit-normalized float vectors, one per text
        .total_tokens — integer approximation of token count

    Usage::

        with patch("voyageai.Client") as MockClient:
            MockClient.return_value.embed.return_value = embed_result(texts=["hello"])
    """

    class _EmbedResult:
        def __init__(self, texts: list[str], dim: int, seed: int | None) -> None:
            """Build a realistic embed result for the given texts."""
            self.embeddings = embeddings(len(texts), dim=dim, seed=seed)
            # Rough token estimate: ~1.3 tokens per word, minimum 1
            self.total_tokens = max(1, sum(len(t.split()) for t in texts) * 13 // 10)

    return _EmbedResult(texts, dim, seed)
