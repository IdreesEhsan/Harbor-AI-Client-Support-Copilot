import json
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


from app.rag.retriever import retrieve_chunks


CASES_FILE = (
    PROJECT_ROOT
    / "tests"
    / "evaluation"
    / "rag_cases.json"
)


def main() -> None:
    """Measure whether expected KB sources are retrieved."""

    cases = json.loads(
        CASES_FILE.read_text(
            encoding="utf-8"
        )
    )

    answerable_cases = 0
    retrieval_hits = 0

    for case in cases:
        if not case["should_answer"]:
            continue

        answerable_cases += 1

        chunks = retrieve_chunks(
            question=case["question"],
        )

        retrieved_sources = {
            chunk.source_name
            for chunk in chunks
        }

        hit = (
            case["expected_source"]
            in retrieved_sources
        )

        if hit:
            retrieval_hits += 1

        print(
            f"{case['id']}: "
            f"{'HIT' if hit else 'MISS'}"
        )

    hit_rate = (
        retrieval_hits / answerable_cases
        if answerable_cases
        else 0.0
    )

    print()
    print(
        f"Retrieval hit rate: "
        f"{hit_rate:.2%}"
    )


if __name__ == "__main__":
    main()