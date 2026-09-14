from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


settings = get_settings()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model only once.

    Model initialization is relatively expensive, so Harbor keeps
    one cached model instance and reuses it across indexing and search.
    """

    return SentenceTransformer(
        settings.embedding_model
    )


def embed_texts(
    texts: list[str],
) -> list[list[float]]:
    """
    Convert multiple strings into normalized embedding vectors.

    Batch embedding is more efficient than embedding each chunk
    individually.
    """

    if not texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    vectors = embeddings.tolist()

    # Catch accidental model/schema mismatches early.
    for vector in vectors:
        if len(vector) != settings.embedding_dimension:
            raise ValueError(
                "Embedding dimension mismatch. "
                f"Expected {settings.embedding_dimension}, "
                f"received {len(vector)}."
            )

    return vectors


def embed_query(
    query: str,
) -> list[float]:
    """Generate one embedding vector for a semantic-search query."""

    if not query.strip():
        raise ValueError(
            "Query cannot be empty."
        )

    return embed_texts(
        [query]
    )[0]