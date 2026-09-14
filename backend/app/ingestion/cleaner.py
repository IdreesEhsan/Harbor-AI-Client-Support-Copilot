import re


def clean_text(text: str) -> str:
    """
    Normalize extracted text while preserving meaningful structure.

    We avoid aggressive cleaning because headings, punctuation,
    and paragraph boundaries may improve retrieval quality later.
    """

    # Normalize different operating-system line endings.
    text = text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    # Collapse repeated spaces and tabs without removing paragraph breaks.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # More than two consecutive newlines usually adds no useful structure.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()