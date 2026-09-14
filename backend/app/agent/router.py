import json

from pydantic import ValidationError

from app.agent.schemas import AgentDecision
from app.core.config import get_settings
from app.core.prompts import load_prompt
from app.rag.generator import get_groq_client


settings = get_settings()


class AgentRoutingError(Exception):
    """
    Raised when Harbor cannot obtain a valid structured routing
    decision from the LLM.
    """


def classify_request(
    message: str,
) -> AgentDecision:
    """
    Classify a user request into one of Harbor's supported routes.

    The router does not answer the support question. It only decides
    whether the graph should answer, clarify, or escalate.
    """

    message = message.strip()

    if not message:
        raise ValueError(
            "Message cannot be empty."
        )

    system_prompt = load_prompt(
        "agent_router.txt"
    )

    user_prompt = f"""
USER MESSAGE

{message}

Return a JSON object with exactly these fields:

{{
  "action": "answer | clarify | escalate",
  "reason": "short explanation",
  "severity": "low | medium | high | critical",
  "confidence": 0.0
}}
""".strip()

    client = get_groq_client()

    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.0,
            response_format={
                "type": "json_object"
            },
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            raise AgentRoutingError(
                "Groq returned an empty routing response."
            )

        raw_decision = json.loads(
            content
        )

        return AgentDecision.model_validate(
            raw_decision
        )

    except (
        json.JSONDecodeError,
        ValidationError,
    ) as exc:
        raise AgentRoutingError(
            "Groq returned an invalid routing decision."
        ) from exc