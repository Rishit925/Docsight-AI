import re
import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
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
from app.storage.supabase_storage import (
    SupabaseStorage,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


document_service = DocumentService()
document_store = DocumentStore()
storage = SupabaseStorage()


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


def _get_unique_file_path(
    filename: str,
) -> Path:
    """
    Return a collision-safe temporary file path.

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


def _get_pdf_storage_path(
    document_id: str,
    stored_filename: str,
) -> str:
    """
    Return the persistent Supabase Storage path
    for an uploaded PDF.
    """

    return (
        f"{document_id}/"
        f"{stored_filename}"
    )


def _delete_cloud_document(
    document_id: str,
    stored_filename: str = None,
):
    """
    Delete the PDF and extracted images belonging
    to a document from Supabase Storage.
    """

    if stored_filename:

        pdf_storage_path = (
            _get_pdf_storage_path(
                document_id=document_id,
                stored_filename=stored_filename,
            )
        )

        try:

            storage.delete_file(
                pdf_storage_path
            )

        except Exception:
            pass

    try:

        storage.delete_folder(
            f"{document_id}/images"
        )

    except Exception:
        pass


def _cleanup_temporary_file(
    file_path: Path,
):
    """
    Delete a temporary local file after it is no
    longer needed.
    """

    if not file_path:
        return

    try:

        if file_path.exists():
            file_path.unlink()

    except OSError:
        pass


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

    The PDF and extracted images are persisted
    in Supabase Storage.

    The local filesystem is used only as temporary
    processing storage.
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
    # Create temporary local path
    # --------------------------------------------------

    file_path = _get_unique_file_path(
        original_filename
    )

    stored_filename = file_path.name

    # --------------------------------------------------
    # Persistent PDF storage path
    # --------------------------------------------------

    pdf_storage_path = (
        _get_pdf_storage_path(
            document_id=document_id,
            stored_filename=stored_filename,
        )
    )

    try:

        # --------------------------------------------------
        # Save uploaded PDF temporarily
        # --------------------------------------------------

        with file_path.open(
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        # --------------------------------------------------
        # Persist original PDF
        # --------------------------------------------------

        storage.upload_file(
            local_path=file_path,
            storage_path=pdf_storage_path,
            content_type="application/pdf",
        )

        # --------------------------------------------------
        # Process and index document
        #
        # DocumentService:
        #
        #   PDF
        #     ↓
        #   text/tables/images
        #     ↓
        #   OpenAI image analysis
        #     ↓
        #   Supabase image storage
        #     ↓
        #   chunks
        #     ↓
        #   embeddings
        #     ↓
        #   Qdrant
        #     ↓
        #   PostgreSQL
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

        try:

            document_service.vector_store.delete_document(
                document_id
            )

        except Exception:
            pass

        try:

            document_store.delete_document(
                document_id
            )

        except Exception:
            pass

        _delete_cloud_document(
            document_id=document_id,
            stored_filename=stored_filename,
        )

        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except ValueError as error:

        try:

            document_service.vector_store.delete_document(
                document_id
            )

        except Exception:
            pass

        try:

            document_store.delete_document(
                document_id
            )

        except Exception:
            pass

        _delete_cloud_document(
            document_id=document_id,
            stored_filename=stored_filename,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:

        import traceback

        traceback.print_exc()

        # --------------------------------------------------
        # Clean vector-store data if indexing succeeded
        # before a later operation failed.
        # --------------------------------------------------

        try:

            document_service.vector_store.delete_document(
                document_id
            )

        except Exception:
            pass

        # --------------------------------------------------
        # Clean database metadata if it was written.
        # --------------------------------------------------

        try:

            document_store.delete_document(
                document_id
            )

        except Exception:
            pass

        # --------------------------------------------------
        # Clean cloud files.
        # --------------------------------------------------

        _delete_cloud_document(
            document_id=document_id,
            stored_filename=stored_filename,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to process document.",
        ) from error

    finally:

        file.file.close()

        # --------------------------------------------------
        # The PDF is temporary.
        #
        # DocumentProcessor's extracted images are also
        # temporary; DocumentService has already uploaded
        # them to Supabase Storage.
        # --------------------------------------------------

        _cleanup_temporary_file(
            file_path
        )


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
    background_tasks: BackgroundTasks,
):
    """
    Serve the original uploaded PDF.

    The PDF is downloaded from private Supabase
    Storage to a temporary local file.

    FastAPI then serves that file to the frontend.

    The temporary file is deleted automatically
    after the response has finished.
    """

    if not document_id:

        raise HTTPException(
            status_code=400,
            detail="Document ID is required.",
        )

    document = None
    temporary_file_path = None

    try:

        # --------------------------------------------------
        # Load document metadata
        # --------------------------------------------------

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

        file_name = Path(
            file_name
        ).name

        # --------------------------------------------------
        # Validate PDF
        # --------------------------------------------------

        if Path(
            file_name
        ).suffix.lower() != ".pdf":

            raise HTTPException(
                status_code=400,
                detail="Stored document is not a PDF.",
            )

        # --------------------------------------------------
        # Build Supabase Storage path
        # --------------------------------------------------

        storage_path = (
            _get_pdf_storage_path(
                document_id=document_id,
                stored_filename=file_name,
            )
        )

        # --------------------------------------------------
        # Temporary source directory
        # --------------------------------------------------

        temporary_directory = (
            UPLOAD_DIRECTORY
            / "temp_sources"
        )

        temporary_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_file_path = (
            temporary_directory
            / f"{document_id}.pdf"
        )

        # --------------------------------------------------
        # Download PDF from Supabase Storage
        # --------------------------------------------------

        storage.download_file(
            storage_path=storage_path,
            local_path=temporary_file_path,
        )

        # --------------------------------------------------
        # Delete temporary file after response
        # --------------------------------------------------

        background_tasks.add_task(
            _cleanup_temporary_file,
            temporary_file_path,
        )

        # --------------------------------------------------
        # Return PDF.
        #
        # The background task runs only after FastAPI
        # finishes sending the response.
        # --------------------------------------------------

        return FileResponse(
            path=temporary_file_path,
            media_type="application/pdf",
            filename=file_name,
            content_disposition_type="inline",
        )

    except HTTPException:
        if temporary_file_path:
            _cleanup_temporary_file(
                temporary_file_path
            )

        raise

    except FileNotFoundError as error:

        if temporary_file_path:
            _cleanup_temporary_file(
                temporary_file_path
            )

        raise HTTPException(
            status_code=404,
            detail="Document file is no longer available.",
        ) from error

    except Exception as error:

        if temporary_file_path:
            _cleanup_temporary_file(
                temporary_file_path
            )

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

        1. Qdrant / ChromaDB
        2. PostgreSQL / SQLite
        3. Supabase Storage
        4. temporary local files
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

        stored_filename = document.get(
            "file_name"
        )

        # --------------------------------------------------
        # Delete from vector database
        # --------------------------------------------------

        document_service.vector_store.delete_document(
            document_id
        )

        # --------------------------------------------------
        # Delete from PostgreSQL / SQLite
        # --------------------------------------------------

        document_store.delete_document(
            document_id
        )

        # --------------------------------------------------
        # Delete from Supabase Storage
        # --------------------------------------------------

        _delete_cloud_document(
            document_id=document_id,
            stored_filename=stored_filename,
        )

        # --------------------------------------------------
        # Delete temporary source file if present
        # --------------------------------------------------

        temporary_source = (
            UPLOAD_DIRECTORY
            / "temp_sources"
            / f"{document_id}.pdf"
        )

        _cleanup_temporary_file(
            temporary_source
        )

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