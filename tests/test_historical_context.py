from app.api.services.query_service import QueryService


class FakeAnswerGenerator:
    def generate_answer(
        self,
        question,
        results=None,
        route="text",
        retrieved_chunks=None,
    ):
        return "FAKE ANSWER"


def main():
    service = QueryService(
        generator=FakeAnswerGenerator()
    )

    question = "Why did sales increase compared with the previous month?"

    rewritten = service.query_rewriter.rewrite(
        question,
        service.conversation_memory.get_history(
            "4f178feb-7c23-43ce-b7b6-d1c942a26b55"
        ),
    )

    print("===== QUERY =====")
    print(question)

    print("\n===== REWRITTEN QUERY =====")
    print(rewritten)

    detection = service.historical_query_detector.detect(
        rewritten["optimized_query"]
    )

    print("\n===== HISTORICAL DETECTION =====")
    print(detection)

    retrieved = service.historical_retriever.retrieve(
        question=rewritten["optimized_query"],
        current_document_id="4f178feb-7c23-43ce-b7b6-d1c942a26b55",
    )

    print("\n===== DOCUMENTS SELECTED =====")

    for document in retrieved["documents"]:
        print(
            f"- {document['document_id']} | "
            f"{document['file_name']}"
        )

    print("\n===== RETRIEVED RESULTS =====")

    for index, result in enumerate(retrieved["results"], start=1):
        metadata = result.get("metadata", {})

        print(f"\nResult {index}")

        print(
            f"Document ID: "
            f"{result.get('document_id')}"
        )

        print(
            f"File name: "
            f"{result.get('file_name')}"
        )

        print(
            f"Page: "
            f"{metadata.get('page_number', result.get('page_number'))}"
        )

        print(
            f"Content type: "
            f"{result.get('content_type', metadata.get('content_type'))}"
        )

        print(
            f"Source: "
            f"{metadata.get('source', result.get('source'))}"
        )

    context = service.historical_retriever.build_context(
        retrieved["results"]
    )

    print("\n===== BUILT HISTORICAL CONTEXT =====")
    print(context)

    grouped = service.historical_retriever.group_results_by_document(
        retrieved["results"]
    )

    print("\n===== GROUPED RESULTS =====")

    for document_id, results in grouped.items():
        print(
            f"{document_id}: "
            f"{len(results)} result(s)"
        )


if __name__ == "__main__":
    main()