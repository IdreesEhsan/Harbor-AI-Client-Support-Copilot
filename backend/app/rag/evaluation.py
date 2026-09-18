from typing import Any

from app.db.supabase import (
    get_supabase_client,
)

from app.rag.service import (
    answer_question,
)

from app.schemas.rag import (
    RAGEvaluationCaseCreate,
)


# ============================================================
# CASE MANAGEMENT
# ============================================================

def create_evaluation_case(
    payload: RAGEvaluationCaseCreate,
) -> dict[str, Any]:
    client = (
        get_supabase_client()
    )

    response = (
        client
        .table(
            "rag_evaluation_cases"
        )
        .insert(
            {
                "question":
                    payload.question.strip(),

                "expected_answer_contains":
                    payload.expected_answer_contains,

                "expected_sources":
                    payload.expected_sources,

                "expected_grounded":
                    payload.expected_grounded,

                "requester_role":
                    payload.requester_role,

                "is_active":
                    True,
            }
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            (
                "Could not create "
                "RAG evaluation case."
            )
        )

    return (
        response.data[0]
    )


def list_evaluation_cases(
    *,
    active_only: bool = True,
    limit: int = 200,
) -> list[
    dict[str, Any]
]:
    client = (
        get_supabase_client()
    )

    query = (
        client
        .table(
            "rag_evaluation_cases"
        )
        .select("*")
    )

    if active_only:
        query = (
            query.eq(
                "is_active",
                True,
            )
        )

    response = (
        query
        .order(
            "created_at",
            desc=False,
        )
        .limit(
            limit
        )
        .execute()
    )

    return (
        response.data
        or []
    )


# ============================================================
# COMPARISON HELPERS
# ============================================================

def _normalized_text(
    value: str,
) -> str:
    return (
        " ".join(
            value
            .lower()
            .split()
        )
    )


def _answer_matches(
    *,
    actual_answer: str,
    expected_terms: list[str],
) -> bool:
    """
    Every configured expected phrase must occur.

    Empty expected_terms means there is no textual assertion
    for this test case.
    """

    if not expected_terms:
        return True

    actual = (
        _normalized_text(
            actual_answer
        )
    )

    return all(
        _normalized_text(
            expected
        )
        in actual

        for expected
        in expected_terms

        if expected.strip()
    )


def _source_matches(
    *,
    actual_sources: list[str],
    expected_sources: list[str],
) -> bool:
    """
    Every expected source must appear among the citations.

    Empty expected_sources means source identity is not part
    of the test.
    """

    if not expected_sources:
        return True

    normalized_actual = {
        source
        .strip()
        .lower()

        for source
        in actual_sources
    }

    return all(
        expected
        .strip()
        .lower()
        in normalized_actual

        for expected
        in expected_sources

        if expected.strip()
    )


# ============================================================
# RUN EVALUATION
# ============================================================

def run_rag_evaluation(
    *,
    created_by: str | None = None,
) -> dict[str, Any]:
    cases = (
        list_evaluation_cases(
            active_only=True,
            limit=500,
        )
    )

    if not cases:
        raise ValueError(
            (
                "No active RAG evaluation "
                "cases are configured."
            )
        )


    client = (
        get_supabase_client()
    )


    result_rows: list[
        dict[str, Any]
    ] = []


    retrieval_passes = 0

    groundedness_passes = 0

    source_passes = 0

    answer_passes = 0

    overall_passes = 0


    for case in cases:
        response = (
            answer_question(
                question=(
                    case[
                        "question"
                    ]
                ),

                requester_role=(
                    case.get(
                        "requester_role",
                        "customer",
                    )
                ),

                # Evaluation should not pollute production
                # query analytics.
                record_analytics=False,
            )
        )


        actual_sources = list(
            dict.fromkeys(
                citation.source

                for citation
                in response.citations
            )
        )


        expected_grounded = bool(
            case.get(
                "expected_grounded",
                True,
            )
        )


        retrieval_pass = (
            response.retrieved_chunks > 0

            if expected_grounded

            else response.retrieved_chunks == 0
        )


        groundedness_pass = (
            response.grounded
            == expected_grounded
        )


        source_pass = (
            _source_matches(
                actual_sources=(
                    actual_sources
                ),

                expected_sources=(
                    case.get(
                        "expected_sources"
                    )
                    or []
                ),
            )
        )


        answer_pass = (
            _answer_matches(
                actual_answer=(
                    response.answer
                ),

                expected_terms=(
                    case.get(
                        "expected_answer_contains"
                    )
                    or []
                ),
            )
        )


        overall_pass = all(
            [
                retrieval_pass,
                groundedness_pass,
                source_pass,
                answer_pass,
            ]
        )


        retrieval_passes += int(
            retrieval_pass
        )

        groundedness_passes += int(
            groundedness_pass
        )

        source_passes += int(
            source_pass
        )

        answer_passes += int(
            answer_pass
        )

        overall_passes += int(
            overall_pass
        )


        result_rows.append(
            {
                "case_id":
                    str(
                        case[
                            "id"
                        ]
                    ),

                "question":
                    case[
                        "question"
                    ],

                "actual_answer":
                    response.answer,

                "actual_grounded":
                    response.grounded,

                "actual_sources":
                    actual_sources,

                "retrieved_chunks":
                    response.retrieved_chunks,

                "retrieval_pass":
                    retrieval_pass,

                "groundedness_pass":
                    groundedness_pass,

                "source_pass":
                    source_pass,

                "answer_pass":
                    answer_pass,

                "overall_pass":
                    overall_pass,
            }
        )


    total = (
        len(
            cases
        )
    )


    run_response = (
        client
        .table(
            "rag_evaluation_runs"
        )
        .insert(
            {
                "total_cases":
                    total,

                "passed_cases":
                    overall_passes,

                "retrieval_hit_rate":
                    retrieval_passes
                    / total,

                "groundedness_accuracy":
                    groundedness_passes
                    / total,

                "source_accuracy":
                    source_passes
                    / total,

                "answer_accuracy":
                    answer_passes
                    / total,

                "overall_pass_rate":
                    overall_passes
                    / total,

                "created_by":
                    created_by,
            }
        )
        .execute()
    )


    if not run_response.data:
        raise RuntimeError(
            (
                "Could not persist "
                "RAG evaluation run."
            )
        )


    run = (
        run_response.data[0]
    )


    run_id = str(
        run[
            "id"
        ]
    )


    database_results = [
        {
            **row,

            "run_id":
                run_id,
        }

        for row
        in result_rows
    ]


    (
        client
        .table(
            "rag_evaluation_results"
        )
        .insert(
            database_results
        )
        .execute()
    )


    return {
        "run_id":
            run_id,

        "total_cases":
            total,

        "passed_cases":
            overall_passes,

        "retrieval_hit_rate":
            round(
                retrieval_passes
                / total,
                4,
            ),

        "groundedness_accuracy":
            round(
                groundedness_passes
                / total,
                4,
            ),

        "source_accuracy":
            round(
                source_passes
                / total,
                4,
            ),

        "answer_accuracy":
            round(
                answer_passes
                / total,
                4,
            ),

        "overall_pass_rate":
            round(
                overall_passes
                / total,
                4,
            ),

        "results":
            result_rows,
    }


# ============================================================
# HISTORICAL RUNS
# ============================================================

def list_evaluation_runs(
    *,
    limit: int = 50,
) -> list[
    dict[str, Any]
]:
    client = (
        get_supabase_client()
    )

    response = (
        client
        .table(
            "rag_evaluation_runs"
        )
        .select("*")
        .order(
            "created_at",
            desc=True,
        )
        .limit(
            limit
        )
        .execute()
    )

    return (
        response.data
        or []
    )