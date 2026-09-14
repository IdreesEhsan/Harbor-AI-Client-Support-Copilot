from functools import lru_cache
from pathlib import Path


BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

PROMPTS_DIR = (
    BACKEND_DIR
    / "prompts"
)


@lru_cache
def load_prompt(
    filename: str,
) -> str:
    """
    Load and cache a Harbor prompt file.

    Prompts live outside Python code so they can later be versioned,
    reviewed, evaluated, and improved independently.
    """

    prompt_path = (
        PROMPTS_DIR
        / filename
    )

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt not found: {prompt_path}"
        )

    return prompt_path.read_text(
        encoding="utf-8"
    ).strip()