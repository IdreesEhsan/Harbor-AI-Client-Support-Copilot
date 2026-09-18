import shutil
import tempfile

from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from fastapi.concurrency import (
    run_in_threadpool,
)


# ============================================================
# AUTH
# ============================================================

from app.dependencies.auth import (
    require_roles,
)


# ============================================================
# ANALYTICS / FEEDBACK
# ============================================================

from app.rag.analytics import (
    get_rag_analytics_summary,
    list_knowledge_gaps,
    list_rag_feedback,
)


# ============================================================
# CONFLICT DETECTION
# ============================================================

from app.rag.conflict_detector import (
    list_policy_conflicts,
)


# ============================================================
# AUTOMATED EVALUATION
# ============================================================

from app.rag.evaluation import (
    create_evaluation_case,
    list_evaluation_cases,
    list_evaluation_runs,
    run_rag_evaluation,
)


# ============================================================
# KNOWLEDGE INGESTION
# ============================================================

from app.rag.indexer import (
    index_document,
)


# ============================================================
# KNOWLEDGE STORAGE
# ============================================================

from app.rag.vector_store import (
    activate_document,
    list_knowledge_documents,
)


# ============================================================
# SCHEMAS
# ============================================================

from app.schemas.rag import (
    RAGEvaluationCaseCreate,
    RAGEvaluationCaseRecord,
    RAGEvaluationRunResponse,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/knowledge",

    tags=[
        "Knowledge Management",
    ],
)


# ============================================================
# CONSTANTS
# ============================================================

ALLOWED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
}


ALLOWED_VISIBILITIES = {
    "public",
    "staff_only",
}


# ============================================================
# LIST KNOWLEDGE DOCUMENTS
# ============================================================

@router.get(
    "/documents",
)
def get_documents(
    active_only: bool = False,

    logical_key: str | None = None,

    visibility: str | None = None,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    List Harbor knowledge documents.

    Staff may optionally filter by:

    - active/inactive state
    - logical policy key
    - visibility
    """

    try:
        return (
            list_knowledge_documents(
                logical_key=(
                    logical_key
                ),

                active_only=(
                    active_only
                ),

                visibility=(
                    visibility
                ),

                limit=200,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# UPLOAD NEW KNOWLEDGE VERSION
# ============================================================

@router.post(
    "/documents",

    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def upload_document_version(
    file: UploadFile = File(...),

    logical_key: str = Form(...),

    title: str = Form(...),

    category: str = Form(
        "general"
    ),

    version: str = Form(...),

    visibility: str = Form(
        "public"
    ),

    effective_date: date | None = Form(
        None
    ),

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Upload and index a new Harbor knowledge-document version.

    Existing versions are preserved.

    The new version becomes active and the previous active
    version for the same logical key becomes inactive.
    """

    # --------------------------------------------------------
    # Filename validation
    # --------------------------------------------------------

    filename = (
        file.filename
        or ""
    ).strip()


    if not filename:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "Uploaded file must have "
                "a filename."
            ),
        )


    # --------------------------------------------------------
    # Extension validation
    # --------------------------------------------------------

    suffix = (
        Path(
            filename
        )
        .suffix
        .lower()
    )


    if (
        suffix
        not in ALLOWED_EXTENSIONS
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "Only TXT, PDF, and DOCX "
                "documents are supported."
            ),
        )


    # --------------------------------------------------------
    # Normalize metadata
    # --------------------------------------------------------

    logical_key = (
        logical_key
        .strip()
        .lower()
    )


    title = (
        title.strip()
    )


    category = (
        category
        .strip()
        .lower()
    )


    version = (
        version.strip()
    )


    visibility = (
        visibility
        .strip()
        .lower()
    )


    # --------------------------------------------------------
    # Required-field validation
    # --------------------------------------------------------

    if not logical_key:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "logical_key cannot be empty."
            ),
        )


    if not title:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "title cannot be empty."
            ),
        )


    if not version:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "version cannot be empty."
            ),
        )


    if (
        visibility
        not in ALLOWED_VISIBILITIES
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "visibility must be either "
                "'public' or 'staff_only'."
            ),
        )


    # --------------------------------------------------------
    # Temporary storage
    # --------------------------------------------------------

    temp_directory = (
        Path(
            tempfile.mkdtemp(
                prefix=(
                    "harbor-kb-"
                )
            )
        )
    )


    temp_file = (
        temp_directory
        / filename
    )


    try:

        # ----------------------------------------------------
        # Stream uploaded file to disk
        # ----------------------------------------------------

        with temp_file.open(
            "wb"
        ) as destination:

            while True:
                chunk = (
                    await file.read(
                        1024 * 1024
                    )
                )

                if not chunk:
                    break

                destination.write(
                    chunk
                )


        # ----------------------------------------------------
        # Index document in threadpool
        #
        # Loading, embeddings and Supabase operations are
        # blocking operations.
        # ----------------------------------------------------

        result = (
            await run_in_threadpool(
                index_document,

                temp_file,

                logical_key=(
                    logical_key
                ),

                title=(
                    title
                ),

                category=(
                    category
                ),

                version=(
                    version
                ),

                effective_date=(
                    effective_date
                ),

                uploaded_by=str(
                    current_user[
                        "id"
                    ]
                ),

                visibility=(
                    visibility
                ),
            )
        )


        return result


    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


    finally:

        await file.close()


        shutil.rmtree(
            temp_directory,

            ignore_errors=True,
        )


