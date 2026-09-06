import re

from app.database.document_store import DocumentStore
from app.retrieval.retriever import Retriever


class HistoricalRetriever:
    """
    Retrieves relevant information from the current document
    and relevant previously uploaded documents.

    Historical document selection is performed locally using
    document metadata and query terms. No LLM is used.

    Pipeline:

        Question
            ↓
        Historical documents
            ↓
        Local document relevance scoring
            ↓
        Relevant historical documents
            ↓
        Existing Retriever
            ↓
        Evidence from each document
    """

    # ==================================================
    # INITIALIZATION
    # ==================================================

    def __init__(
        self,
        retriever=None,
        document_store=None,
        max_historical_documents=5,
        top_k_per_document=3,
    ):
        self.retriever = (
            retriever
            or Retriever()
        )

        self.document_store = (
            document_store
            or DocumentStore()
        )

        self.max_historical_documents = max(
            1,
            int(max_historical_documents),
        )

        self.top_k_per_document = max(
            1,
            int(top_k_per_document),
        )

    # ==================================================
    # MAIN RETRIEVAL
    # ==================================================

    def retrieve(
        self,
        question,
        current_document_id=None,
        include_current=True,
        route="text",
    ):
        """
        Retrieve evidence from the current document and
        relevant historical documents.

        Historical documents are selected locally before
        semantic retrieval is performed.

        Returns:

            {
                "question": str,
                "current_document_id": str,
                "documents": [...],
                "results": [...]
            }
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        question = question.strip()

        all_documents = (
            self.document_store.get_all_documents()
        )

        if not all_documents:
            return {
                "question": question,
                "current_document_id": (
                    current_document_id
                ),
                "documents": [],
                "results": [],
            }

        selected_documents = (
            self._select_documents(
                all_documents=all_documents,
                question=question,
                current_document_id=(
                    current_document_id
                ),
                include_current=include_current,
            )
        )

        results = []

        for document in selected_documents:

            document_id = document.get(
                "document_id"
            )

            if not document_id:
                continue

            retrieved = self.retriever.retrieve(
                query=question,
                top_k=self.top_k_per_document,
                route=route,
                document_id=document_id,
            )

            for result in retrieved:

                if not isinstance(
                    result,
                    dict,
                ):
                    continue

                normalized_result = dict(
                    result
                )

                normalized_result[
                    "document_id"
                ] = document_id

                normalized_result[
                    "file_name"
                ] = document.get(
                    "file_name",
                    "Unknown",
                )

                normalized_result[
                    "upload_time"
                ] = document.get(
                    "upload_time"
                )

                results.append(
                    normalized_result
                )

        return {
            "question": question,
            "current_document_id": (
                current_document_id
            ),
            "documents": selected_documents,
            "results": results,
        }

    # ==================================================
    # DOCUMENT SELECTION
    # ==================================================

    def _select_documents(
        self,
        all_documents,
        question,
        current_document_id,
        include_current=True,
    ):
        """
        Select the current document and the most relevant
        historical documents.

        Current document:
            Always included when requested and available.

        Historical documents:
            Ranked using local metadata relevance.

        The ranking considers:
            - filename/query term overlap
            - temporal/comparison language
            - recency

        No LLM or external API is used.
        """

        current_document = None
        historical_documents = []

        for document in all_documents:

            document_id = document.get(
                "document_id"
            )

            if (
                current_document_id
                and document_id
                == current_document_id
            ):
                current_document = document

            else:
                historical_documents.append(
                    document
                )

        selected = []

        # ----------------------------------------------
        # Current document
        # ----------------------------------------------

        if (
            include_current
            and current_document is not None
        ):
            selected.append(
                current_document
            )

        # ----------------------------------------------
        # Rank historical documents
        # ----------------------------------------------

        ranked_historical = (
            self._rank_historical_documents(
                documents=historical_documents,
                question=question,
            )
        )

        selected.extend(
            ranked_historical[
                :self.max_historical_documents
            ]
        )

        return selected

    # ==================================================
    # RANK HISTORICAL DOCUMENTS
    # ==================================================

    def _rank_historical_documents(
        self,
        documents,
        question,
    ):
        """
        Rank historical documents using deterministic
        local signals.

        Score components:

            Filename relevance    0.65
            Temporal relevance    0.20
            Recency               0.15

        Filename relevance is deliberately strongest
        because it helps avoid retrieving unrelated
        historical documents such as resumes or unrelated
        reports.

        Recency remains a secondary signal so that a
        genuinely relevant older report can still outrank
        an unrelated recent document.
        """

        if not documents:
            return []

        query_tokens = self._tokenize(
            question
        )

        historical_language = (
            self._has_historical_language(
                question
            )
        )

        scored_documents = []

        total_documents = len(
            documents
        )

        for index, document in enumerate(
            documents
        ):

            file_name = str(
                document.get(
                    "file_name",
                    "",
                )
            )

            filename_tokens = self._tokenize(
                file_name
            )

            filename_score = (
                self._calculate_token_overlap(
                    query_tokens,
                    filename_tokens,
                )
            )

            temporal_score = (
                1.0
                if historical_language
                else 0.0
            )

            # Documents are returned newest-first by
            # DocumentStore. Convert that ordering into
            # a normalized recency score.
            if total_documents <= 1:
                recency_score = 1.0

            else:
                recency_score = (
                    total_documents
                    - index
                ) / total_documents

            final_score = (
                filename_score * 0.65
                + temporal_score * 0.20
                + recency_score * 0.15
            )

            scored_documents.append(
                {
                    "document": document,
                    "score": final_score,
                    "filename_score": filename_score,
                    "temporal_score": temporal_score,
                    "recency_score": recency_score,
                }
            )

        scored_documents.sort(
            key=lambda item: (
                item["score"],
                item["filename_score"],
                item["recency_score"],
            ),
            reverse=True,
        )

        return [
            item["document"]
            for item in scored_documents
        ]

    # ==================================================
    # TOKENIZE
    # ==================================================

    def _tokenize(
        self,
        text,
    ):
        """
        Convert text into normalized meaningful tokens.
        """

        if not text:
            return set()

        tokens = re.findall(
            r"[a-z0-9]+",
            str(text).lower(),
        )

        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "what",
            "why",
            "how",
            "did",
            "do",
            "does",
            "and",
            "or",
            "of",
            "to",
            "in",
            "on",
            "for",
            "with",
            "from",
            "than",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "their",
            "they",
            "them",
            "previous",
            "previously",
            "earlier",
            "prior",
            "compared",
            "compare",
            "comparison",
            "difference",
            "differences",
            "change",
            "changed",
            "increase",
            "increased",
            "decrease",
            "decreased",
            "trend",
            "trends",
            "pattern",
            "patterns",
        }

        return {
            token
            for token in tokens
            if token not in stop_words
            and len(token) > 1
        }

    # ==================================================
    # TOKEN OVERLAP
    # ==================================================

    def _calculate_token_overlap(
        self,
        query_tokens,
        filename_tokens,
    ):
        """
        Calculate normalized overlap between question
        terms and filename terms.

        Returns:
            0.0 to 1.0
        """

        if not query_tokens:
            return 0.0

        if not filename_tokens:
            return 0.0

        matched = (
            query_tokens.intersection(
                filename_tokens
            )
        )

        return len(
            matched
        ) / len(
            query_tokens
        )

    # ==================================================
    # HISTORICAL LANGUAGE
    # ==================================================

    def _has_historical_language(
        self,
        question,
    ):
        """
        Detect whether the question contains historical
        or comparative language.

        This is only a lightweight supporting signal.
        The main historical decision is still handled by
        HistoricalQueryDetector.
        """

        text = question.lower()

        patterns = [
            r"\bprevious\b",
            r"\bpreviously\b",
            r"\bearlier\b",
            r"\bprior\b",
            r"\bhistorical\b",
            r"\bhistory\b",
            r"\bcompare\b",
            r"\bcomparison\b",
            r"\bcompared\b",
            r"\bdifference\b",
            r"\bdifferences\b",
            r"\btrend\b",
            r"\btrends\b",
            r"\bpattern\b",
            r"\bpatterns\b",
            r"\bchange\b",
            r"\bchanged\b",
            r"\bincrease\b",
            r"\bincreased\b",
            r"\bdecrease\b",
            r"\bdecreased\b",
            r"\bgrowth\b",
            r"\bdecline\b",
            r"\bvs\b",
            r"\bversus\b",
        ]

        return any(
            re.search(
                pattern,
                text,
            )
            for pattern in patterns
        )

    # ==================================================
    # GROUP RESULTS BY DOCUMENT
    # ==================================================

    def group_results_by_document(
        self,
        results,
    ):
        """
        Group retrieved chunks by document.

        Returns:

            {
                document_id: [
                    result,
                    result,
                    ...
                ]
            }
        """

        grouped = {}

        if not results:
            return grouped

        for result in results:

            if not isinstance(
                result,
                dict,
            ):
                continue

            document_id = result.get(
                "document_id"
            )

            if not document_id:
                continue

            if document_id not in grouped:
                grouped[
                    document_id
                ] = []

            grouped[
                document_id
            ].append(
                result
            )

        return grouped

    # ==================================================
    # BUILD HISTORICAL CONTEXT
    # ==================================================

    def build_context(
        self,
        results,
    ):
        """
        Convert historical retrieval results into clearly
        separated document context.

        This method is retained for backwards compatibility.
        ComparisonService provides the newer structured
        comparison context.
        """

        grouped = (
            self.group_results_by_document(
                results
            )
        )

        if not grouped:
            return ""

        context_parts = []

        for document_id, document_results in (
            grouped.items()
        ):

            file_name = (
                document_results[0].get(
                    "file_name",
                    "Unknown",
                )
            )

            upload_time = (
                document_results[0].get(
                    "upload_time"
                )
            )

            context_parts.append(
                "===== DOCUMENT =====\n"
                f"Document ID: {document_id}\n"
                f"File name: {file_name}\n"
                f"Upload time: {upload_time}\n"
            )

            for index, result in enumerate(
                document_results,
                start=1,
            ):

                content = str(
                    result.get(
                        "content",
                        "",
                    )
                ).strip()

                if not content:
                    continue

                metadata = result.get(
                    "metadata",
                    {},
                )

                if not isinstance(
                    metadata,
                    dict,
                ):
                    metadata = {}

                source = (
                    result.get(
                        "source"
                    )
                    or metadata.get(
                        "source"
                    )
                    or file_name
                )

                page_number = (
                    result.get(
                        "page_number"
                    )
                    or metadata.get(
                        "page_number"
                    )
                    or "Unknown"
                )

                content_type = (
                    result.get(
                        "content_type"
                    )
                    or metadata.get(
                        "content_type"
                    )
                    or "text"
                )

                context_parts.append(
                    f"\nChunk {index}\n"
                    f"Source: {source}\n"
                    f"Page: {page_number}\n"
                    f"Type: {content_type}\n"
                    f"Content:\n"
                    f"{content}\n"
                )

        return "\n".join(
            context_parts
        ).strip()