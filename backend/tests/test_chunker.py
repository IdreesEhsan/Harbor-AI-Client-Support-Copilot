import pytest

from app.ingestion.chunker import (
    chunk_document,
)
from app.schemas.document import (
    LoadedDocument,
)


@pytest.fixture
def sample_document() -> LoadedDocument:
    """Provide reusable text for chunking tests."""

    return LoadedDocument(
        source="test.txt",
        file_type="txt",
        content=(
            "Harbor support documentation. "
            * 150
        ),
    )


def test_fixed_chunking_creates_multiple_chunks(
    sample_document,
):
    chunks = chunk_document(
        document=sample_document,
        strategy="fixed",
        chunk_size=300,
        overlap=50,
    )

    assert len(chunks) > 1

    assert chunks[0].chunk_index == 0

    assert (
        chunks[0].metadata[
            "chunking_strategy"
        ]
        == "fixed"
    )


def test_recursive_chunking_creates_multiple_chunks(
    sample_document,
):
    chunks = chunk_document(
        document=sample_document,
        strategy="recursive",
        chunk_size=300,
        overlap=50,
    )

    assert len(chunks) > 1

    assert (
        chunks[0].metadata[
            "chunking_strategy"
        ]
        == "recursive"
    )


def test_overlap_cannot_equal_chunk_size(
    sample_document,
):
    with pytest.raises(ValueError):
        chunk_document(
            document=sample_document,
            strategy="recursive",
            chunk_size=300,
            overlap=300,
        )


def test_overlap_cannot_exceed_chunk_size(
    sample_document,
):
    with pytest.raises(ValueError):
        chunk_document(
            document=sample_document,
            strategy="fixed",
            chunk_size=300,
            overlap=301,
        )


def test_negative_overlap_is_rejected(
    sample_document,
):
    with pytest.raises(ValueError):
        chunk_document(
            document=sample_document,
            strategy="recursive",
            chunk_size=300,
            overlap=-1,
        )