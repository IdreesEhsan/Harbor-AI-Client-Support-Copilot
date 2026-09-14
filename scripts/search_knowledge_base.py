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


from app.rag.embeddings import embed_query
from app.rag.vector_store import similarity_search


def parse_arguments():
    """Read semantic-search settings from the command line."""

    parser = argparse.ArgumentParser(
        description=(
            "Search Harbor's semantic knowledge base."
        )
    )

    parser.add_argument(
        "query",
        type=str,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.35,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    query_embedding = embed_query(
        args.query
    )

    results = similarity_search(
        query_embedding=query_embedding,
        match_threshold=args.threshold,
        match_count=args.limit,
    )

    if not results:
        print(
            "No sufficiently similar knowledge-base "
            "chunks were found."
        )
        return

    print(
        f"\nResults for: {args.query}\n"
    )

    for index, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"--- Result {index} ---"
        )

        print(
            f"Source: {result['source_name']}"
        )

        print(
            f"Similarity: {result['similarity']:.4f}"
        )

        print(
            f"Chunk: {result['chunk_index']}"
        )

        print(
            result["content"]
        )

        print()


if __name__ == "__main__":
    main()