import hashlib


def calculate_content_hash(
    content: str,
) -> str:
    """
    Return a deterministic SHA-256 fingerprint for document content.

    Harbor uses this hash to determine whether a source document
    actually changed before recomputing embeddings.
    """

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()