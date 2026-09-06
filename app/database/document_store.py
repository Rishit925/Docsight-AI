import sqlite3
from datetime import datetime
from pathlib import Path


class DocumentStore:
    def __init__(self, database_path="data/docsight.db"):
        self.database_path = database_path

        Path(database_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._create_tables()

    def _get_connection(self):
        return sqlite3.connect(self.database_path)

    def _create_tables(self):
        connection = self._get_connection()

        try:
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

    def get_document(self, document_id):
        connection = self._get_connection()

        try:
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
                (document_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "document_id": row[0],
                "file_name": row[1],
                "upload_time": row[2],
                "total_pages": row[3],
                "total_chunks": row[4],
                "text_chunks": row[5],
                "table_chunks": row[6],
                "image_chunks": row[7],
            }

        finally:
            connection.close()

    def get_all_documents(self):
        connection = self._get_connection()

        try:
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
                    "upload_time": row[2],
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

    def delete_document(self, document_id):
        connection = self._get_connection()

        try:
            connection.execute(
                """
                DELETE FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            )

            connection.commit()

        finally:
            connection.close()