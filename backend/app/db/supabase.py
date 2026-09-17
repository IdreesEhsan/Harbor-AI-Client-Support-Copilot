from supabase import (
    Client,
    create_client,
)

from app.core.config import (
    get_settings,
)


def get_supabase_client() -> Client:
    """
    Trusted Harbor server-side Supabase client.

    Uses the service role key for database and
    administrator operations.
    """

    settings = get_settings()

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def get_supabase_auth_client() -> Client:
    """
    Normal end-user Supabase Auth client.

    Used for customer/staff password authentication
    and customer registration.
    """

    settings = get_settings()

    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )