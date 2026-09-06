from app.retrieval.query_router import QueryRouter
from app.retrieval.retriever import Retriever


def main():

    router = QueryRouter()
    retriever = Retriever()

    print(
        "\n========== DOCSIGHT ROUTED RETRIEVAL =========="
    )

    questions = [
        "What is artificial intelligence?",
        "What does the table compare?",
        "What does the diagram show?",
        "Compare the table and diagram.",
    ]

    for question in questions:

        print("\n" + "=" * 60)

        print(
            f"Question: {question}"
        )

        # --------------------------------------------
        # Route query
        # --------------------------------------------

        route_info = router.route(
            question
        )

        print(
            f"Route: {route_info['route']}"
        )

        print(
            f"Content types: "
            f"{route_info['content_types']}"
        )

        # --------------------------------------------
        # Retrieve and rerank
        # --------------------------------------------

        results = retriever.retrieve(
            query=question,
            top_k=5,
            route=route_info["route"],
        )

        print(
            "\n---------- RETRIEVED CHUNKS ----------"
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
                f"{metadata.get('content_type')}"
            )

            print(
                f"Page: "
                f"{metadata.get('page_number')}"
            )

            print(
                f"Distance: "
                f"{result.get('distance', 0):.4f}"
            )

            print(
                f"Rerank Score: "
                f"{result.get('rerank_score', 0):.4f}"
            )

            print(
                f"Source: "
                f"{metadata.get('source')}"
            )

            content = result.get(
                "content",
                "",
            )

            if len(content) > 300:

                content = (
                    content[:300]
                    + "..."
                )

            print(
                f"Content:\n{content}"
            )


if __name__ == "__main__":
    main()