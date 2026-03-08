"""Embedding generation utilizing the Voyage AI API.

Requires the ``VOYAGE_API_KEY`` environment variable to be set.
"""

import os
import voyageai


def get_embeddings(texts: list[str], model: str = "voyage-finance-2") -> list[list[float]] | None:
    """Generate vector embeddings for a list of texts.

    Handles batching automatically via the Voyage client.

    Args:
        texts: A list of strings to embed.
        model: The Voyage model to use. Defaults to the finance-specialized model.

    Returns:
        A list of embeddings (where each embedding is a list of floats) in the
        same order as the input texts. Returns None if VOYAGE_API_KEY is not set.
    """
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        return None

    client = voyageai.Client(api_key=api_key)
    
    # The Voyage client sdk handles batching automatically via the `embed` method.
    # voyage-finance-2 generates 1024-dimensional float vectors.
    result = client.embed(texts, model=model)
    
    return result.embeddings
