from fastapi import APIRouter, HTTPException

from app.database.conversation_store import ConversationStore


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


conversation_store = ConversationStore()


@router.get("/{document_id}")
def get_conversation(document_id: str):
    """
    Get saved conversation history for a document.
    """

    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=400,
            detail="document_id cannot be empty.",
        )

    try:
        conversations = conversation_store.get_conversation(
            document_id.strip()
        )

        return {
            "document_id": document_id.strip(),
            "conversations": conversations,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to load conversation history.",
        ) from error