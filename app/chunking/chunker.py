from pathlib import Path
import hashlib

from app.ingestion.table_normalizer import TableNormalizer
from app.ingestion.table_validator import TableValidator

from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:
    """
    Converts extracted document data into RAG-ready chunks.

    Handles:
    - Text chunks
    - Valid table chunks
    - Image chunks

    Invalid table detections are ignored before they
    reach the embedding/vector-store stage.
    """

    def __init__(
        self,
        chunk_size=1000,
        chunk_overlap=150,
    ):

        self.text_splitter = (
            RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=[
                    "\n\n",
                    "\n",
                    ". ",
                    " ",
                    "",
                ],
            )
        )

        self.table_normalizer = TableNormalizer()
        self.table_validator = TableValidator()

    # ==================================================
    # CHUNK ID
    # ==================================================

    def _create_chunk_id(
        self,
        document_id,
        page_number,
        content_type,
        index,
    ):
        """
        Create a deterministic ID for a chunk.
        """

        raw_id = (
            f"{document_id}_"
            f"{page_number}_"
            f"{content_type}_"
            f"{index}"
        )

        return hashlib.md5(
            raw_id.encode()
        ).hexdigest()

    # ==================================================
    # TEXT CLEANING
    # ==================================================

    def _clean_text(self, text):
        """
        Clean unnecessary whitespace from extracted text.
        """

        if not text:
            return ""

        lines = []

        for line in text.splitlines():

            line = " ".join(
                line.split()
            )

            if line:
                lines.append(line)

        return "\n".join(lines)

    # ==================================================
    # TABLE VALIDATION
    # ==================================================

    def _is_valid_table(self, table):
        """
        Validate a detected table before creating a
        table chunk.

        The validator is deliberately kept separate from
        normalization so invalid PDF table detections
        never enter the RAG pipeline.
        """

        try:

            result = self.table_validator.validate(
                table
            )

            # ------------------------------------------
            # Validator returns a boolean
            # ------------------------------------------

            if isinstance(result, bool):
                return result

            # ------------------------------------------
            # Validator returns a dictionary
            # ------------------------------------------

            if isinstance(result, dict):

                if "valid" in result:
                    return bool(
                        result["valid"]
                    )

                if "is_valid" in result:
                    return bool(
                        result["is_valid"]
                    )

                if "status" in result:

                    return str(
                        result["status"]
                    ).upper() in {
                        "VALID",
                        "VALID TABLE",
                        "VALID_TABLE",
                    }

            # ------------------------------------------
            # Validator returns an object
            # ------------------------------------------

            if hasattr(
                result,
                "valid",
            ):
                return bool(
                    result.valid
                )

            if hasattr(
                result,
                "is_valid",
            ):
                return bool(
                    result.is_valid
                )

            if hasattr(
                result,
                "status",
            ):

                return str(
                    result.status
                ).upper() in {
                    "VALID",
                    "VALID TABLE",
                    "VALID_TABLE",
                }

        except Exception:
            return False

        return False

    # ==================================================
    # TABLE TO TEXT
    # ==================================================

    def _table_to_text(self, table):
        """
        Convert a validated table into normalized
        semantic text.
        """

        return self.table_normalizer.normalize(
            table
        )

    # ==================================================
    # CREATE CHUNKS
    # ==================================================

    def create_chunks(
        self,
        document_data,
    ):
        """
        Convert extracted document data into
        RAG-ready chunks.

        Returns:
            list of structured chunks.
        """

        document_id = Path(
            document_data["file_name"]
        ).stem

        source = document_data[
            "file_name"
        ]

        chunks = []

        # Counters are kept per page/content type.
        text_count = 0
        table_count = 0
        image_count = 0

        # ==================================================
        # PROCESS PAGES
        # ==================================================

        for page in document_data[
            "pages"
        ]:

            page_number = page[
                "page_number"
            ]

            # ==============================================
            # TEXT CHUNKS
            # ==============================================

            text = self._clean_text(
                page.get(
                    "text",
                    "",
                )
            )

            if text:

                text_parts = (
                    self.text_splitter.split_text(
                        text
                    )
                )

                for index, text_part in enumerate(
                    text_parts,
                    start=1,
                ):

                    text_count += 1

                    chunk_id = (
                        self._create_chunk_id(
                            document_id,
                            page_number,
                            "text",
                            index,
                        )
                    )

                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "page_number": page_number,
                            "content_type": "text",
                            "content": text_part,
                            "source": source,
                        }
                    )

            # ==============================================
            # TABLE CHUNKS
            # ==============================================

            for table_index, table in enumerate(
                page.get(
                    "tables",
                    [],
                ),
                start=1,
            ):

                # ------------------------------------------
                # IMPORTANT:
                # Validate table before normalization.
                # ------------------------------------------

                if not self._is_valid_table(
                    table
                ):
                    continue

                table_text = (
                    self._table_to_text(
                        table
                    )
                )

                if not table_text:
                    continue

                table_count += 1

                chunk_id = (
                    self._create_chunk_id(
                        document_id,
                        page_number,
                        "table",
                        table_index,
                    )
                )

                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "page_number": page_number,
                        "content_type": "table",
                        "content": table_text,
                        "source": source,
                    }
                )

            # ==============================================
            # IMAGE CHUNKS
            # ==============================================

            for image_index, image in enumerate(
                page.get(
                    "images",
                    [],
                ),
                start=1,
            ):

                image_description = image.get(
                    "description",
                    "",
                )

                # ------------------------------------------
                # Don't create useless empty image chunks.
                # ------------------------------------------

                if not image_description:
                    continue

                image_count += 1

                chunk_id = (
                    self._create_chunk_id(
                        document_id,
                        page_number,
                        "image",
                        image_index,
                    )
                )

                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "page_number": page_number,
                        "content_type": "image",
                        "content": image_description,
                        "image_path": image["path"],
                        "source": source,
                    }
                )

        # ==================================================
        # SUMMARY
        # ==================================================

        print(
            "\n========== CHUNK SUMMARY =========="
        )

        print(
            f"Text chunks: {text_count}"
        )

        print(
            f"Valid table chunks: {table_count}"
        )

        print(
            f"Image chunks: {image_count}"
        )

        print(
            f"Total chunks: {len(chunks)}"
        )

        return chunks