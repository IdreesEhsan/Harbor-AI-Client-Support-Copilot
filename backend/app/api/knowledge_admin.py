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

from app.dependencies.auth import (
    require_roles,
)

from app.rag.analytics import (
    get_rag_analytics_summary,
    list_knowledge_gaps,
    list_rag_feedback,
)

from app.rag.conflict_detector import (
    list_policy_conflicts,
)

from app.rag.evaluation import (
    create_evaluation_case,
    list_evaluation_cases,
    list_evaluation_runs,
    run_rag_evaluation,
)

from app.rag.indexer import (
    index_document,
)

from app.rag.vector_store import (
    activate_document,
    deactivate_document,
    delete_document,
    list_knowledge_documents,
)

from app.schemas.rag import (
    RAGEvaluationCaseCreate,
    RAGEvaluationCaseRecord,
    RAGEvaluationRunResponse,
)


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
# LIST DOCUMENTS
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
# UPLOAD NEW DOCUMENT VERSION
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
# ACTIVATE DOCUMENT VERSION
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
# DEACTIVATE DOCUMENT VERSION
# ============================================================

@router.post(
    "/documents/{document_id}/deactivate",
)
def deactivate_document_version(
    document_id: UUID,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    try:
        return (
            deactivate_document(
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
# DELETE DOCUMENT VERSION
# ============================================================

@router.delete(
    "/documents/{document_id}",
)
def delete_knowledge_document(
    document_id: UUID,

    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Permanently remove one knowledge-document version and all
    of its indexed chunks.

    Deleting an active version intentionally does not activate
    an older version automatically.
    """

    try:
        return (
            delete_document(
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
# RAG ANALYTICS
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
    try:
        return (
            list_knowledge_gaps(
                limit=limit
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
    try:
        return (
            list_policy_conflicts(
                limit=limit
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
# CREATE EVALUATION CASE
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
# LIST EVALUATION CASES
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
    return (
        list_evaluation_cases(
            active_only=(
                active_only
            )
        )
    )


# ============================================================
# RUN RAG EVALUATION
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
# EVALUATION HISTORY
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
            limit=limit
        )
    )