import logging
import threading
from time import perf_counter
from typing import Any

import httpx

from app.core.config import (
    get_settings,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# EXCEPTIONS
# ============================================================

class N8NConfigurationError(Exception):
    """
    Raised when Harbor cannot safely use n8n because the
    production webhook URL has not been configured.
    """


class N8NWebhookError(Exception):
    """
    Raised when Harbor cannot safely deliver an event to n8n.
    """


# ============================================================
# HELPERS
# ============================================================

def _milliseconds(
    started_at: float,
) -> float:
    return (
        (
            perf_counter()
            - started_at
        )
        * 1000
    )


# ============================================================
# CONFIGURATION
# ============================================================

def get_n8n_webhook_url() -> str:
    """
    Return Harbor's configured production n8n webhook.

    The URL remains server-side and must never be exposed
    to the React frontend.
    """

    settings = (
        get_settings()
    )


    webhook_url = (
        settings
        .n8n_ticket_webhook_url
    )


    if (
        not isinstance(
            webhook_url,
            str,
        )
        or not webhook_url.strip()
    ):
        raise N8NConfigurationError(
            (
                "n8n ticket webhook URL "
                "is not configured."
            )
        )


    return (
        webhook_url.strip()
    )


# ============================================================
# EVENT CONTRACT
# ============================================================

def build_ticket_execution_event(
    ticket: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert one successfully executed Harbor ticket into
    the normalized event contract consumed by n8n.

    This contract is intentionally independent from the
    internal database shape so downstream automation does
    not depend directly on Harbor's persistence model.
    """

    required_fields = {
        "id":
            ticket.get(
                "id"
            ),

        "monday_item_id":
            ticket.get(
                "monday_item_id"
            ),

        "title":
            ticket.get(
                "title"
            ),

        "description":
            ticket.get(
                "description"
            ),

        "severity":
            ticket.get(
                "severity"
            ),

        "status":
            ticket.get(
                "status"
            ),

        "idempotency_key":
            ticket.get(
                "idempotency_key"
            ),
    }


    missing_fields = [
        field_name

        for (
            field_name,
            value
        )
        in required_fields.items()

        if (
            value is None
            or not str(
                value
            ).strip()
        )
    ]


    if missing_fields:
        raise N8NWebhookError(
            (
                "Executed ticket cannot be "
                "dispatched to n8n because "
                "required fields are missing: "
                + ", ".join(
                    missing_fields
                )
            )
        )


    return {
        "event_type":
            "ticket.executed",

        "event_version":
            "1.0",

        "source":
            "harbor",

        "ticket_id":
            str(
                ticket[
                    "id"
                ]
            ),

        "conversation_id":
            (
                str(
                    ticket[
                        "conversation_id"
                    ]
                )
                if ticket.get(
                    "conversation_id"
                )
                else None
            ),

        "customer_id":
            (
                str(
                    ticket[
                        "user_id"
                    ]
                )
                if ticket.get(
                    "user_id"
                )
                else None
            ),

        "monday_item_id":
            str(
                ticket[
                    "monday_item_id"
                ]
            ),

        "title":
            str(
                ticket[
                    "title"
                ]
            ),

        "description":
            str(
                ticket[
                    "description"
                ]
            ),

        "severity":
            str(
                ticket[
                    "severity"
                ]
            ),

        "status":
            str(
                ticket[
                    "status"
                ]
            ),

        "approval_status":
            (
                str(
                    ticket[
                        "approval_status"
                    ]
                )
                if ticket.get(
                    "approval_status"
                )
                else None
            ),

        "approved_by":
            (
                str(
                    ticket[
                        "approved_by"
                    ]
                )
                if ticket.get(
                    "approved_by"
                )
                else None
            ),

        "approved_at":
            ticket.get(
                "approved_at"
            ),

        "executed_at":
            ticket.get(
                "executed_at"
            )
            or ticket.get(
                "updated_at"
            ),

        "idempotency_key":
            str(
                ticket[
                    "idempotency_key"
                ]
            ),
    }


# ============================================================
# SYNCHRONOUS DELIVERY
# ============================================================

def send_ticket_execution_event(
    ticket: dict[str, Any],
) -> None:
    """
    Deliver one normalized execution event to n8n.

    This function is synchronous and is useful when the
    caller explicitly wants delivery confirmation.

    Harbor's normal ticket execution path uses the
    non-blocking dispatcher below.
    """

    total_started_at = (
        perf_counter()
    )


    settings = (
        get_settings()
    )


    webhook_url = (
        get_n8n_webhook_url()
    )


    payload = (
        build_ticket_execution_event(
            ticket
        )
    )


    try:
        response = (
            httpx.post(
                webhook_url,

                json=payload,

                timeout=(
                    settings
                    .n8n_webhook_timeout_seconds
                ),
            )
        )


        response.raise_for_status()


    except httpx.TimeoutException as exc:
        logger.exception(
            (
                "n8n webhook timed out | "
                "ticket_id=%s | "
                "idempotency_key=%s | "
                "duration_ms=%.2f"
            ),
            payload[
                "ticket_id"
            ],
            payload[
                "idempotency_key"
            ],
            _milliseconds(
                total_started_at
            ),
        )


        raise N8NWebhookError(
            "n8n Cloud webhook timed out."
        ) from exc


    except httpx.HTTPError as exc:
        logger.exception(
            (
                "n8n webhook delivery failed | "
                "ticket_id=%s | "
                "idempotency_key=%s | "
                "duration_ms=%.2f"
            ),
            payload[
                "ticket_id"
            ],
            payload[
                "idempotency_key"
            ],
            _milliseconds(
                total_started_at
            ),
        )


        raise N8NWebhookError(
            (
                "Ticket event could not "
                "be delivered to n8n."
            )
        ) from exc


    logger.info(
        (
            "Ticket execution event delivered "
            "to n8n | "
            "ticket_id=%s | "
            "idempotency_key=%s | "
            "duration_ms=%.2f"
        ),
        payload[
            "ticket_id"
        ],
        payload[
            "idempotency_key"
        ],
        _milliseconds(
            total_started_at
        ),
    )


# ============================================================
# BACKGROUND DELIVERY WORKER
# ============================================================

def _background_delivery_worker(
    ticket: dict[str, Any],
) -> None:
    """
    Background worker used by Harbor's non-blocking
    execution path.

    n8n errors are intentionally logged rather than
    propagated because Monday.com + Harbor persistence have
    already succeeded by the time this worker runs.
    """

    try:
        send_ticket_execution_event(
            ticket
        )


    except N8NConfigurationError:
        logger.exception(
            (
                "Ticket execution succeeded but "
                "n8n is not configured | "
                "ticket_id=%s"
            ),
            ticket.get(
                "id"
            ),
        )


    except N8NWebhookError:
        logger.exception(
            (
                "Ticket execution succeeded but "
                "n8n delivery failed | "
                "ticket_id=%s"
            ),
            ticket.get(
                "id"
            ),
        )


    except Exception:
        logger.exception(
            (
                "Unexpected n8n background "
                "delivery failure | "
                "ticket_id=%s"
            ),
            ticket.get(
                "id"
            ),
        )


# ============================================================
# NON-BLOCKING DISPATCH
# ============================================================

def dispatch_ticket_execution_event(
    ticket: dict[str, Any],
) -> None:
    """
    Dispatch the ticket-execution event without making the
    user's Execute request wait for n8n.

    Staff receives the Harbor execution result immediately
    after Monday.com + Harbor persistence succeed.

    The n8n workflow then continues independently.

    For a larger distributed deployment, replace this
    thread-based dispatcher with a durable queue/outbox.
    """

    if not isinstance(
        ticket,
        dict,
    ):
        raise TypeError(
            "ticket must be a dictionary."
        )


    ticket_snapshot = (
        dict(
            ticket
        )
    )


    worker = threading.Thread(
        target=(
            _background_delivery_worker
        ),

        args=(
            ticket_snapshot,
        ),

        name=(
            "harbor-n8n-"
            + str(
                ticket.get(
                    "id",
                    "event",
                )
            )[
                :12
            ]
        ),

        daemon=True,
    )


    worker.start()


    logger.info(
        (
            "Ticket execution event queued "
            "for background n8n delivery | "
            "ticket_id=%s"
        ),
        ticket.get(
            "id"
        ),
    )