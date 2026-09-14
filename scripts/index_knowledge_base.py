import argparse
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

BACKEND_DIR = (
    PROJECT_ROOT
    / "backend"
)

sys.path.insert(
    0,
    str(BACKEND_DIR),
)


from app.rag.indexer import index_document


SOURCE_DIR = (
    PROJECT_ROOT
    / "knowledge_base"
    / "source"
)

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
}


def parse_arguments():
    """Read indexing configuration from the command line."""

    parser = argparse.ArgumentParser(
        description=(
            "Index Harbor knowledge-base documents "
            "into Supabase pgvector."
        )
    )

    parser.add_argument(
        "--strategy",
        choices=[
            "fixed",
            "recursive",
        ],
        default="recursive",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=800,
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=120,
    )

    return parser.parse_args()


def main() -> None:
    """Index all supported source documents."""

    args = parse_arguments()

    if not SOURCE_DIR.exists():
        print(
            "Knowledge-base source directory does not exist."
        )
        return

    files = sorted(
        file_path
        for file_path in SOURCE_DIR.iterdir()
        if file_path.is_file()
        and file_path.suffix.lower()
        in SUPPORTED_EXTENSIONS
    )

    if not files:
        print(
            "No supported knowledge-base documents found."
        )
        return

    for file_path in files:
        try:
            result = index_document(
                file_path=file_path,
                strategy=args.strategy,
                chunk_size=args.chunk_size,
                overlap=args.overlap,
            )

            print(
                f"{result['source']}: "
                f"{result['status']}"
            )

            if result["status"] == "indexed":
                print(
                    f"Chunks stored: "
                    f"{result['chunks']}"
                )

        except Exception as exc:
            print(
                f"{file_path.name}: failed"
            )

            print(
                f"Reason: {exc}"
            )


if __name__ == "__main__":
    main()