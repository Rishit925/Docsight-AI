from fastapi import (
    APIRouter,
    HTTPException,
)

from app.api.schemas.question import (
    QuestionRequest,
    QuestionResponse,
)

from app.api.services.container import (
    retriever,
)

from app.api.services.query_service import (
    QueryService,
)


router = APIRouter()


# ==================================================
# SHARED QUERY SERVICE
# ==================================================

query_service = QueryService(
    retriever=retriever,
)


# ==================================================
# ASK QUESTION
# ==================================================

@router.post(
    "/questions/ask",
    response_model=QuestionResponse,
    summary="Ask a question",
    description=(
        "Ask a question about an indexed document."
    ),
)
def ask_question(
    request: QuestionRequest,
) -> QuestionResponse:
    """
    Ask a question against an indexed document.
    """

    try:

        result = query_service.ask(
            question=request.question,
            document_id=request.document_id,
            top_k=request.top_k,
        )

        return QuestionResponse(
            question=result["question"],
            answer=result["answer"],
            route=result["route"],
            content_types=result["content_types"],
            sources=result["sources"],
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:

        print("\n" + "=" * 70)
        print("DOCSIGHT AI QUESTION ERROR")
        print("=" * 70)
        print(type(error).__name__)
        print(str(error))
        print("=" * 70 + "\n")

        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(error).__name__}: {str(error)}"
            ),
        ) from error