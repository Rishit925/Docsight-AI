import os
import sqlite3
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()


class DocumentStore:
    """
    Persistent storage for document metadata.

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
            Path(database_path).parent.mkdir(
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
                    CREATE TABLE IF NOT EXISTS public.documents (
                        document_id TEXT PRIMARY KEY,
                        file_name TEXT NOT NULL,
                        upload_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        total_pages INTEGER NOT NULL DEFAULT 0,
                        total_chunks INTEGER NOT NULL DEFAULT 0,
                        text_chunks INTEGER NOT NULL DEFAULT 0,
                        table_chunks INTEGER NOT NULL DEFAULT 0,
                        image_chunks INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )

            else:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id TEXT PRIMARY KEY,
                        file_name TEXT NOT NULL,
                        upload_time TEXT NOT NULL,
                        total_pages INTEGER DEFAULT 0,
                        total_chunks INTEGER DEFAULT 0,
                        text_chunks INTEGER DEFAULT 0,
                        table_chunks INTEGER DEFAULT 0,
                        image_chunks INTEGER DEFAULT 0
                    )
                    """
                )

            connection.commit()

        finally:
            connection.close()

    # ==================================================
    # ADD DOCUMENT
    # ==================================================

    def add_document(
        self,
        document_id,
        file_name,
        total_pages,
        total_chunks,
        text_chunks,
        table_chunks,
        image_chunks,
    ):
        connection = self._get_connection()

        try:
            if self.db_backend == "postgres":
                connection.execute(
                    """
                    INSERT INTO public.documents (
                        document_id,
                        file_name,
                        upload_time,
                        total_pages,
                        total_chunks,
                        text_chunks,
                        table_chunks,
                        image_chunks
                    )
                    VALUES (
                        %s,
                        %s,
                        NOW(),
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (document_id)
                    DO UPDATE SET
                        file_name = EXCLUDED.file_name,
                        upload_time = EXCLUDED.upload_time,
                        total_pages = EXCLUDED.total_pages,
                        total_chunks = EXCLUDED.total_chunks,
                        text_chunks = EXCLUDED.text_chunks,
                        table_chunks = EXCLUDED.table_chunks,
                        image_chunks = EXCLUDED.image_chunks
                    """,
                    (
                        document_id,
                        file_name,
                        total_pages,
                        total_chunks,
                        text_chunks,
                        table_chunks,
                        image_chunks,
                    ),
                )

            else:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO documents (
                        document_id,
                        file_name,
                        upload_time,
                        total_pages,
                        total_chunks,
                        text_chunks,
                        table_chunks,
                        image_chunks
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        file_name,
                        datetime.now().isoformat(),
                        total_pages,
                        total_chunks,
                        text_chunks,
                        table_chunks,
                        image_chunks,
                    ),
                )

            connection.commit()

        finally:
            connection.close()

    # ==================================================
    # GET DOCUMENT
    # ==================================================

    def get_document(
        self,
        document_id,
    ):
        connection = self._get_connection()

        try:
            if self.db_backend == "postgres":
                cursor = connection.execute(
                    """
                    SELECT
                        document_id,
                        file_name,
                        upload_time,
                        total_pages,
                        total_chunks,
                        text_chunks,
                        table_chunks,
                        image_chunks
                    FROM public.documents
                    WHERE document_id = %s
                    """,
                    (
                        document_id,
                    ),
                )

            else:
                cursor = connection.execute(
                    """
                    SELECT
                        document_id,
                        file_name,
                        upload_time,
                        total_pages,
                        total_chunks,
                        text_chunks,
                        table_chunks,
                        image_chunks
                    FROM documents
                    WHERE document_id = ?
                    """,
                    (
                        document_id,
                    ),
                )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "document_id": row[0],
                "file_name": row[1],
                "upload_time": (
                    row[2].isoformat()
                    if hasattr(row[2], "isoformat")
                    else row[2]
                ),
                "total_pages": row[3],
                "total_chunks": row[4],
                "text_chunks": row[5],
                "table_chunks": row[6],
                "image_chunks": row[7],
            }

        finally:
            connection.close()

    # ==================================================
    # GET ALL DOCUMENTS
    # ==================================================

    def get_all_documents(self):
        connection = self._get_connection()

        try:
            if self.db_backend == "postgres":
                cursor = connection.execute(
                    """
                    SELECT
                        document_id,
                        file_name,
                        upload_time,
                        total_pages,
                        total_chunks,
                        text_chunks,
                        table_chunks,
                        image_chunks
                    FROM public.documents
                    ORDER BY upload_time DESC
                    """
                )

            else:
                cursor = connection.execute(
                    """
                    SELECT
                        document_id,
                        file_name,
                        upload_time,
                        total_pages,
                        total_chunks,
                        text_chunks,
                        table_chunks,
                        image_chunks
                    FROM documents
                    ORDER BY upload_time DESC
                    """
                )

            rows = cursor.fetchall()

            return [
                {
                    "document_id": row[0],
                    "file_name": row[1],
                    "upload_time": (
                        row[2].isoformat()
                        if hasattr(row[2], "isoformat")
                        else row[2]
                    ),
                    "total_pages": row[3],
                    "total_chunks": row[4],
                    "text_chunks": row[5],
                    "table_chunks": row[6],
                    "image_chunks": row[7],
                }
                for row in rows
            ]

        finally:
            connection.close()

    # ==================================================
    # DELETE DOCUMENT
    # ==================================================

    def delete_document(
        self,
        document_id,
    ):
        connection = self._get_connection()

        try:
            if self.db_backend == "postgres":
                connection.execute(
                    """
                    DELETE FROM public.documents
                    WHERE document_id = %s
                    """,
                    (
                        document_id,
                    ),
                )

            else:
                connection.execute(
                    """
                    DELETE FROM documents
                    WHERE document_id = ?
                    """,
                    (
                        document_id,
                    ),
                )

            connection.commit()

        finally:
            connection.close()