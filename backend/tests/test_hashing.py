from app.ingestion.hashing import calculate_content_hash


def test_same_content_produces_same_hash():
    text = "Harbor refund policy"

    first = calculate_content_hash(
        text
    )

    second = calculate_content_hash(
        text
    )

    assert first == second


def test_different_content_produces_different_hash():
    first = calculate_content_hash(
        "Original content"
    )

    second = calculate_content_hash(
        "Updated content"
    )

    assert first != second