import threading
from collections.abc import Callable


# ============================================================
# THREAD-LOCAL STREAMING CONTEXT
# ============================================================

_stream_context = threading.local()


# ============================================================
# STREAM SETUP
# ============================================================

def set_stream_emitter(
    emitter: Callable[[str], None],
) -> None:
    """
    Register the final SSE emitter for the current worker
    thread.

    Important security behavior:

    Model-generated chunks are NOT sent directly to this
    emitter.

    They are temporarily buffered until Harbor's complete
    output has passed the output guardrail.

    Flow:

        Groq chunk
            ↓
        emit_stream_token()
            ↓
        private request buffer
            ↓
        complete answer
            ↓
        output guardrail
            ↓
        emit_validated_stream_text()
            ↓
        SSE emitter
            ↓
        browser

    Non-streaming requests do not install an emitter, so
    Harbor's existing /agent/chat behavior remains unchanged.
    """

    _stream_context.emitter = emitter

    # Raw model output is request-local and temporary.
    #
    # It is deliberately never exposed to the client directly.
    _stream_context.generated_parts = []


# ============================================================
# STREAM CLEANUP
# ============================================================

def clear_stream_emitter() -> None:
    """
    Remove all request-local streaming state.

    Both the emitter and any temporary unvalidated model
    fragments are removed.
    """

    if hasattr(
        _stream_context,
        "emitter",
    ):
        delattr(
            _stream_context,
            "emitter",
        )


    if hasattr(
        _stream_context,
        "generated_parts",
    ):
        delattr(
            _stream_context,
            "generated_parts",
        )


# ============================================================
# STREAM STATUS
# ============================================================

def has_stream_emitter() -> bool:
    """
    Return True when the current Harbor request is running
    through /agent/chat/stream.

    RAG and conversation-memory generators use this to enable
    Groq's stream=True mode.

    Important:

    stream=True means Harbor receives incremental model
    chunks internally.

    Those chunks are still withheld from the customer until
    the complete response has passed Harbor's output
    guardrail.
    """

    return callable(
        getattr(
            _stream_context,
            "emitter",
            None,
        )
    )


# ============================================================
# RAW MODEL CHUNK COLLECTION
# ============================================================

def emit_stream_token(
    token: str,
) -> None:
    """
    Receive one raw generated model chunk.

    SECURITY BOUNDARY:

    This function intentionally DOES NOT send the chunk to
    the browser.

    The raw chunk is kept only in the current worker thread's
    temporary streaming buffer.

    This prevents partial model output from bypassing Harbor's
    full-response output guardrail.

    Existing model-generation code may continue calling:

        emit_stream_token(delta)

    without needing any changes.
    """

    if not token:
        return


    emitter = getattr(
        _stream_context,
        "emitter",
        None,
    )


    # Normal /agent/chat requests do not have an emitter.
    if not callable(
        emitter
    ):
        return


    generated_parts = getattr(
        _stream_context,
        "generated_parts",
        None,
    )


    if generated_parts is None:
        generated_parts = []

        _stream_context.generated_parts = (
            generated_parts
        )


    generated_parts.append(
        token
    )


# ============================================================
# OPTIONAL RAW BUFFER ACCESS
# ============================================================

def get_buffered_stream_text() -> str:
    """
    Return the raw internally-generated stream text.

    This helper is primarily useful for diagnostics and tests.

    The returned value must NEVER be sent directly to the
    customer without passing Harbor's output guardrail.
    """

    generated_parts = getattr(
        _stream_context,
        "generated_parts",
        [],
    )


    return "".join(
        generated_parts
    )


# ============================================================
# SAFE CUSTOMER STREAM
# ============================================================

def emit_validated_stream_text(
    text: str,
    *,
    chunk_size: int = 48,
) -> None:
    """
    Stream FINAL VALIDATED text to the browser.

    This function must only be called after Harbor has decided
    exactly what customer-visible answer is safe to return.

    Examples include:

    - normal output that passed evaluate_output();
    - redacted output returned by evaluate_output();
    - Harbor's safe fallback response;
    - deterministic ticket-confirmation responses.

    The text is divided into small chunks so the frontend can
    preserve Harbor's progressive-response experience.

    No artificial delay is introduced.
    """

    if not isinstance(
        text,
        str,
    ):
        raise TypeError(
            "Validated stream text must be a string."
        )


    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than zero."
        )


    if not text:
        return


    emitter = getattr(
        _stream_context,
        "emitter",
        None,
    )


    # Normal non-streaming endpoint.
    if not callable(
        emitter
    ):
        return


    # Raw model fragments are no longer needed once Harbor
    # has selected the final safe answer.
    if hasattr(
        _stream_context,
        "generated_parts",
    ):
        _stream_context.generated_parts.clear()


    # Stream the already-validated answer progressively.
    for start in range(
        0,
        len(text),
        chunk_size,
    ):
        emitter(
            text[
                start:
                start + chunk_size
            ]
        )