# ============================================================
# ACTIVATE PREVIOUS DOCUMENT VERSION
# ============================================================

@router.post(
    "/documents/{document_id}/activate",
)
def activate_document_version(
    document_id: UUID,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Roll Harbor back to a previous knowledge-document version.

    Activating one version automatically deactivates the other
    active version sharing the same logical key.
    """

    try:
        return (
            activate_document(
                str(
                    document_id
                )
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# RAG ANALYTICS SUMMARY
# ============================================================

@router.get(
    "/analytics",
)
def rag_analytics(
    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Return dashboard-ready RAG quality and feedback metrics.
    """

    return (
        get_rag_analytics_summary()
    )


# ============================================================
# KNOWLEDGE GAPS
# ============================================================

@router.get(
    "/knowledge-gaps",
)
def knowledge_gaps(
    limit: int = 100,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    List customer questions for which Harbor could not retrieve
    sufficient verified knowledge.
    """

    try:
        return (
            list_knowledge_gaps(
                limit=(
                    limit
                )
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# POLICY CONFLICTS
# ============================================================

@router.get(
    "/conflicts",
)
def policy_conflicts(
    limit: int = 100,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    List policy conflicts detected during live RAG retrieval.
    """

    try:
        return (
            list_policy_conflicts(
                limit=(
                    limit
                )
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# RAG FEEDBACK
# ============================================================

@router.get(
    "/feedback",
)
def rag_feedback(
    rating: str | None = None,

    limit: int = 100,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Review customer/staff feedback about Harbor RAG answers.

    Optional rating filter:

        positive
        negative
    """

    try:
        return (
            list_rag_feedback(
                rating=(
                    rating
                ),

                limit=(
                    limit
                ),
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# CREATE RAG EVALUATION CASE
# ============================================================

@router.post(
    "/evaluation/cases",

    response_model=(
        RAGEvaluationCaseRecord
    ),

    status_code=(
        status.HTTP_201_CREATED
    ),
)
def create_rag_evaluation_case(
    payload: RAGEvaluationCaseCreate,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Create one reusable automated RAG evaluation test case.

    Example:

        Question:
            What is the refund period?

        Expected answer:
            contains "14 days"

        Expected source:
            refund_policy_v2.txt

        Expected grounded:
            true
    """

    try:
        return (
            create_evaluation_case(
                payload
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# LIST RAG EVALUATION CASES
# ============================================================

@router.get(
    "/evaluation/cases",
)
def get_rag_evaluation_cases(
    active_only: bool = True,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    List automated RAG quality-test cases.
    """

    return (
        list_evaluation_cases(
            active_only=(
                active_only
            )
        )
    )


# ============================================================
# RUN AUTOMATED RAG EVALUATION
# ============================================================

@router.post(
    "/evaluation/run",

    response_model=(
        RAGEvaluationRunResponse
    ),
)
def execute_rag_evaluation(
    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Execute all currently-active RAG evaluation cases.

    Measures:

    - retrieval success
    - groundedness accuracy
    - expected-source accuracy
    - expected-answer accuracy
    - overall test pass rate
    """

    try:
        return (
            run_rag_evaluation(
                created_by=str(
                    current_user[
                        "id"
                    ]
                )
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# RAG EVALUATION HISTORY
# ============================================================

@router.get(
    "/evaluation/runs",
)
def get_rag_evaluation_runs(
    limit: int = 50,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    List previous automated RAG evaluation runs so Harbor's
    quality can be compared over time.
    """

    if limit <= 0:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "limit must be greater than zero."
            ),
        )


    return (
        list_evaluation_runs(
            limit=(
                limit
            )
        )
    )