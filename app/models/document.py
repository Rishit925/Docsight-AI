from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """
    Response returned after document processing.
    """

    document_id: str

    file_name: str

    total_pages: int


class DocumentListItem(BaseModel):
    """
    Basic document information used when listing documents.
    """

    document_id: str

    file_name: str

    total_pages: int