import json
from typing import Any

import httpx

from app.core.config import get_settings


class MondayConfigurationError(Exception):
    """
    Raised when Harbor cannot safely use Monday.com because
    required integration configuration is missing.
    """


class MondayAPIError(Exception):
    """
    Raised when communication with Monday.com fails or
    Monday returns an invalid GraphQL response.
    """


def get_monday_configuration() -> dict[str, str]:
    """
    Load and validate the Monday.com integration settings.

    Validation occurs only when Monday functionality is used,
    allowing the rest of Harbor to run without this optional
    external integration.
    """

    settings = get_settings()

    required_settings = {
        "api_token": settings.monday_api_token,
        "api_url": settings.monday_api_url,
        "board_id": settings.monday_board_id,
        "group_id": settings.monday_group_id,
        "harbor_ticket_id_column_id": (
            settings.monday_harbor_ticket_id_column_id
        ),
        "status_column_id": (
            settings.monday_status_column_id
        ),
        "idempotency_key_column_id": (
            settings.monday_idempotency_key_column_id
        ),
        "description_column_id": (
            settings.monday_description_column_id
        ),
        "severity_column_id": (
            settings.monday_severity_column_id
        ),
    }

    missing = [
        name
        for name, value in required_settings.items()
        if not value
    ]

    if missing:
        raise MondayConfigurationError(
            "Monday.com configuration is incomplete: "
            + ", ".join(missing)
        )

    return {
        key: str(value)
        for key, value in required_settings.items()
    }


def _build_headers(
    api_token: str,
) -> dict[str, str]:
    """
    Build the HTTP headers required by Monday.com.

    Keeping header construction centralized reduces the
    chance of inconsistent authentication between queries
    and mutations.
    """

    return {
        "Authorization": api_token,
        "Content-Type": "application/json",
    }


def _execute_graphql(
    *,
    query: str,
    variables: dict[str, Any],
    config: dict[str, str],
) -> dict[str, Any]:
    """
    Execute one Monday.com GraphQL request safely.

    HTTP failures, invalid JSON, and GraphQL-level errors are
    normalized into MondayAPIError so callers do not need to
    understand transport-specific failure details.

    Secrets and raw authorization headers are never included
    in raised error messages.
    """

    try:
        response = httpx.post(
            config["api_url"],
            headers=_build_headers(
                config["api_token"]
            ),
            json={
                "query": query,
                "variables": variables,
            },
            timeout=15.0,
        )

        response.raise_for_status()

    except httpx.HTTPError as exc:
        raise MondayAPIError(
            "Monday.com request failed."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise MondayAPIError(
            "Monday.com returned invalid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise MondayAPIError(
            "Monday.com returned an invalid response."
        )

    if payload.get("errors"):
        raise MondayAPIError(
            "Monday.com returned GraphQL errors."
        )

    data = payload.get("data")

    if not isinstance(data, dict):
        raise MondayAPIError(
            "Monday.com response did not contain "
            "valid GraphQL data."
        )

    return data


def normalize_severity(
    severity: str,
) -> str:
    """
    Convert Harbor's internal severity value into the exact
    label configured on the Monday Severity column.
    """

    mapping = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
    }

    try:
        return mapping[severity]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported ticket severity: {severity}"
        ) from exc


def find_support_ticket_by_idempotency_key(
    *,
    idempotency_key: str,
) -> dict[str, Any] | None:
    """
    Search Harbor's Monday board for an existing item with
    the exact idempotency key.

    This lookup is used before creating an external support
    item. If a previous attempt created the Monday item but
    Harbor failed before saving its external ID, the existing
    item can be recovered instead of creating a duplicate.

    Returns:
        A minimal Monday item dictionary when found.
        None when no matching item exists.

    Raises:
        TypeError:
            If idempotency_key is not a string.

        ValueError:
            If idempotency_key is empty.

        MondayAPIError:
            If Monday cannot be queried safely.
    """

    if not isinstance(
        idempotency_key,
        str,
    ):
        raise TypeError(
            "idempotency_key must be a string."
        )

    idempotency_key = (
        idempotency_key.strip()
    )

    if not idempotency_key:
        raise ValueError(
            "idempotency_key cannot be empty."
        )

    config = get_monday_configuration()

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
        "boardId": config["board_id"],
        "columnId": (
            config[
                "idempotency_key_column_id"
            ]
        ),
        "columnValues": [
            idempotency_key
        ],
    }

    data = _execute_graphql(
        query=query,
        variables=variables,
        config=config,
    )

    page = data.get(
        "items_page_by_column_values"
    )

    if not isinstance(page, dict):
        raise MondayAPIError(
            "Monday.com response did not contain "
            "an item search result."
        )

    items = page.get("items")

    if not isinstance(items, list):
        raise MondayAPIError(
            "Monday.com response contained an invalid "
            "item search result."
        )

    if not items:
        return None

    # Harbor expects its idempotency key to uniquely identify
    # one external escalation. More than one match means the
    # external system is already in an ambiguous duplicate
    # state, so we fail closed instead of choosing one.
    if len(items) > 1:
        raise MondayAPIError(
            "Multiple Monday.com items were found for "
            "the same Harbor idempotency key."
        )

    item = items[0]

    if (
        not isinstance(item, dict)
        or not item.get("id")
    ):
        raise MondayAPIError(
            "Monday.com returned an invalid matching item."
        )

    return {
        "id": str(item["id"]),
        "name": item.get("name"),
    }


def create_support_ticket_item(
    *,
    title: str,
    description: str,
    severity: str,
    harbor_ticket_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    """
    Create one approved Harbor escalation on Monday.com.

    Authorization is intentionally not performed here.
    The ticket execution service must verify persisted human
    approval before this external adapter is called.

    Duplicate recovery is also intentionally handled by the
    orchestration service. This function performs only the
    actual create operation.
    """

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

    title = title.strip()
    description = description.strip()

    if not title:
        raise ValueError(
            "title cannot be empty."
        )

    if not description:
        raise ValueError(
            "description cannot be empty."
        )

    monday_severity = normalize_severity(
        severity
    )

    config = get_monday_configuration()

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
        ]: harbor_ticket_id,

        config[
            "status_column_id"
        ]: {
            "label": "Open"
        },

        config[
            "idempotency_key_column_id"
        ]: idempotency_key,

        config[
            "description_column_id"
        ]: description,

        config[
            "severity_column_id"
        ]: {
            "label": monday_severity
        },
    }

    variables = {
        "boardId": config["board_id"],
        "groupId": config["group_id"],
        "itemName": title,
        "columnValues": json.dumps(
            column_values
        ),
    }

    data = _execute_graphql(
        query=mutation,
        variables=variables,
        config=config,
    )

    item = data.get(
        "create_item"
    )

    if (
        not isinstance(item, dict)
        or not item.get("id")
    ):
        raise MondayAPIError(
            "Monday.com response did not contain "
            "a created item."
        )

    return {
        "id": str(item["id"]),
        "name": item.get(
            "name",
            title,
        ),
    }