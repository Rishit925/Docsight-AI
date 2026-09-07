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


CHROMA_PATH = "vectorstore"
CHROMA_COLLECTION = "docsight_documents"
QDRANT_COLLECTION = "docsight_documents"

BATCH_SIZE = 50
EMBEDDING_DIMENSION = 384


def get_qdrant_client():
    """Create and validate the Qdrant client."""

    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if not url:
        raise ValueError(
            "QDRANT_URL is missing from .env"
        )

    if not api_key:
        raise ValueError(
            "QDRANT_API_KEY is missing from .env"
        )

    return QdrantClient(
        url=url,
        api_key=api_key,
    )


def ensure_collection(client):
    """Create the Qdrant collection if necessary."""

    collections = client.get_collections()

    collection_names = {
        collection.name
        for collection in collections.collections
    }

    if QDRANT_COLLECTION not in collection_names:
        print(
            f"Creating Qdrant collection: "
            f"{QDRANT_COLLECTION}"
        )

        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
    else:
        print(
            f"Qdrant collection already exists: "
            f"{QDRANT_COLLECTION}"
        )

    # Required for filtered searches.
    client.create_payload_index(
        collection_name=QDRANT_COLLECTION,
        field_name="document_id",
        field_schema="keyword",
    )

    client.create_payload_index(
        collection_name=QDRANT_COLLECTION,
        field_name="content_type",
        field_schema="keyword",
    )


def load_chroma_data():
    """Read the existing Chroma collection."""

    print("Loading existing Chroma collection...")

    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    collection = client.get_collection(
        name=CHROMA_COLLECTION
    )

    total = collection.count()

    print(
        f"Chroma vectors found: {total}"
    )

    if total == 0:
        raise RuntimeError(
            "Chroma collection is empty. "
            "Migration aborted."
        )

    data = collection.get(
        include=[
            "documents",
            "metadatas",
            "embeddings",
        ]
    )

    return data


def build_points(data):
    """Convert Chroma records into Qdrant points."""

    ids = data["ids"]
    documents = data["documents"]
    metadatas = data["metadatas"]
    embeddings = data["embeddings"]

    if not (
        len(ids)
        == len(documents)
        == len(metadatas)
        == len(embeddings)
    ):
        raise RuntimeError(
            "Chroma data lengths do not match."
        )

    points = []

    for index in range(len(ids)):
        chunk_id = str(
            ids[index]
        )

        metadata = (
            metadatas[index]
            or {}
        )

        document = documents[index]

        if document is None:
            document = ""

        document = str(document)

        payload = {
            "content": document,
            "document_id": str(
                metadata.get(
                    "document_id",
                    "",
                )
            ),
            "page_number": int(
                metadata.get(
                    "page_number",
                    0,
                )
            ),
            "content_type": str(
                metadata.get(
                    "content_type",
                    "text",
                )
            ),
            "source": str(
                metadata.get(
                    "source",
                    "",
                )
            ),
            "chunk_id": chunk_id,
        }

        if metadata.get("image_path"):
            payload["image_path"] = str(
                metadata["image_path"]
            )

        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"docsight:{chunk_id}",
            )
        )

        embedding = embeddings[index]

        if len(embedding) != EMBEDDING_DIMENSION:
            raise RuntimeError(
                f"Unexpected embedding dimension "
                f"for chunk {chunk_id}: "
                f"{len(embedding)}"
            )

        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
        )

    return points


def migrate(client, points):
    """Upload points to Qdrant in batches."""

    total = len(points)

    print(
        f"Migrating {total} vectors..."
    )

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):
        end = min(
            start + BATCH_SIZE,
            total,
        )

        batch = points[start:end]

        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=batch,
        )

        print(
            f"Migrated {end}/{total}"
        )


def verify(client, expected_count):
    """Verify the Qdrant vector count."""

    result = client.count(
        collection_name=QDRANT_COLLECTION,
        exact=True,
    )

    actual_count = result.count

    print(
        f"Qdrant vectors: {actual_count}"
    )

    if actual_count != expected_count:
        raise RuntimeError(
            "Migration verification failed: "
            f"expected {expected_count}, "
            f"found {actual_count}."
        )

    print(
        "Migration verification: SUCCESS"
    )


def main():
    print("=" * 60)
    print("Docsight AI — Chroma to Qdrant Migration")
    print("=" * 60)

    print()
    print(
        "Gemini/OpenAI will NOT be used."
    )
    print(
        "Existing Chroma embeddings will be "
        "copied directly."
    )
    print()

    qdrant_client = get_qdrant_client()

    print("Qdrant connection: SUCCESS")

    ensure_collection(
        qdrant_client
    )

    data = load_chroma_data()

    expected_count = len(
        data["ids"]
    )

    points = build_points(
        data
    )

    print(
        f"Prepared points: {len(points)}"
    )

    migrate(
        qdrant_client,
        points,
    )

    verify(
        qdrant_client,
        expected_count,
    )

    print()
    print("=" * 60)
    print("Migration completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()