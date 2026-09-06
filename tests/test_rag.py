from app.generation.answer_generator import AnswerGenerator


def main():

    print("========== DOCSIGHT AI RAG ==========")

    question = input(
        "Ask a question about the document: "
    ).strip()

    generator = AnswerGenerator()

    print("\nRetrieving relevant information...")

    result = generator.answer(
        question=question,
        top_k=5,
    )

    print("\n========== ANSWER ==========")

    print(result["answer"])

    print("\n========== SOURCES ==========")

    for index, source in enumerate(
        result["sources"],
        start=1,
    ):
        metadata = source["metadata"]

        print(
            f"{index}. "
            f"{metadata['source']} "
            f"- Page {metadata['page_number']} "
            f"- {metadata['content_type']}"
        )


if __name__ == "__main__":
    main()