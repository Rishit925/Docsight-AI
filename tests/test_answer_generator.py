from app.generation.answer_generator import (
    AnswerGenerator
)

from app.retrieval.query_router import (
    QueryRouter
)

from app.retrieval.retriever import (
    Retriever
)


def main():

    print(
        "\n========== DOCSIGHT RAG =========="
    )

    question = (
        "What are the differences between "
        "Traditional AI, Machine Learning, "
        "and Deep Learning?"
    )

    # ==============================================
    # ROUTE
    # ==============================================

    router = QueryRouter()

    route_info = router.route(
        question
    )

    print(
        f"\nQuestion: {question}"
    )

    print(
        f"Route: {route_info['route']}"
    )

    print(
        f"Content types: "
        f"{route_info['content_types']}"
    )

    # ==============================================
    # RETRIEVE
    # ==============================================

    retriever = Retriever()

    results = retriever.retrieve(
        query=question,
        top_k=5,
        route=route_info["route"],
    )

    print(
        "\n========== RETRIEVED CHUNKS =========="
    )

    for index, result in enumerate(
        results,
        start=1,
    ):

        metadata = result.get(
            "metadata",
            {},
        )

        print(
            f"\nResult {index}"
        )

        print(
            f"Type: "
            f"{result.get('content_type')}"
        )

        print(
            f"Page: "
            f"{metadata.get('page_number')}"
        )

        print(
            f"Rerank Score: "
            f"{result.get('rerank_score')}"
        )

    # ==============================================
    # GENERATE ANSWER
    # ==============================================

    print(
        "\n========== GENERATING ANSWER =========="
    )

    generator = AnswerGenerator()

    response = generator.generate_answer(
        question=question,
        results=results,
    )

    # ==============================================
    # FINAL ANSWER
    # ==============================================

    print(
        "\n========== FINAL ANSWER =========="
    )

    print(
        response["answer"]
    )

    # ==============================================
    # SOURCES
    # ==============================================

    print(
        "\n========== SOURCES =========="
    )

    for source in response["sources"]:

        print(
            f"Source: {source['source']} | "
            f"Page: {source['page_number']} | "
            f"Type: {source['content_type']}"
        )


if __name__ == "__main__":
    main()