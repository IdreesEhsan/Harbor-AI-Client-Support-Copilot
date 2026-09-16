from app.integrations.monday import (
    MondayAPIError,
    MondayConfigurationError,
    create_support_ticket_item,
)


def main():
    """
    Perform one controlled live Monday.com integration test.

    This script intentionally bypasses Harbor's ticket
    execution workflow and should only be used manually
    during integration setup.
    """

    try:
        result = create_support_ticket_item(
            title="Harbor Integration Test",
            description=(
                "Controlled test item created while "
                "validating Harbor's Monday.com integration."
            ),
            severity="medium",
            harbor_ticket_id="HARBOR-LIVE-TEST",
            idempotency_key=(
                "harbor-monday-live-test"
            ),
        )

    except MondayConfigurationError as exc:
        print(
            f"Configuration error: {exc}"
        )
        return

    except MondayAPIError as exc:
        print(
            f"Monday API error: {exc}"
        )
        return

    print(
        "Monday.com item created successfully."
    )
    print(
        f"Item ID: {result['id']}"
    )
    print(
        f"Item name: {result['name']}"
    )


if __name__ == "__main__":
    main()