import json
import logging
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

class MondayConfigurationError(Exception):
    """
    Required Monday integration configuration is missing.
    """


class MondayAPIError(Exception):
    """
    Monday communication or GraphQL processing failed.
    """


# ============================================================
# TIMING
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

def get_monday_configuration() -> dict[
    str,
    str
]:
    settings = (
        get_settings()
    )


    required_settings = {
        "api_token":
            settings.monday_api_token,

        "api_url":
            settings.monday_api_url,

        "board_id":
            settings.monday_board_id,

        "group_id":
            settings.monday_group_id,

        "harbor_ticket_id_column_id":
            (
                settings
                .monday_harbor_ticket_id_column_id
            ),

        "status_column_id":
            (
                settings
                .monday_status_column_id
            ),

        "idempotency_key_column_id":
            (
                settings
                .monday_idempotency_key_column_id
            ),

        "description_column_id":
            (
                settings
                .monday_description_column_id
            ),

        "severity_column_id":
            (
                settings
                .monday_severity_column_id
            ),
    }


    missing = [
        name

        for (
            name,
            value
        )
        in required_settings.items()

        if not value
    ]


    if missing:
        raise MondayConfigurationError(
            (
                "Monday.com configuration "
                "is incomplete: "
                + ", ".join(
                    missing
                )
            )
        )


    return {
        key:
            str(
                value
            )

        for (
            key,
            value
        )
        in required_settings.items()
    }


# ============================================================
# HEADERS
# ============================================================

def _build_headers(
    api_token: str,
) -> dict[str, str]:
    return {
        "Authorization":
            api_token,

        "Content-Type":
            "application/json",
    }


# ============================================================
# GRAPHQL TRANSPORT
# ============================================================

def _execute_graphql(
    *,
    query: str,
    variables: dict[str, Any],
    config: dict[str, str],
    operation_name: str,
) -> dict[str, Any]:
    started_at = (
        perf_counter()
    )


    try:
        response = (
            httpx.post(
                config[
                    "api_url"
                ],

                headers=(
                    _build_headers(
                        config[
                            "api_token"
                        ]
                    )
                ),

                json={
                    "query":
                        query,

                    "variables":
                        variables,
                },

                timeout=15.0,
            )
        )


        response.raise_for_status()


    except httpx.TimeoutException as exc:
        logger.exception(
            (
                "Monday operation timed out | "
                "operation=%s | "
                "duration_ms=%.2f"
            ),
            operation_name,
            _milliseconds(
                started_at
            ),
        )


        raise MondayAPIError(
            "Monday.com request timed out."
        ) from exc


    except httpx.HTTPError as exc:
        logger.exception(
            (
                "Monday HTTP request failed | "
                "operation=%s | "
                "duration_ms=%.2f"
            ),
            operation_name,
            _milliseconds(
                started_at
            ),
        )


        raise MondayAPIError(
            "Monday.com request failed."
        ) from exc


    try:
        payload = (
            response.json()
        )


    except ValueError as exc:
        raise MondayAPIError(
            (
                "Monday.com returned "
                "invalid JSON."
            )
        ) from exc


    if not isinstance(
        payload,
        dict,
    ):
        raise MondayAPIError(
            (
                "Monday.com returned "
                "an invalid response."
            )
        )


    graphql_errors = (
        payload.get(
            "errors"
        )
    )


    if graphql_errors:
        logger.error(
            (
                "Monday GraphQL error | "
                "operation=%s | "
                "duration_ms=%.2f | "
                "error_count=%s"
            ),
            operation_name,
            _milliseconds(
                started_at
            ),
            (
                len(
                    graphql_errors
                )
                if isinstance(
                    graphql_errors,
                    list,
                )
                else 1
            ),
        )


        raise MondayAPIError(
            (
                "Monday.com returned "
                "GraphQL errors."
            )
        )


    data = (
        payload.get(
            "data"
        )
    )


    if not isinstance(
        data,
        dict,
    ):
        raise MondayAPIError(
            (
                "Monday.com response did "
                "not contain valid "
                "GraphQL data."
            )
        )


    logger.info(
        (
            "Monday operation completed | "
            "operation=%s | "
            "duration_ms=%.2f"
        ),
        operation_name,
        _milliseconds(
            started_at
        ),
    )


    return data


# ============================================================
# SEVERITY
# ============================================================

def normalize_severity(
    severity: str,
) -> str:
    mapping = {
        "low":
            "Low",

        "medium":
            "Medium",

        "high":
            "High",

        "critical":
            "Critical",
    }


    try:
        return mapping[
            severity
        ]


    except KeyError as exc:
        raise ValueError(
            (
                "Unsupported ticket "
                f"severity: {severity}"
            )
        ) from exc


# ============================================================
# IDEMPOTENCY LOOKUP
# ============================================================

