from typing import Optional

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    """
    Response returned after a document is processed
    and indexed.
    """

    document_id: str
    file_name: str
    total_pages: int
    total_chunks: int
    text_chunks: int
    table_chunks: int
    image_chunks: int


class DocumentDeleteResponse(BaseModel):
    """
    Response returned after deleting a document.
    """

    document_id: str
    message: str