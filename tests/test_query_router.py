from app.retrieval.query_router import QueryRouter


def main():

    router = QueryRouter()

    questions = [
        "What is syntax?",
        "What is the difference between syntax and semantics?",
        "What does the diagram show?",
        "What does the table compare?",
        "Compare the diagram with the table.",
    ]

    print("\n========== QUERY ROUTING ==========")

    for question in questions:

        result = router.route(question)

        print(
            f"\nQuestion: {question}"
        )

        print(
            f"Route: {result['route']}"
        )

        print(
            f"Content types: "
            f"{result['content_types']}"
        )


if __name__ == "__main__":
    main()