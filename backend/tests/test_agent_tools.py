from unittest.mock import patch

from app.agent.tools import (
    search_knowledge_base,
)
from app.schemas.rag import (
    Citation,
    RAGResponse,
)


@patch(
    "app.agent.tools.answer_question"
)
def test_search_knowledge_base_tool(
    mock_answer_question,
):
    """
    The tool should expose Phase 6 RAG output as a dictionary
    suitable for LangGraph nodes.
    """

    mock_answer_question.return_value = (
        RAGResponse(
            answer=(
                "Refunds take 5 to 10 "
                "business days."
            ),
            grounded=True,
            citations=[
                Citation(
                    source="refund_policy.txt",
                    chunk_index=0,
                    similarity=0.91,
                    metadata={},
                )
            ],
            retrieved_chunks=1,
        )
    )

    result = (
        search_knowledge_base.invoke(
            {
                "question": (
                    "How long does a refund take?"
                )
            }
        )
    )

    assert result["grounded"] is True
    assert result["retrieved_chunks"] == 1

    assert (
        result["citations"][0]["source"]
        == "refund_policy.txt"
    )