from app.database.conversation_store import ConversationStore


class ConversationMemory:
    """
    Provides a memory layer on top of ConversationStore.

    ConversationStore:
        Persists conversation data.

    ConversationMemory:
        Retrieves and prepares relevant previous conversation
        so it can be used by the question-answering pipeline.
    """

    def __init__(
        self,
        conversation_store=None,
        max_messages=5,
    ):
        self.conversation_store = (
            conversation_store
            or ConversationStore()
        )

        self.max_messages = max(
            1,
            int(max_messages),
        )

    def get_history(
        self,
        document_id,
    ):
        """
        Retrieve recent conversation history
        for a document.
        """

        if not document_id or not document_id.strip():
            return []

        history = self.conversation_store.get_conversation(
            document_id.strip()
        )

        if not history:
            return []

        return history[-self.max_messages:]

    def build_context(
        self,
        document_id,
    ):
        """
        Convert recent conversation history into
        a compact text context for the LLM.
        """

        history = self.get_history(
            document_id
        )

        if not history:
            return ""

        context_parts = []

        for message in history:
            question = str(
                message.get(
                    "question",
                    "",
                )
            ).strip()

            answer = str(
                message.get(
                    "answer",
                    "",
                )
            ).strip()

            if not question:
                continue

            context_parts.append(
                f"User: {question}\n"
                f"Assistant: {answer}"
            )

        return "\n\n".join(
            context_parts
        )

    def get_last_message(
        self,
        document_id,
    ):
        """
        Return the most recent conversation message
        for a document.
        """

        history = self.get_history(
            document_id
        )

        if not history:
            return None

        return history[-1]