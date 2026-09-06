import re
import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse

from app.api.schemas.document import (
    DocumentDeleteResponse,
    DocumentUploadResponse,
)
from app.api.services.document_service import (
    DocumentService,
)
from app.database.document_store import DocumentStore


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


document_service = DocumentService()
document_store = DocumentStore()


UPLOAD_DIRECTORY = Path(
    "data/uploads"
)

UPLOAD_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


def _safe_filename(filename: str) -> str:
    """
    Create a safe user-facing filename while preserving
    the original filename as much as possible.
    """

    filename = Path(filename).name

    filename = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        "_",
        filename,
    )

    filename = filename.strip()

    if not filename:
        filename = "document.pdf"

    return filename


def _get_unique_file_path(filename: str) -> Path:
    """
    Return a collision-safe physical file path.

    Examples:

        aiml.pdf
        aiml (1).pdf
        aiml (2).pdf
    """

    safe_filename = _safe_filename(
        filename
    )

    file_path = (
        UPLOAD_DIRECTORY
        / safe_filename
    )

    if not file_path.exists():
        return file_path

    stem = file_path.stem
    suffix = file_path.suffix

    counter = 1

    while True:

        candidate = (
            UPLOAD_DIRECTORY
            / f"{stem} ({counter}){suffix}"
        )

        if not candidate.exists():
            return candidate

        counter += 1


# ======================================================
# UPLOAD DOCUMENT
# ======================================================

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
)
def upload_document(
    file: UploadFile = File(...),
):
    """
    Upload and index a PDF document.

    The internal document_id remains a UUID.

    The physical file uses a human-readable,
    collision-safe filename.
    """

    # --------------------------------------------------
    # Validate filename
    # --------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    original_filename = Path(
        file.filename
    ).name

    # --------------------------------------------------
    # Validate extension
    # --------------------------------------------------

    extension = Path(
        original_filename
    ).suffix.lower()

    if extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    # --------------------------------------------------
    # Generate internal document ID
    # --------------------------------------------------

    document_id = str(
        uuid.uuid4()
    )

    # --------------------------------------------------
    # Create collision-safe physical path
    # --------------------------------------------------

    file_path = _get_unique_file_path(
        original_filename
    )

    # IMPORTANT:
    #
    # Use the actual stored filename as the document's
    # user-facing filename.
    #
    # This keeps:
    #
    #     SQLite
    #     ChromaDB
    #     Sources
    #     Physical PDF
    #
    # synchronized.
    #
    # Example:
    #
    #     aiml.pdf
    #     aiml (1).pdf
    #
    # If "aiml.pdf" already exists and the new upload
    # becomes "aiml (1).pdf", the database will also
    # contain "aiml (1).pdf".

    stored_filename = file_path.name

    # --------------------------------------------------
    # Save uploaded file
    # --------------------------------------------------

    try:

        with file_path.open(
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        # --------------------------------------------------
        # Process and index document
        # --------------------------------------------------

        result = (
            document_service.process_document(
                file_path=str(file_path),
                document_id=document_id,
                original_filename=stored_filename,
            )
        )

        return result

    except FileNotFoundError as error:

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except ValueError as error:

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Failed to process document.",
        ) from error

    finally:

        file.file.close()


# ======================================================
# DOCUMENT HISTORY
# ======================================================

@router.get("/history")
def get_document_history():
    """
    Return all indexed documents.

    The frontend uses this endpoint to display
    human-readable document names.
    """

    try:

        documents = (
            document_store.get_all_documents()
        )

        return documents

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail="Failed to load document history.",
        ) from error


# ======================================================
# OPEN / SERVE DOCUMENT PDF
# ======================================================

@router.get(
    "/{document_id}/file"
)
def get_document_file(
    document_id: str,
):
    """
    Serve the original uploaded PDF.

    The frontend can use this endpoint to open
    a source document in a PDF viewer.
    """

    if not document_id:
        raise HTTPException(
            status_code=400,
            detail="Document ID is required.",
        )

    try:

        document = (
            document_store.get_document(
                document_id
            )
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        file_name = document.get(
            "file_name"
        )

        if not file_name:
            raise HTTPException(
                status_code=404,
                detail="Document filename not found.",
            )

        file_path = (
            UPLOAD_DIRECTORY
            / Path(file_name).name
        )

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Document file is no longer available.",
            )

        if file_path.suffix.lower() != ".pdf":
            raise HTTPException(
                status_code=400,
                detail="Stored document is not a PDF.",
            )

        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=file_path.name,
            content_disposition_type="inline",
        )

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail="Failed to open document.",
        ) from error


# ======================================================
# DELETE DOCUMENT
# ======================================================

@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
)
def delete_document(
    document_id: str,
):
    """
    Delete a document from:

        1. ChromaDB
        2. SQLite
        3. uploads directory
    """

    if not document_id:
        raise HTTPException(
            status_code=400,
            detail="Document ID is required.",
        )

    try:

        document = (
            document_store.get_document(
                document_id
            )
        )

        if not document:

            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        # --------------------------------------------------
        # Remember physical filename before deleting
        # SQLite metadata.
        # --------------------------------------------------

        stored_filename = document.get(
            "file_name"
        )

        # --------------------------------------------------
        # Delete from ChromaDB
        # --------------------------------------------------

        document_service.vector_store.delete_document(
            document_id
        )

        # --------------------------------------------------
        # Delete from SQLite
        # --------------------------------------------------

        document_store.delete_document(
            document_id
        )

        # --------------------------------------------------
        # Delete physical PDF
        # --------------------------------------------------

        if stored_filename:

            file_path = (
                UPLOAD_DIRECTORY
                / Path(
                    stored_filename
                ).name
            )

            if file_path.exists():
                file_path.unlink()

        return {
            "success": True,
            "message": "Document deleted successfully.",
            "document_id": document_id,
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail="Failed to delete document.",
        ) from error