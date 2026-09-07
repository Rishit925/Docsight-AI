import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()


class ConversationStore:
    """
    Persistent storage for document conversations.

    Supports:
    - SQLite for local development
    - PostgreSQL (Supabase) for deployment

    Backend selection:
        DOCSIGHT_DB=sqlite
        DOCSIGHT_DB=postgres
    """

    def __init__(
        self,
        database_path="data/docsight.db",
    ):
        self.database_path = database_path

        self.db_backend = os.getenv(
            "DOCSIGHT_DB",
            "sqlite",
        ).strip().lower()

        if self.db_backend not in {
            "sqlite",
            "postgres",
        }:
            raise ValueError(
                "DOCSIGHT_DB must be either "
                "'sqlite' or 'postgres'."
            )

        if self.db_backend == "sqlite":
            Path(
                database_path
            ).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        else:
            self.database_url = os.getenv(
                "DATABASE_URL"
            )

            if not self.database_url:
                raise ValueError(
                    "DATABASE_URL is required when "
                    "DOCSIGHT_DB=postgres."
                )

        self._create_tables()

    # ==================================================
    # DATABASE CONNECTION
    # ==================================================

    def _get_connection(self):
        if self.db_backend == "postgres":
            return psycopg.connect(
                self.database_url
            )

        return sqlite3.connect(
            self.database_path
        )

    # ==================================================
    # CREATE TABLE
    # ==================================================

    def _create_tables(self):
        connection = self._get_connection()

        try:
            if self.db_backend == "postgres":
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.conversations (
                        conversation_id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        route TEXT,
                        content_types TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )

            else:
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
            if self.db_backend == "postgres":
                connection.execute(
                    """
                    INSERT INTO public.conversations (
                        conversation_id,
                        document_id,
                        question,
                        answer,
                        route,
                        content_types,
                        created_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        NOW()
                    )
                    """,
                    (
                        conversation_id,
                        document_id,
                        question,
                        answer,
                        route,
                        content_types_text,
                    ),
                )

            else:
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
            if self.db_backend == "postgres":
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
                    FROM public.conversations
                    WHERE document_id = %s
                    ORDER BY created_at ASC
                    """,
                    (
                        document_id,
                    ),
                )

            else:
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
                        "created_at": (
                            row[6].isoformat()
                            if hasattr(
                                row[6],
                                "isoformat",
                            )
                            else row[6]
                        ),
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
            if self.db_backend == "postgres":
                connection.execute(
                    """
                    DELETE FROM public.conversations
                    WHERE document_id = %s
                    """,
                    (
                        document_id,
                    ),
                )

            else:
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