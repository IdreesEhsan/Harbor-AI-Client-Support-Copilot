from langchain_core.tools import tool

from app.rag.service import answer_question


@tool
def search_knowledge_base(
    question: str,
) -> dict:
    """
    Search Harbor's knowledge base and generate a grounded answer.

    Use this tool for normal customer-support questions that may be
    answered using Harbor's indexed knowledge-base documents.
    """

    result = answer_question(
        question=question
    )

    return result.model_dump()