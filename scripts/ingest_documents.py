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

# The ingestion script lives outside the backend package, so we add
# backend/ to Python's import path when running it from project root.
sys.path.insert(
    0,
    str(BACKEND_DIR),
)


from app.ingestion.pipeline import (
    process_document,
)


SOURCE_DIR = (
    PROJECT_ROOT
    / "knowledge_base"
    / "source"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "knowledge_base"
    / "processed"
)

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
}


def parse_arguments():
    """Read chunking settings from the command line."""

    parser = argparse.ArgumentParser(
        description="Ingest Harbor knowledge-base documents."
    )

    parser.add_argument(
        "--strategy",
        choices=[
            "fixed",
            "recursive",
        ],
        default="recursive",
        help="Chunking strategy to use.",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Maximum chunk size.",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=120,
        help="Chunk overlap.",
    )

    return parser.parse_args()


def main() -> None:
    """Process all supported documents found in the source directory."""

    args = parse_arguments()

    files = sorted(
        file_path
        for file_path in SOURCE_DIR.iterdir()
        if file_path.is_file()
        and file_path.suffix.lower()
        in SUPPORTED_EXTENSIONS
    )

    if not files:
        print(
            "No supported documents found in knowledge_base/source."
        )

        return

    for file_path in files:
        try:
            output_path = process_document(
                file_path=file_path,
                output_directory=OUTPUT_DIR,
                chunking_strategy=args.strategy,
                chunk_size=args.chunk_size,
                overlap=args.overlap,
            )

            print(
                f"Processed: {file_path.name}"
            )

            print(
                f"Strategy: {args.strategy}"
            )

            print(
                f"Output: {output_path}"
            )

        except Exception as exc:
            print(
                f"Failed: {file_path.name}"
            )

            print(
                f"Reason: {exc}"
            )


if __name__ == "__main__":
    main()