from typing import List, Optional

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """
    Request body for asking a question.
    """

    question: str = Field(
        ...,
        min_length=1,
        description="Question to ask about the document.",
    )

    document_id: Optional[str] = Field(
        default=None,
        description="Optional document ID to restrict the search.",
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve.",
    )


class SourceResponse(BaseModel):
    """
    Source information associated with an answer.
    """

    source: str
    page_number: Optional[int] = None
    content_type: str
    document_id: Optional[str] = None
    file_name: Optional[str] = None


class QuestionResponse(BaseModel):
    """
    Structured response returned by the question API.
    """

    question: str
    answer: str
    route: str
    content_types: List[str]
    sources: List[SourceResponse]