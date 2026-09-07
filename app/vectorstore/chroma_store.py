import os
import uuid

import chromadb
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

load_dotenv()


class ChromaStore:
    """
    Vector-store interface used by Docsight AI.

    Supports two backends:

        DOCSIGHT_VECTOR_DB=chroma
            Local persistent ChromaDB.

        DOCSIGHT_VECTOR_DB=qdrant
            Qdrant Cloud.

    The public interface intentionally remains compatible with the
    existing Retriever and DocumentService.
    """

    def __init__(
        self,
        persist_directory="vectorstore",
        collection_name="docsight_documents",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        self.backend = os.getenv(
            "DOCSIGHT_VECTOR_DB",
            "chroma",
        ).lower().strip()

        if self.backend not in {"chroma", "qdrant"}:
            raise ValueError(
                "DOCSIGHT_VECTOR_DB must be either "
                "'chroma' or 'qdrant'."
            )

        if self.backend == "qdrant":
            self._initialize_qdrant()
        else:
            self._initialize_chroma()

    # ==================================================
    # INITIALIZATION
    # ==================================================

    def _initialize_chroma(self):
        """Initialize the existing local ChromaDB backend."""

        self.client = chromadb.PersistentClient(
            path=self.persist_directory
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=self.collection_name
            )
        )

    def _initialize_qdrant(self):
        """Initialize Qdrant Cloud."""

        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")

        if not url:
            raise ValueError(
                "QDRANT_URL is required when "
                "DOCSIGHT_VECTOR_DB=qdrant."
            )

        if not api_key:
            raise ValueError(
                "QDRANT_API_KEY is required when "
                "DOCSIGHT_VECTOR_DB=qdrant."
            )

        self.client = QdrantClient(
            url=url,
            api_key=api_key,
        )

        self._ensure_qdrant_collection()

    def _ensure_qdrant_collection(self):
        """
        Create the Qdrant collection and required payload indexes.
        """

        collections = self.client.get_collections()

        collection_names = {
            collection.name
            for collection in collections.collections
        }

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE,
                ),
            )
        

        # --------------------------------------------------
        # Payload indexes required for filtered searches
        # --------------------------------------------------

        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema="keyword",
            )
        except Exception:
            pass

        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="content_type",
                field_schema="keyword",
            )
        except Exception:
            pass

    # ==================================================
    # ADD CHUNKS
    # ==================================================

    def add_chunks(
        self,
        chunks,
        embeddings,
    ):
        """
        Store document chunks and their embeddings.

        Keeps the original Chroma-compatible interface.
        """

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Number of chunks must match "
                "number of embeddings."
            )

        if not chunks:
            return

        if self.backend == "qdrant":
            self._add_chunks_qdrant(
                chunks,
                embeddings,
            )
            return

        self._add_chunks_chroma(
            chunks,
            embeddings,
        )

    def _add_chunks_chroma(
        self,
        chunks,
        embeddings,
    ):
        """Store chunks in local ChromaDB."""

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id = str(
                chunk.get(
                    "chunk_id",
                    "",
                )
            )

            if not chunk_id:
                raise ValueError(
                    "Each chunk must contain a chunk_id."
                )

            ids.append(chunk_id)

            content = chunk.get(
                "content",
                "",
            )

            if isinstance(content, dict):
                content = content.get(
                    "description",
                    str(content),
                )
            elif content is None:
                content = ""
            else:
                content = str(content)

            documents.append(content)

            metadata = {
                "document_id": str(
                    chunk["document_id"]
                ),
                "page_number": int(
                    chunk["page_number"]
                ),
                "content_type": str(
                    chunk["content_type"]
                ),
                "source": str(
                    chunk["source"]
                ),
            }

            if chunk.get("image_path"):
                metadata["image_path"] = str(
                    chunk["image_path"]
                )

            metadatas.append(metadata)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def _add_chunks_qdrant(
        self,
        chunks,
        embeddings,
    ):
        """Store chunks in Qdrant Cloud."""

        points = []

        for chunk, embedding in zip(
            chunks,
            embeddings,
        ):
            chunk_id = str(
                chunk.get(
                    "chunk_id",
                    "",
                )
            )

            if not chunk_id:
                raise ValueError(
                    "Each chunk must contain a chunk_id."
                )

            content = chunk.get(
                "content",
                "",
            )

            if isinstance(content, dict):
                content = content.get(
                    "description",
                    str(content),
                )
            elif content is None:
                content = ""
            else:
                content = str(content)

            payload = {
                "content": content,
                "document_id": str(
                    chunk["document_id"]
                ),
                "page_number": int(
                    chunk["page_number"]
                ),
                "content_type": str(
                    chunk["content_type"]
                ),
                "source": str(
                    chunk["source"]
                ),
                "chunk_id": chunk_id,
            }

            if chunk.get("image_path"):
                payload["image_path"] = str(
                    chunk["image_path"]
                )

            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"docsight:{chunk_id}",
                    )
                )

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    # ==================================================
    # SEARCH
    # ==================================================

    def search(
        self,
        query_embedding,
        top_k=5,
        content_types=None,
        document_id=None,
    ):
        """
        Search the vector store.

        Returns the same result structure expected by
        the existing Retriever:

            documents
            metadatas
            distances
        """

        if self.backend == "qdrant":
            return self._search_qdrant(
                query_embedding=query_embedding,
                top_k=top_k,
                content_types=content_types,
                document_id=document_id,
            )

        return self._search_chroma(
            query_embedding=query_embedding,
            top_k=top_k,
            content_types=content_types,
            document_id=document_id,
        )

    def _search_chroma(
        self,
        query_embedding,
        top_k=5,
        content_types=None,
        document_id=None,
    ):
        """Search local ChromaDB."""

        where = self._build_filter(
            content_types=content_types,
            document_id=document_id,
        )

        query_kwargs = {
            "query_embeddings": [
                query_embedding
            ],
            "n_results": top_k,
        }

        if where:
            query_kwargs["where"] = where

        return self.collection.query(
            **query_kwargs
        )

    def _search_qdrant(
        self,
        query_embedding,
        top_k=5,
        content_types=None,
        document_id=None,
    ):
        """Search Qdrant and return Chroma-compatible results."""

        query_filter = self._build_qdrant_filter(
            content_types=content_types,
            document_id=document_id,
        )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        ).points

        documents = []
        metadatas = []
        distances = []
        ids = []

        for result in results:
            payload = result.payload or {}

            content = payload.get(
                "content",
                "",
            )

            metadata = {
                "document_id": str(
                    payload.get(
                        "document_id",
                        "",
                    )
                ),
                "page_number": int(
                    payload.get(
                        "page_number",
                        0,
                    )
                ),
                "content_type": str(
                    payload.get(
                        "content_type",
                        "text",
                    )
                ),
                "source": str(
                    payload.get(
                        "source",
                        "",
                    )
                ),
                "chunk_id": str(
                    payload.get(
                        "chunk_id",
                        result.id,
                    )
                ),
            }

            if payload.get("image_path"):
                metadata["image_path"] = str(
                    payload["image_path"]
                )

            documents.append(
                str(content)
            )

            metadatas.append(metadata)

            # Qdrant cosine score:
            # higher = more similar.
            #
            # Existing Retriever expects a distance:
            # lower = more similar.
            #
            # Convert similarity into cosine distance.
            score = float(
                result.score
            )

            distances.append(
                1.0 - score
            )

            ids.append(
                str(result.id)
            )

        return {
            "ids": [ids],
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [distances],
        }

    # ==================================================
    # FILTERS
    # ==================================================

    def _build_filter(
        self,
        content_types=None,
        document_id=None,
    ):
        """
        Build the original Chroma filter.
        """

        conditions = []

        if document_id:
            conditions.append(
                {
                    "document_id": {
                        "$eq": str(
                            document_id
                        )
                    }
                }
            )

        if content_types:
            if len(content_types) == 1:
                conditions.append(
                    {
                        "content_type": {
                            "$eq": str(
                                content_types[0]
                            )
                        }
                    }
                )
            else:
                conditions.append(
                    {
                        "$or": [
                            {
                                "content_type": {
                                    "$eq": str(
                                        content_type
                                    )
                                }
                            }
                            for content_type
                            in content_types
                        ]
                    }
                )

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {
            "$and": conditions
        }

    def _build_qdrant_filter(
        self,
        content_types=None,
        document_id=None,
    ):
        """Build the equivalent Qdrant filter."""

        must_conditions = []

        if document_id:
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(
                        value=str(
                            document_id
                        )
                    ),
                )
            )

        if content_types:
            content_type_conditions = [
                FieldCondition(
                    key="content_type",
                    match=MatchValue(
                        value=str(
                            content_type
                        )
                    ),
                )
                for content_type
                in content_types
            ]

            if len(content_type_conditions) == 1:
                must_conditions.append(
                    content_type_conditions[0]
                )
            else:
                must_conditions.append(
                    Filter(
                        should=content_type_conditions
                    )
                )

        if not must_conditions:
            return None

        return Filter(
            must=must_conditions
        )

    # ==================================================
    # COUNT
    # ==================================================

    def count(
        self,
        document_id=None,
    ):
        """Return the number of stored vectors."""

        if self.backend == "qdrant":
            return self._count_qdrant(
                document_id
            )

        if document_id:
            result = self.collection.get(
                where={
                    "document_id": {
                        "$eq": str(
                            document_id
                        )
                    }
                },
                include=[],
            )

            return len(
                result.get("ids", [])
            )

        return self.collection.count()

    def _count_qdrant(
        self,
        document_id=None,
    ):
        """Count Qdrant vectors."""

        if document_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(
                            value=str(
                                document_id
                            )
                        ),
                    )
                ]
            )

            result = self.client.count(
                collection_name=self.collection_name,
                count_filter=query_filter,
                exact=True,
            )

            return result.count

        result = self.client.count(
            collection_name=self.collection_name,
            exact=True,
        )

        return result.count

    # ==================================================
    # DELETE DOCUMENT
    # ==================================================

    def delete_document(
        self,
        document_id,
    ):
        """Delete all vectors belonging to a document."""

        if self.backend == "qdrant":
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(
                            value=str(
                                document_id
                            )
                        ),
                    )
                ]
            )

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=query_filter,
            )

            return

        self.collection.delete(
            where={
                "document_id": {
                    "$eq": str(
                        document_id
                    )
                }
            }
        )

    # ==================================================
    # RESET
    # ==================================================

    def reset(self):
        """Delete and recreate the complete vector collection."""

        if self.backend == "qdrant":
            self.client.delete_collection(
                collection_name=self.collection_name
            )

            self._ensure_qdrant_collection()

            return

        self.client.delete_collection(
            name=self.collection_name
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=self.collection_name
            )
        )