from pathlib import Path

from app.ingestion.loaders import (
    load_document,
)


def test_txt_loader(
    tmp_path: Path,
):
    file_path = (
        tmp_path / "sample.txt"
    )

    file_path.write_text(
        "Harbor knowledge base",
        encoding="utf-8",
    )

    document = load_document(
        file_path
    )

    assert document.file_type == "txt"

    assert (
        document.content
        == "Harbor knowledge base"
    )

    assert (
        document.source
        == "sample.txt"
    )