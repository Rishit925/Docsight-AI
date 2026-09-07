from pathlib import Path

from app.ingestion.document_processor import (
    DocumentProcessor,
)

from app.chunking.chunker import DocumentChunker

from app.embeddings.embedding_service import (
    EmbeddingService,
)

from app.vectorstore.chroma_store import ChromaStore

from app.database.document_store import DocumentStore

from app.storage.supabase_storage import (
    SupabaseStorage,
)


class DocumentService:
    """
    Coordinates the complete document ingestion pipeline.

    Pipeline:

        PDF
          ↓
        DocumentProcessor
          ↓
        Supabase Storage for extracted images
          ↓
        Chunks
          ↓
        Embeddings
          ↓
        ChromaDB / Qdrant
          ↓
        PostgreSQL / SQLite document metadata
    """

    def __init__(
        self,
        processor=None,
        chunker=None,
        embedding_service=None,
        vector_store=None,
        document_store=None,
        storage=None,
    ):
        self.processor = (
            processor
            or DocumentProcessor()
        )

        self.chunker = (
            chunker
            or DocumentChunker()
        )

        self.embedding_service = (
            embedding_service
            or EmbeddingService()
        )

        self.vector_store = (
            vector_store
            or ChromaStore()
        )

        self.document_store = (
            document_store
            or DocumentStore()
        )

        self.storage = (
            storage
            or SupabaseStorage()
        )

    # ==================================================
    # PROCESS DOCUMENT
    # ==================================================

    def process_document(
        self,
        file_path: str,
        document_id: str,
        original_filename: str = None,
    ):
        """
        Process and index one document.

        Args:
            file_path:
                Internal temporary path to the uploaded PDF.

            document_id:
                Unique ID assigned by the API.

            original_filename:
                Original filename supplied by the user.
                Used for display and source information.
        """

        if not file_path:
            raise ValueError(
                "file_path cannot be empty."
            )

        if not document_id:
            raise ValueError(
                "document_id cannot be empty."
            )

        file_path = Path(
            file_path
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Document not found: {file_path}"
            )

        # --------------------------------------------------
        # Determine display filename
        # --------------------------------------------------

        if original_filename:
            display_filename = Path(
                original_filename
            ).name
        else:
            display_filename = file_path.name

        # --------------------------------------------------
        # 1. Process PDF
        # --------------------------------------------------

        processed_document = (
            self.processor.process(
                str(file_path)
            )
        )

        # --------------------------------------------------
        # 2. Attach document ID
        # --------------------------------------------------

        processed_document[
            "document_id"
        ] = document_id

        # --------------------------------------------------
        # 3. Preserve original filename
        #
        # DocumentProcessor sees the physical filename,
        # so explicitly replace it with the user-facing
        # filename.
        # --------------------------------------------------

        processed_document[
            "file_name"
        ] = display_filename

        # --------------------------------------------------
        # 4. Persist extracted images
        #
        # Images are processed locally first because
        # ImageProcessor/OpenAIProvider require filesystem
        # paths.
        #
        # After OpenAI analysis is complete, the images are
        # uploaded to Supabase Storage and the permanent
        # storage path replaces the temporary local path.
        # --------------------------------------------------

        self._persist_image_storage(
            processed_document=processed_document,
            document_id=document_id,
        )

        # --------------------------------------------------
        # 5. Create chunks
        # --------------------------------------------------

        chunks = self._create_chunks(
            processed_document,
            document_id,
        )

        # --------------------------------------------------
        # 6. Handle empty documents
        # --------------------------------------------------

        if not chunks:
            return {
                "document_id": document_id,
                "file_name": display_filename,
                "total_pages": processed_document.get(
                    "total_pages",
                    0,
                ),
                "total_chunks": 0,
                "text_chunks": 0,
                "table_chunks": 0,
                "image_chunks": 0,
            }

        # --------------------------------------------------
        # 7. Generate embeddings
        # --------------------------------------------------

        texts = []

        for chunk in chunks:

            content = chunk.get(
                "content",
                "",
            )

            if content is None:
                content = ""

            texts.append(
                str(content)
            )

        embeddings = (
            self._create_embeddings(
                texts
            )
        )

        # --------------------------------------------------
        # 8. Store in ChromaDB / Qdrant
        # --------------------------------------------------

        self.vector_store.add_chunks(
            chunks=chunks,
            embeddings=embeddings,
        )

        # --------------------------------------------------
        # 9. Statistics
        # --------------------------------------------------

        statistics = (
            self._build_statistics(
                chunks
            )
        )

        # --------------------------------------------------
        # 10. Store document metadata
        # --------------------------------------------------

        self.document_store.add_document(
            document_id=document_id,
            file_name=display_filename,
            total_pages=processed_document.get(
                "total_pages",
                0,
            ),
            total_chunks=len(chunks),
            text_chunks=statistics[
                "text_chunks"
            ],
            table_chunks=statistics[
                "table_chunks"
            ],
            image_chunks=statistics[
                "image_chunks"
            ],
        )

        # --------------------------------------------------
        # 11. Return API response
        # --------------------------------------------------

        return {
            "document_id": document_id,
            "file_name": display_filename,
            "total_pages": processed_document.get(
                "total_pages",
                0,
            ),
            "total_chunks": len(
                chunks
            ),
            "text_chunks": statistics[
                "text_chunks"
            ],
            "table_chunks": statistics[
                "table_chunks"
            ],
            "image_chunks": statistics[
                "image_chunks"
            ],
        }

    # ==================================================
    # PERSIST IMAGE STORAGE
    # ==================================================

    def _persist_image_storage(
        self,
        processed_document,
        document_id,
    ):
        """
        Upload extracted images to Supabase Storage.

        The local image path is retained temporarily
        for OpenAI processing, then replaced with the
        permanent Supabase Storage object path.

        This method does not change image descriptions.
        """

        pages = processed_document.get(
            "pages",
            [],
        )

        for page in pages:

            images = page.get(
                "images",
                [],
            )

            for image in images:

                local_path = image.get(
                    "path"
                )

                if not local_path:
                    continue

                local_path = Path(
                    local_path
                )

                if not local_path.exists():
                    raise FileNotFoundError(
                        f"Extracted image not found: "
                        f"{local_path}"
                    )

                storage_path = (
                    self._get_image_storage_path(
                        document_id=document_id,
                        image_path=local_path,
                    )
                )

                content_type = (
                    self._get_image_content_type(
                        local_path
                    )
                )

                self.storage.upload_file(
                    local_path=local_path,
                    storage_path=storage_path,
                    content_type=content_type,
                )

                # --------------------------------------------------
                # Replace temporary filesystem path with the
                # persistent Supabase Storage object path.
                # --------------------------------------------------

                image[
                    "storage_path"
                ] = storage_path

                image[
                    "path"
                ] = storage_path

    # ==================================================
    # IMAGE STORAGE PATH
    # ==================================================

    def _get_image_storage_path(
        self,
        document_id,
        image_path,
    ):
        """
        Create a stable Supabase Storage path for
        an extracted image.
        """

        return (
            f"{document_id}/"
            f"images/"
            f"{image_path.name}"
        )

    # ==================================================
    # IMAGE CONTENT TYPE
    # ==================================================

    def _get_image_content_type(
        self,
        image_path,
    ):
        """
        Determine the MIME type for an extracted image.
        """

        extension = (
            image_path.suffix.lower()
        )

        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
        }

        return content_types.get(
            extension,
            "application/octet-stream",
        )

    # ==================================================
    # CREATE CHUNKS
    # ==================================================

    def _create_chunks(
        self,
        processed_document,
        document_id,
    ):
        """
        Convert processed document data into
        searchable chunks.
        """

        chunks = self.chunker.create_chunks(
            processed_document
        )

        if chunks is None:
            return []

        normalized_chunks = []

        for index, chunk in enumerate(
            chunks
        ):

            if not isinstance(
                chunk,
                dict,
            ):
                continue

            chunk = dict(
                chunk
            )

            # ------------------------------------------
            # Ensure document ID
            # ------------------------------------------

            chunk[
                "document_id"
            ] = document_id

            # ------------------------------------------
            # Ensure chunk ID
            # ------------------------------------------

            if not chunk.get(
                "chunk_id"
            ):

                chunk[
                    "chunk_id"
                ] = (
                    f"{document_id}_"
                    f"chunk_{index}"
                )

            # ------------------------------------------
            # Ensure content
            # ------------------------------------------

            if (
                chunk.get(
                    "content"
                ) is None
            ):

                chunk[
                    "content"
                ] = ""

            # ------------------------------------------
            # Ensure content is vector-store safe
            # ------------------------------------------

            if not isinstance(
                chunk["content"],
                str,
            ):

                chunk[
                    "content"
                ] = str(
                    chunk["content"]
                )

            # ------------------------------------------
            # Ensure content type
            # ------------------------------------------

            if not chunk.get(
                "content_type"
            ):

                chunk[
                    "content_type"
                ] = "text"

            # ------------------------------------------
            # Ensure source
            # ------------------------------------------

            if not chunk.get(
                "source"
            ):

                chunk[
                    "source"
                ] = processed_document.get(
                    "file_name",
                    "Unknown",
                )

            # ------------------------------------------
            # Ensure page number
            # ------------------------------------------

            if not chunk.get(
                "page_number"
            ):

                chunk[
                    "page_number"
                ] = 1

            normalized_chunks.append(
                chunk
            )

        return normalized_chunks

    # ==================================================
    # CREATE EMBEDDINGS
    # ==================================================

    def _create_embeddings(
        self,
        texts,
    ):
        """
        Generate embeddings for all chunk contents.

        Prefer the batch embedding interface when
        available. Fall back to individual embedding
        calls when necessary.
        """

        if not texts:
            return []

        # --------------------------------------------------
        # Prefer batch embedding
        # --------------------------------------------------

        embed_documents = getattr(
            self.embedding_service,
            "embed_documents",
            None,
        )

        if callable(
            embed_documents
        ):

            return embed_documents(
                texts
            )

        # --------------------------------------------------
        # Fallback to individual embedding
        # --------------------------------------------------

        embed_text = getattr(
            self.embedding_service,
            "embed_text",
            None,
        )

        if not callable(
            embed_text
        ):

            raise AttributeError(
                "Embedding service must provide "
                "embed_documents() or embed_text()."
            )

        embeddings = []

        for text in texts:

            embeddings.append(
                embed_text(
                    text
                )
            )

        return embeddings

    # ==================================================
    # BUILD STATISTICS
    # ==================================================

    def _build_statistics(
        self,
        chunks,
    ):
        """
        Count chunks by content type.
        """

        statistics = {
            "text_chunks": 0,
            "table_chunks": 0,
            "image_chunks": 0,
        }

        for chunk in chunks:

            content_type = (
                chunk.get(
                    "content_type",
                    "text",
                )
            )

            if content_type == "text":

                statistics[
                    "text_chunks"
                ] += 1

            elif content_type == "table":

                statistics[
                    "table_chunks"
                ] += 1

            elif content_type == "image":

                statistics[
                    "image_chunks"
                ] += 1

        return statistics