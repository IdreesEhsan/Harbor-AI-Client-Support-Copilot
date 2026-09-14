from app.rag.context import build_context
from app.schemas.rag import RetrievedChunk


def test_context_contains_source_information():
    chunks = [
        RetrievedChunk(
            id="chunk-1",
            document_id="document-1",
            source_name="refund_policy.txt",
            content=(
                "Refunds take 5 to 10 business days."
            ),
            chunk_index=0,
            similarity=0.82,
            metadata={},
        )
    ]

    context = build_context(
        chunks
    )

    assert "[SOURCE 1]" in context
    assert "refund_policy.txt" in context
    assert "5 to 10 business days" in context


def test_empty_chunks_return_empty_context():
    assert build_context([]) == ""