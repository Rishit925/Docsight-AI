from app.api.services.query_service import QueryService


class FakeAnswerGenerator:
    def generate_answer(
        self,
        question,
        results=None,
        route="text",
        retrieved_chunks=None,
    ):
        chunks = results if results is not None else retrieved_chunks

        document_ids = []

        for chunk in chunks or []:
            document_id = chunk.get("document_id")

            if document_id and document_id not in document_ids:
                document_ids.append(document_id)

        return (
            "FAKE ANSWER | "
            f"documents={document_ids}"
        )


def print_result(title, result):
    print(f"\n===== {title} =====")
    print(result)


def main():
    service = QueryService(
        generator=FakeAnswerGenerator()
    )

    current_document_id = (
        "4f178feb-7c23-43ce-b7b6-d1c942a26b55"
    )

    # ---------------------------------------------------------
    # TEST 1: Normal question
    # ---------------------------------------------------------

    normal_question = "What technical skills are listed?"

    try:
        result = service.ask(
            document_id=current_document_id,
            question=normal_question,
        )

        print_result(
            "TEST 1 - NORMAL QUESTION",
            result,
        )

    except Exception as error:
        print(
            "\nTEST 1 FAILED:",
            type(error).__name__,
            str(error),
        )

    # ---------------------------------------------------------
    # TEST 2: Historical question
    # ---------------------------------------------------------

    historical_question = (
        "How do these skills compare with the previous document?"
    )

    try:
        result = service.ask(
            document_id=current_document_id,
            question=historical_question,
        )

        print_result(
            "TEST 2 - HISTORICAL QUESTION",
            result,
        )

    except Exception as error:
        print(
            "\nTEST 2 FAILED:",
            type(error).__name__,
            str(error),
        )

    # ---------------------------------------------------------
    # TEST 3: Only one document
    # ---------------------------------------------------------

    print("\n===== TEST 3 - ONE DOCUMENT SCENARIO =====")

    try:
        current_document = service.historical_retriever.document_store.get_document(
            current_document_id
        )

        original_get_all_documents = (
            service.historical_retriever.document_store.get_all_documents
        )

        service.historical_retriever.document_store.get_all_documents = (
            lambda: [current_document] if current_document else []
        )

        historical_result = service.historical_retriever.retrieve(
            question="What information is in this document?",
            current_document_id=current_document_id,
        )

        service.historical_retriever.document_store.get_all_documents = (
            original_get_all_documents
        )

        print(
            "Documents selected:",
            len(historical_result["documents"]),
        )

        for document in historical_result["documents"]:
            print(
                "-",
                document.get("document_id"),
                "|",
                document.get("file_name"),
            )

        print(
            "Retrieved results:",
            len(historical_result["results"]),
        )

        if len(historical_result["documents"]) != 1:
            raise AssertionError(
                "One-document scenario should select exactly one document."
            )

        print("TEST 3 completed successfully.")

    except Exception as error:
        print(
            "TEST 3 FAILED:",
            type(error).__name__,
            str(error),
        )

    # ---------------------------------------------------------
    # TEST 4: Empty question
    # ---------------------------------------------------------

    print("\n===== TEST 4 - EMPTY QUESTION =====")

    try:
        service.ask(
            document_id=current_document_id,
            question="",
        )

        print(
            "TEST 4 FAILED: "
            "empty question was accepted."
        )

    except Exception as error:
        print(
            "Expected error:",
            type(error).__name__,
            str(error),
        )

        print("TEST 4 completed successfully.")

    # ---------------------------------------------------------
    # TEST 5: Invalid document ID
    # ---------------------------------------------------------

    print("\n===== TEST 5 - INVALID DOCUMENT ID =====")

    invalid_document_id = "document-that-does-not-exist"

    try:
        result = service.ask(
            document_id=invalid_document_id,
            question="What information is available?",
        )

        print("Result:", result)

        print(
            "TEST 5 completed without crashing."
        )

    except Exception as error:
        print(
            "Expected/handled error:",
            type(error).__name__,
            str(error),
        )

        print(
            "TEST 5 completed with handled exception."
        )


if __name__ == "__main__":
    main()