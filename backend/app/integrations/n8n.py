import logging
from typing import Any

import httpx

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class N8NConfigurationError(Exception):
    """
    Raised when Harbor cannot safely use n8n because the
    production webhook URL has not been configured.
    """


class N8NWebhookError(Exception):
    """
    Raised when Harbor cannot safely deliver an event to n8n.
    """


def get_n8n_webhook_url() -> str:
    """
    Return Harbor's configured n8n Cloud production webhook.

    This value must remain server-side and must never be
    exposed to the React frontend.
    """

    settings = get_settings()

    webhook_url = (
        settings.n8n_ticket_webhook_url
    )

    if (
        not isinstance(webhook_url, str)
        or not webhook_url.strip()
    ):
        raise N8NConfigurationError(
            "n8n ticket webhook URL is not configured."
        )

    return webhook_url.strip()


def build_ticket_execution_event(
    ticket: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert one successfully executed Harbor ticket into the
    normalized event contract expected by n8n.

    Required downstream fields:

    - event_type
    - ticket_id
    - monday_item_id
    - title
    - description
    - severity
    - status
    - source
    - idempotency_key
    """

    required_fields = {
        "id": ticket.get("id"),
        "monday_item_id": ticket.get(
            "monday_item_id"
        ),
        "title": ticket.get("title"),
        "description": ticket.get(
            "description"
        ),
        "severity": ticket.get(
            "severity"
        ),
        "status": ticket.get("status"),
        "idempotency_key": ticket.get(
            "idempotency_key"
        ),
    }

    missing_fields = [
        field_name
        for field_name, value
        in required_fields.items()
        if (
            value is None
            or not str(value).strip()
        )
    ]

    if missing_fields:
        raise N8NWebhookError(
            "Executed ticket cannot be dispatched to n8n "
            "because required fields are missing: "
            + ", ".join(missing_fields)
        )

    return {
        "event_type": "ticket.executed",
        "ticket_id": str(
            ticket["id"]
        ),
        "monday_item_id": str(
            ticket["monday_item_id"]
        ),
        "title": str(
            ticket["title"]
        ),
        "description": str(
            ticket["description"]
        ),
        "severity": str(
            ticket["severity"]
        ),
        "status": str(
            ticket["status"]
        ),
        "source": "harbor",
        "idempotency_key": str(
            ticket["idempotency_key"]
        ),
    }


def send_ticket_execution_event(
    ticket: dict[str, Any],
) -> None:
    """
    Deliver one normalized ticket-execution event to Harbor's
    n8n Cloud workflow.

    Important ordering:

        Monday.com
            ↓
        Harbor persistence
            ↓
        n8n Cloud

    Therefore, an n8n failure must never cause Harbor to
    recreate the Monday.com ticket.

    Downstream duplicate protection uses the deterministic
    Harbor idempotency key.
    """

    settings = get_settings()

    webhook_url = (
        get_n8n_webhook_url()
    )

    payload = (
        build_ticket_execution_event(
            ticket
        )
    )

    try:
        response = httpx.post(
            webhook_url,
            json=payload,
            timeout=(
                settings
                .n8n_webhook_timeout_seconds
            ),
        )

        response.raise_for_status()

    except httpx.TimeoutException as exc:
        logger.exception(
            (
                "n8n Cloud webhook timed out. "
                "ticket_id=%s idempotency_key=%s"
            ),
            payload["ticket_id"],
            payload["idempotency_key"],
        )

        raise N8NWebhookError(
            "n8n Cloud webhook timed out."
        ) from exc

    except httpx.HTTPError as exc:
        logger.exception(
            (
                "n8n Cloud webhook delivery failed. "
                "ticket_id=%s idempotency_key=%s"
            ),
            payload["ticket_id"],
            payload["idempotency_key"],
        )

        raise N8NWebhookError(
            "Ticket event could not be delivered to n8n."
        ) from exc

    logger.info(
        (
            "Ticket execution event delivered to n8n Cloud. "
            "ticket_id=%s idempotency_key=%s"
        ),
        payload["ticket_id"],
        payload["idempotency_key"],
    )