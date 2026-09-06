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

        print("\n===== FAKE GENERATOR =====")
        print("Question received by generator:")
        print(question)

        print("\nRetrieved chunks:", len(chunks or []))

        document_ids = []
        for chunk in chunks or []:
            document_id = chunk.get("document_id")

            if document_id and document_id not in document_ids:
                document_ids.append(document_id)

        print("Documents used:")
        for document_id in document_ids:
            print("-", document_id)

        return (
            "FAKE ANSWER — memory integration pipeline "
            "executed successfully."
        )


def main():
    service = QueryService(
        generator=FakeAnswerGenerator()
    )

    document_id = "4f178feb-7c23-43ce-b7b6-d1c942a26b55"

    first_question = "What technical skills are listed in the document?"

    print("===== FIRST QUESTION =====")
    print(first_question)

    first_result = service.ask(
        document_id=document_id,
        question=first_question,
    )

    print("\n===== FIRST RESULT =====")
    print(first_result["answer"])

    print("\n===== CONVERSATION HISTORY AFTER FIRST QUESTION =====")

    history = service.conversation_memory.get_history(
        document_id
    )

    for message in history:
        print("Question:", message.get("question"))
        print("Answer:", message.get("answer"))
        print()

    second_question = (
        "How do those skills compare with the previous document?"
    )

    print("===== SECOND QUESTION =====")
    print(second_question)

    rewritten = service.query_rewriter.rewrite(
        second_question,
        history,
    )

    print("\n===== REWRITTEN SECOND QUESTION =====")
    print(rewritten)

    optimized_query = rewritten["optimized_query"]

    detection = service.historical_query_detector.detect(
        optimized_query
    )

    print("\n===== HISTORICAL DETECTION =====")
    print(detection)

    second_result = service.ask(
        document_id=document_id,
        question=second_question,
    )

    print("\n===== SECOND RESULT =====")
    print("Question:", second_result["question"])
    print("Answer:", second_result["answer"])
    print("Route:", second_result["route"])

    print("\n===== SECOND SOURCES =====")

    for source in second_result["sources"]:
        print(source)


if __name__ == "__main__":
    main()