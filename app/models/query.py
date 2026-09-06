from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """
    Request model for document questions.
    """

    question: str = Field(
        ...,
        min_length=1,
        description="Question to ask about the document.",
    )

    document_id: Optional[str] = Field(
        default=None,
        description="Optional document identifier.",
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve.",
    )


class SourceResponse(BaseModel):
    """
    Source information returned with an answer.
    """

    source: str

    page_number: int | str

    content_type: str

    image_path: Optional[str] = None


class QueryResponse(BaseModel):
    """
    Response returned by the Docsight question-answering API.
    """

    answer: str

    route: str

    sources: list[SourceResponse]