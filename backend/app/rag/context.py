from app.schemas.rag import RetrievedChunk


def build_context(
    chunks: list[RetrievedChunk],
) -> str:
    """
    Convert retrieved chunks into clearly separated source blocks.

    Clear source boundaries help the LLM distinguish evidence and
    reduce confusion between multiple retrieved passages.
    """

    if not chunks:
        return ""

    blocks: list[str] = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        blocks.append(
            (
                f"[SOURCE {index}]\n"
                f"Source: {chunk.source_name}\n"
                f"Chunk: {chunk.chunk_index}\n"
                f"Content:\n{chunk.content}"
            )
        )

    return "\n\n".join(
        blocks
    )