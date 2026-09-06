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
        print("Question:", question)
        print("Route:", route)
        print("Retrieved chunks:", len(chunks or []))

        document_ids = []
        for chunk in chunks or []:
            document_id = chunk.get("document_id")
            if document_id and document_id not in document_ids:
                document_ids.append(document_id)

        print("Documents used:", document_ids)

        return (
            "FAKE ANSWER — historical pipeline executed successfully. "
            f"Documents used: {', '.join(document_ids)}"
        )


def main():
    service = QueryService(
        generator=FakeAnswerGenerator()
    )

    document_id = "4f178feb-7c23-43ce-b7b6-d1c942a26b55"

    question = "Why did sales increase compared with the previous month?"

    result = service.ask(
        document_id=document_id,
        question=question,
    )

    print("\n===== FINAL RESULT =====")
    print("Question:", result["question"])
    print("Answer:", result["answer"])
    print("Route:", result["route"])
    print("Content types:", result["content_types"])

    print("\n===== SOURCES =====")
    for source in result["sources"]:
        print(source)


if __name__ == "__main__":
    main()