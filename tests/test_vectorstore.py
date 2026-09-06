from app.ingestion.document_processor import DocumentProcessor
from app.chunking.chunker import DocumentChunker
from app.embeddings.embedding_service import EmbeddingService
from app.vectorstore.chroma_store import ChromaStore


def main():

    # --------------------------------
    # Get PDF path
    # --------------------------------

    file_path = input(
        "Enter the path of your PDF: "
    ).strip()

    # --------------------------------
    # Process document
    # --------------------------------

    print("\n========== PROCESSING DOCUMENT ==========")

    processor = DocumentProcessor()

    document_data = processor.process(
        file_path
    )

    # --------------------------------
    # Create chunks
    # --------------------------------

    print("\n========== CREATING CHUNKS ==========")

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=150,
    )

    chunks = chunker.create_chunks(
        document_data
    )

    print(f"Total chunks created: {len(chunks)}")

    # --------------------------------
    # Select chunks that can be embedded
    # --------------------------------

    embeddable_chunks = []

    for chunk in chunks:

        if chunk["content"].strip():
            embeddable_chunks.append(chunk)

    print(
        f"Chunks to embed: "
        f"{len(embeddable_chunks)}"
    )

    # --------------------------------
    # Load embedding model
    # --------------------------------

    print("\n========== LOADING EMBEDDING MODEL ==========")

    embedding_service = EmbeddingService()

    print(
        f"Embedding dimension: "
        f"{embedding_service.get_dimension()}"
    )

    # --------------------------------
    # Create embeddings
    # --------------------------------

    print("\n========== CREATING EMBEDDINGS ==========")

    texts = [
        chunk["content"]
        for chunk in embeddable_chunks
    ]

    embeddings = embedding_service.embed_documents(
        texts
    )

    print(
        f"Created {len(embeddings)} embeddings."
    )

    # --------------------------------
    # Store in ChromaDB
    # --------------------------------

    print("\n========== STORING IN CHROMADB ==========")

    vector_store = ChromaStore()

    vector_store.add_chunks(
        embeddable_chunks,
        embeddings,
    )

    print(
        f"Chunks stored in ChromaDB: "
        f"{vector_store.count()}"
    )

    # --------------------------------
    # Test semantic search
    # --------------------------------

    print("\n========== SEMANTIC SEARCH ==========")

    query = input(
        "\nEnter a question to search the document: "
    ).strip()

    query_embedding = embedding_service.embed_text(
        query
    )

    results = vector_store.search(
        query_embedding,
        top_k=5,
    )

    print("\n========== SEARCH RESULTS ==========")

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for index in range(len(documents)):

        print(
            f"\n----- Result {index + 1} -----"
        )

        print(
            f"Source: "
            f"{metadatas[index]['source']}"
        )

        print(
            f"Page: "
            f"{metadatas[index]['page_number']}"
        )

        print(
            f"Type: "
            f"{metadatas[index]['content_type']}"
        )

        print(
            f"Distance: "
            f"{distances[index]:.4f}"
        )

        print("Content:")

        print(
            documents[index][:1000]
        )


if __name__ == "__main__":
    main()