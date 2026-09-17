from functools import lru_cache

from supabase import (
    Client,
    create_client,
)

from app.core.config import (
    get_settings,
)


# ============================================================
# TRUSTED SERVER DATABASE CLIENT
# ============================================================

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Return Harbor's shared trusted server-side Supabase
    database client.

    Important:

    This client uses the service-role key and is intended for
    backend database/admin operations only.

    The client is cached so Harbor can reuse the underlying
    HTTP connection pool instead of constructing a brand-new
    Supabase/httpx client for every repository call.

    This significantly reduces:

    - repeated TCP connections
    - repeated TLS handshakes
    - repeated client construction
    - unnecessary network overhead
    """

    settings = (
        get_settings()
    )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


# ============================================================
# END-USER AUTH CLIENT
# ============================================================

def get_supabase_auth_client() -> Client:
    """
    Return a fresh Supabase Auth client.

    Unlike the trusted database client above, this client is
    intentionally NOT cached.

    Supabase Auth clients can maintain authentication/session
    state internally. Sharing one mutable Auth client between
    different Harbor customers could cause session leakage or
    cross-user state.

    Therefore:

        database client -> shared
        auth client     -> fresh per auth operation
    """

    settings = (
        get_settings()
    )

    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )