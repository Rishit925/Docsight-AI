from app.ingestion.document_processor import DocumentProcessor
from app.chunking.chunker import DocumentChunker


def main():
    file_path = input(
        "Enter the path of your PDF: "
    ).strip()

    # --------------------------------
    # Process document
    # --------------------------------

    processor = DocumentProcessor()

    document_data = processor.process(
        file_path
    )

    # --------------------------------
    # Create chunks
    # --------------------------------

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=150,
    )

    chunks = chunker.create_chunks(
        document_data
    )

    # --------------------------------
    # Count chunks
    # --------------------------------

    text_chunks = 0
    table_chunks = 0
    image_chunks = 0

    for chunk in chunks:

        if chunk["content_type"] == "text":
            text_chunks += 1

        elif chunk["content_type"] == "table":
            table_chunks += 1

        elif chunk["content_type"] == "image":
            image_chunks += 1

    print("\n========== CHUNKING INFO ==========")

    print(
        f"Document: "
        f"{document_data['file_name']}"
    )

    print(
        f"Total pages: "
        f"{document_data['total_pages']}"
    )

    print(
        f"Total chunks: "
        f"{len(chunks)}"
    )

    print(
        f"Text chunks: "
        f"{text_chunks}"
    )

    print(
        f"Table chunks: "
        f"{table_chunks}"
    )

    print(
        f"Image chunks: "
        f"{image_chunks}"
    )

    # --------------------------------
    # Show image chunks
    # --------------------------------

    print("\n========== IMAGE CHUNKS ==========")

    for chunk in chunks:

        if chunk["content_type"] != "image":
            continue

        print(
            f"\nPage: "
            f"{chunk['page_number']}"
        )

        print(
            f"Image path: "
            f"{chunk['image_path']}"
        )

        print(
            "\nDescription:"
        )

        print(
            chunk["content"]
        )


if __name__ == "__main__":
    main()