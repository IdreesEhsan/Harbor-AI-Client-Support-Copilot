import json

from pydantic import ValidationError

from app.agent.schemas import AgentDecision
from app.core.config import get_settings
from app.core.prompts import load_prompt
from app.rag.generator import get_groq_client
from app.services.memory_service import history_to_text


settings = get_settings()


class AgentRoutingError(Exception):
    """
    Raised when Harbor cannot obtain a valid structured routing
    decision from the LLM.
    """


def classify_request(
    message: str,
    history: list[dict[str, str]] | None = None,
    conversation_summary: str | None = None,
) -> AgentDecision:
    """
    Classify a user request into one of Harbor's supported routes.

    Harbor makes two related routing decisions:

    1. action:
       - answer
       - clarify
       - escalate

    2. answer_source:
       - knowledge_base
       - conversation_memory

    Conversation memory is contextual information supplied during
    the conversation. It must not be treated as authoritative
    Harbor policy or knowledge-base evidence.
    """

    message = message.strip()

    if not message:
        raise ValueError(
            "Message cannot be empty."
        )

    system_prompt = load_prompt(
        "agent_router.txt"
    )

    history = history or []

    # Recent user/assistant messages provide short-term
    # conversational context.
    conversation_context = history_to_text(
        history
    )

    # The summary contains compressed older conversation
    # context when the recent buffer is no longer sufficient.
    summary_context = (
        conversation_summary.strip()
        if conversation_summary
        else "No previous conversation summary."
    )

    user_prompt = f"""
CONVERSATION SUMMARY

{summary_context}

RECENT CONVERSATION

{conversation_context}

CURRENT USER MESSAGE

{message}

ROUTING RULES

Use "knowledge_base" when answering requires authoritative
Harbor information such as policies, procedures, refund rules,
support instructions, product information, or other company
knowledge.

Use "conversation_memory" when the user is asking Harbor to
recall information that the user previously supplied or that
appeared earlier in this conversation.

Examples of conversation-memory questions include:
- "What was my order reference?"
- "What reason did I give for the refund?"
- "What did I tell you earlier?"
- "Did I already say that I contacted support?"
- "Remind me what reference I gave you."

Conversation memory is not verified company policy. Do not use
conversation_memory as the source for authoritative Harbor rules.

If the user asks a policy question that depends on conversational
context, use "knowledge_base". The memory may help interpret the
question, but the factual policy answer must still come from the
knowledge base.

If the user explicitly asks for a human, or the request requires
human review according to Harbor's routing rules, use "escalate".

If there is not enough information to determine what the user is
asking, use "clarify".

Return a JSON object with exactly these fields:

{{
  "action": "answer | clarify | escalate",
  "answer_source": "knowledge_base | conversation_memory",
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