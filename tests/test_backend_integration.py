from app.api.services.query_service import QueryService
from app.database.document_store import DocumentStore
from app.memory.query_rewriter import QueryRewriter


class FakeAnswerGenerator:
    def generate_answer(
        self,
        question,
        results,
        route,
        max_context_chunks=None,
    ):
        chunks = results if results is not None else []

        document_ids = []

        for chunk in chunks:
            document_id = chunk.get("document_id")

            if document_id and document_id not in document_ids:
                document_ids.append(document_id)

        return f"FAKE ANSWER | documents={document_ids}"


def get_current_document_id():
    documents = DocumentStore().get_all_documents()

    current_documents = [
        document
        for document in documents
        if "FlowCV_Resume" in document["file_name"]
    ]

    if not current_documents:
        raise AssertionError(
            "Current FlowCV resume document was not found in the document store."
        )

    return current_documents[0]["document_id"]


def create_service():
    return QueryService(
        generator=FakeAnswerGenerator()
    )


def test_normal_question_uses_current_document_only():
    current_document_id = get_current_document_id()
    service = create_service()

    result = service.ask(
        document_id=current_document_id,
        question="What technical skills are listed?",
    )

    assert result["route"] == "text"
    assert len(result["sources"]) > 0

    document_ids = {
        source["document_id"]
        for source in result["sources"]
        if source.get("document_id")
    }

    assert document_ids == {current_document_id}
    assert "comparison" not in result


def test_historical_question_uses_current_and_previous_documents():
    current_document_id = get_current_document_id()
    service = create_service()

    result = service.ask(
        document_id=current_document_id,
        question="How do these skills compare with the previous document?",
    )

    assert result["route"] == "table"

    document_ids = {
        source["document_id"]
        for source in result["sources"]
        if source.get("document_id")
    }

    assert current_document_id in document_ids
    assert len(document_ids) >= 2

    assert "comparison" in result
    assert result["comparison"]["enabled"] is True
    assert result["comparison"]["document_count"] >= 2


def test_historical_detector_identifies_comparison_question():
    service = create_service()

    detection = service.historical_query_detector.detect(
        "Why did sales increase compared with the previous month?"
    )

    assert detection["is_historical"] is True


def test_historical_detector_does_not_flag_normal_question():
    service = create_service()

    detection = service.historical_query_detector.detect(
        "What technical skills are listed?"
    )

    assert detection["is_historical"] is False


def test_query_rewriter_preserves_comparison_question():
    rewriter = QueryRewriter()

    history = [
        {
            "question": "What is machine learning?",
            "answer": "Machine learning is a subset of artificial intelligence.",
        }
    ]

    result = rewriter.rewrite(
        "Why did sales increase compared with the previous month?",
        history,
    )

    assert result["used_memory"] is True
    assert (
        result["optimized_query"]
        == "Why did sales increase compared with the previous month?"
    )


def test_query_rewriter_resolves_contextual_question():
    rewriter = QueryRewriter()

    history = [
        {
            "question": "What is machine learning?",
            "answer": "Machine learning is a subset of artificial intelligence.",
        }
    ]

    result = rewriter.rewrite(
        "What are its applications?",
        history,
    )

    assert result["used_memory"] is True
    assert "machine learning" in result["optimized_query"].lower()


def test_empty_question_is_rejected():
    current_document_id = get_current_document_id()
    service = create_service()

    try:
        service.ask(
            document_id=current_document_id,
            question="",
        )
    except ValueError as error:
        assert str(error) == "Question cannot be empty."
    else:
        raise AssertionError(
            "Empty question should raise ValueError."
        )


def test_comparison_service_separates_documents():
    current_document_id = get_current_document_id()
    service = create_service()

    result = service.ask(
        document_id=current_document_id,
        question="How do these skills compare with the previous document?",
    )

    comparison = result["comparison"]

    assert comparison["enabled"] is True
    assert comparison["current_document"]["document_id"] == (
        current_document_id
    )
    assert len(comparison["historical_documents"]) >= 1