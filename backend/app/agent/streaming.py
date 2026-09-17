import threading
from collections.abc import Callable


# ============================================================
# THREAD-LOCAL STREAMING CONTEXT
# ============================================================

_stream_context = threading.local()


def set_stream_emitter(
    emitter: Callable[[str], None],
) -> None:
    """
    Register a token emitter for the current worker thread.

    Harbor's normal non-streaming requests do not install an
    emitter, so existing blocking behavior remains unchanged.
    """

    _stream_context.emitter = emitter


def clear_stream_emitter() -> None:
    """
    Remove the emitter from the current worker thread.
    """

    if hasattr(
        _stream_context,
        "emitter",
    ):
        delattr(
            _stream_context,
            "emitter",
        )


def has_stream_emitter() -> bool:
    """
    Return True when the current Harbor request is running
    through the streaming endpoint.
    """

    return callable(
        getattr(
            _stream_context,
            "emitter",
            None,
        )
    )


def emit_stream_token(
    token: str,
) -> None:
    """
    Send one generated model chunk to the active stream.

    If no stream is active, this function becomes a no-op.
    """

    if not token:
        return

    emitter = getattr(
        _stream_context,
        "emitter",
        None,
    )

    if callable(emitter):
        emitter(token)