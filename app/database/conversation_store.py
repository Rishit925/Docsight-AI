import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


class ConversationStore:
    """
    Persistent storage for document conversations.

    Conversations are stored in the same SQLite database
    used by DocumentStore.
    """

    def __init__(
        self,
        database_path="data/docsight.db",
    ):
        self.database_path = database_path

        Path(
            database_path
        ).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._create_tables()

    # ==================================================
    # DATABASE CONNECTION
    # ==================================================

    def _get_connection(self):
        return sqlite3.connect(
            self.database_path
        )

    # ==================================================
    # CREATE TABLE
    # ==================================================

    def _create_tables(self):
        connection = self._get_connection()

        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    route TEXT,
                    content_types TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.commit()

        finally:
            connection.close()

    # ==================================================
    # ADD CONVERSATION
    # ==================================================

    def add_message(
        self,
        document_id,
        question,
        answer,
        route=None,
        content_types=None,
    ):
        """
        Store one question-answer interaction.
        """

        conversation_id = str(
            uuid.uuid4()
        )

        if content_types is None:
            content_types = []

        content_types_text = ",".join(
            str(item)
            for item in content_types
        )

        connection = self._get_connection()

        try:
            connection.execute(
                """
                INSERT INTO conversations (
                    conversation_id,
                    document_id,
                    question,
                    answer,
                    route,
                    content_types,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    document_id,
                    question,
                    answer,
                    route,
                    content_types_text,
                    datetime.now().isoformat(),
                ),
            )

            connection.commit()

        finally:
            connection.close()

        return conversation_id

    # ==================================================
    # GET CONVERSATION
    # ==================================================

    def get_conversation(
        self,
        document_id,
    ):
        """
        Return all previous messages for one document.
        """

        connection = self._get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT
                    conversation_id,
                    document_id,
                    question,
                    answer,
                    route,
                    content_types,
                    created_at
                FROM conversations
                WHERE document_id = ?
                ORDER BY created_at ASC
                """,
                (
                    document_id,
                ),
            )

            rows = cursor.fetchall()

            conversations = []

            for row in rows:

                content_types = []

                if row[5]:
                    content_types = [
                        item
                        for item in row[5].split(",")
                        if item
                    ]

                conversations.append(
                    {
                        "conversation_id": row[0],
                        "document_id": row[1],
                        "question": row[2],
                        "answer": row[3],
                        "route": row[4],
                        "content_types": content_types,
                        "created_at": row[6],
                    }
                )

            return conversations

        finally:
            connection.close()

    # ==================================================
    # DELETE CONVERSATION
    # ==================================================

    def delete_conversation(
        self,
        document_id,
    ):
        """
        Delete all conversation messages
        belonging to a document.
        """

        connection = self._get_connection()

        try:
            connection.execute(
                """
                DELETE FROM conversations
                WHERE document_id = ?
                """,
                (
                    document_id,
                ),
            )

            connection.commit()

        finally:
            connection.close()