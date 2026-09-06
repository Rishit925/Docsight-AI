from app.memory.query_rewriter import QueryRewriter


def main():
    rewriter = QueryRewriter()

    history = [
        {
            "question": "What is machine learning?",
            "answer": "Machine learning is a subset of artificial intelligence.",
        }
    ]

    test_cases = [
        "What is machine learning?",
        "What are its applications?",
        "How is it different?",
        "What technical skills are listed?",
        "How do those skills compare with the previous document?",
        "Why did sales increase compared with the previous month?",
    ]

    print("===== QUERY REWRITER TESTS =====")

    for question in test_cases:
        result = rewriter.rewrite(
            question=question,
            history=history,
        )

        print("\nOriginal:")
        print(result["original_query"])

        print("Optimized:")
        print(result["optimized_query"])

        print("Used memory:")
        print(result["used_memory"])

        if not result["optimized_query"].strip():
            raise AssertionError(
                "Optimized query must not be empty."
            )

    print("\n===== ALL QUERY REWRITER TESTS PASSED =====")


if __name__ == "__main__":
    main()