def find_support_ticket_by_idempotency_key(
    *,
    idempotency_key: str,
) -> dict[str, Any] | None:
    if not isinstance(
        idempotency_key,
        str,
    ):
        raise TypeError(
            (
                "idempotency_key must "
                "be a string."
            )
        )


    idempotency_key = (
        idempotency_key.strip()
    )


    if not idempotency_key:
        raise ValueError(
            (
                "idempotency_key "
                "cannot be empty."
            )
        )


    config = (
        get_monday_configuration()
    )


    query = """
    query FindHarborTicketByIdempotencyKey(
        $boardId: ID!,
        $columnId: String!,
        $columnValues: [String]!
    ) {
        items_page_by_column_values(
            board_id: $boardId,
            limit: 2,
            columns: [
                {
                    column_id: $columnId,
                    column_values: $columnValues
                }
            ]
        ) {
            items {
                id
                name
            }
        }
    }
    """


    variables = {
        "boardId":
            config[
                "board_id"
            ],

        "columnId":
            config[
                "idempotency_key_column_id"
            ],

        "columnValues": [
            idempotency_key
        ],
    }


    data = (
        _execute_graphql(
            query=query,
            variables=variables,
            config=config,
            operation_name=(
                "find_ticket_by_idempotency_key"
            ),
        )
    )


    page = (
        data.get(
            "items_page_by_column_values"
        )
    )


    if not isinstance(
        page,
        dict,
    ):
        raise MondayAPIError(
            (
                "Monday.com response did "
                "not contain an item "
                "search result."
            )
        )


    items = (
        page.get(
            "items"
        )
    )


    if not isinstance(
        items,
        list,
    ):
        raise MondayAPIError(
            (
                "Monday.com response "
                "contained an invalid "
                "item search result."
            )
        )


    if not items:
        logger.info(
            (
                "No existing Monday item "
                "found for Harbor "
                "idempotency key."
            )
        )

        return None


    if len(
        items
    ) > 1:
        raise MondayAPIError(
            (
                "Multiple Monday.com items "
                "were found for the same "
                "Harbor idempotency key."
            )
        )


    item = (
        items[0]
    )


    if (
        not isinstance(
            item,
            dict,
        )
        or not item.get(
            "id"
        )
    ):
        raise MondayAPIError(
            (
                "Monday.com returned an "
                "invalid matching item."
            )
        )


    logger.info(
        (
            "Existing Monday item recovered | "
            "monday_item_id=%s"
        ),
        item[
            "id"
        ],
    )


    return {
        "id":
            str(
                item[
                    "id"
                ]
            ),

        "name":
            item.get(
                "name"
            ),
    }


# ============================================================
# CREATE MONDAY ITEM
# ============================================================

def create_support_ticket_item(
    *,
    title: str,
    description: str,
    severity: str,
    harbor_ticket_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    if not isinstance(
        title,
        str,
    ):
        raise TypeError(
            "title must be a string."
        )


    if not isinstance(
        description,
        str,
    ):
        raise TypeError(
            "description must be a string."
        )


    title = (
        title.strip()
    )


    description = (
        description.strip()
    )


    if not title:
        raise ValueError(
            "title cannot be empty."
        )


    if not description:
        raise ValueError(
            "description cannot be empty."
        )


    monday_severity = (
        normalize_severity(
            severity
        )
    )


    config = (
        get_monday_configuration()
    )


    mutation = """
    mutation CreateHarborSupportTicket(
        $boardId: ID!,
        $groupId: String!,
        $itemName: String!,
        $columnValues: JSON!
    ) {
        create_item(
            board_id: $boardId,
            group_id: $groupId,
            item_name: $itemName,
            column_values: $columnValues
        ) {
            id
            name
        }
    }
    """


    column_values = {
        config[
            "harbor_ticket_id_column_id"
        ]:
            harbor_ticket_id,

        config[
            "status_column_id"
        ]: {
            "label":
                "Open",
        },

        config[
            "idempotency_key_column_id"
        ]:
            idempotency_key,

        config[
            "description_column_id"
        ]:
            description,

        config[
            "severity_column_id"
        ]: {
            "label":
                monday_severity,
        },
    }


    variables = {
        "boardId":
            config[
                "board_id"
            ],

        "groupId":
            config[
                "group_id"
            ],

        "itemName":
            title,

        "columnValues":
            json.dumps(
                column_values
            ),
    }


    data = (
        _execute_graphql(
            query=mutation,
            variables=variables,
            config=config,
            operation_name=(
                "create_support_ticket"
            ),
        )
    )


    item = (
        data.get(
            "create_item"
        )
    )


    if (
        not isinstance(
            item,
            dict,
        )
        or not item.get(
            "id"
        )
    ):
        raise MondayAPIError(
            (
                "Monday.com response did "
                "not contain a "
                "created item."
            )
        )


    logger.info(
        (
            "Monday support ticket created | "
            "harbor_ticket_id=%s | "
            "monday_item_id=%s"
        ),
        harbor_ticket_id,
        item[
            "id"
        ],
    )


    return {
        "id":
            str(
                item[
                    "id"
                ]
            ),

        "name":
            item.get(
                "name",
                title,
            ),
    }