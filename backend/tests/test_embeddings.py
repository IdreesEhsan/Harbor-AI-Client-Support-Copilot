from app.rag.embeddings import (
    embed_query,
    embed_texts,
)


def test_embed_query_returns_expected_dimension():
    vector = embed_query(
        "Harbor customer support"
    )

    assert len(vector) == 384


def test_embed_texts_returns_one_vector_per_input():
    texts = [
        "Refund policy",
        "Password reset",
    ]

    vectors = embed_texts(
        texts
    )

    assert len(vectors) == 2

    assert all(
        len(vector) == 384
        for vector in vectors
    )