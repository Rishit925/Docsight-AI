class ComparisonService:
    """
    Organizes retrieved evidence for comparison questions.

    This service is intentionally deterministic and does not
    call an LLM. It prepares current, comparison, and guide
    document evidence so that the generation layer can reason
    over it.

    Responsibilities:
    - Identify current vs comparison documents
    - Identify comparison/reference guide documents
    - Group retrieved results by document
    - Preserve document metadata
    - Build structured comparison context
    - Provide comparison metadata
    - Keep evidence separated by document
    """

    def __init__(
        self,
        max_results_per_document=5,
    ):
        self.max_results_per_document = max(
            1,
            int(max_results_per_document),
        )

    # ==================================================
    # BUILD COMPARISON
    # ==================================================

    def build_comparison(
        self,
        results,
        current_document_id=None,
    ):
        """
        Organize retrieved results into a comparison structure.

        Returns:
            {
                "current_document": {...} or None,
                "comparison_documents": [...],
                "historical_documents": [...],
                "comparison_guides": [...],
                "documents": [...],
                "results_by_document": {...},
                "comparison_context": "...",
                "document_count": int,
            }
        """

        if not results:
            return {
                "current_document": None,
                "comparison_documents": [],
                "historical_documents": [],
                "comparison_guides": [],
                "documents": [],
                "results_by_document": {},
                "comparison_context": "",
                "document_count": 0,
            }

        grouped = self.group_results_by_document(
            results
        )

        document_metadata = (
            self._build_document_metadata(
                results
            )
        )

        current_document = None
        comparison_documents = []
        comparison_guides = []
        historical_documents = []

        for document in document_metadata:

            document_id = document.get(
                "document_id"
            )

            if (
                current_document_id
                and document_id
                == current_document_id
            ):
                current_document = document
                continue

            if self._is_comparison_guide(
                document
            ):
                comparison_guides.append(
                    document
                )
                continue

            comparison_documents.append(
                document
            )

        # If no explicit current document was supplied,
        # preserve the first non-guide document as current.
        if (
            current_document is None
            and document_metadata
            and not current_document_id
        ):
            for document in document_metadata:

                if self._is_comparison_guide(
                    document
                ):
                    continue

                current_document = document
                break

        # Historical documents are retained as a backwards-
        # compatible concept, but now exclude comparison guides.
        current_id = None

        if current_document:
            current_id = current_document.get(
                "document_id"
            )

        historical_documents = [
            document
            for document in comparison_documents
            if document.get("document_id")
            != current_id
        ]

        comparison_context = (
            self.build_context(
                results=results,
                current_document_id=(
                    current_id
                ),
            )
        )

        return {
            "current_document": current_document,
            "comparison_documents": comparison_documents,
            "historical_documents": historical_documents,
            "comparison_guides": comparison_guides,
            "documents": document_metadata,
            "results_by_document": grouped,
            "comparison_context": comparison_context,
            "document_count": len(
                document_metadata
            ),
        }

    # ==================================================
    # GROUP RESULTS
    # ==================================================

    def group_results_by_document(
        self,
        results,
    ):
        """
        Group retrieved chunks by document ID.

        The original retrieval ordering is preserved.
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

            document_id = (
                result.get(
                    "document_id"
                )
            )

            if not document_id:

                metadata = result.get(
                    "metadata",
                    {},
                )

                if isinstance(
                    metadata,
                    dict,
                ):
                    document_id = metadata.get(
                        "document_id"
                    )

            if not document_id:
                continue

            if document_id not in grouped:
                grouped[document_id] = []

            if len(
                grouped[document_id]
            ) >= self.max_results_per_document:
                continue

            grouped[
                document_id
            ].append(
                result
            )

        return grouped

    # ==================================================
    # DOCUMENT METADATA
    # ==================================================

    def _build_document_metadata(
        self,
        results,
    ):
        """
        Extract one metadata record for each document.
        """

        documents = {}
        order = []

        if not results:
            return []

        for result in results:

            if not isinstance(
                result,
                dict,
            ):
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

            document_id = (
                result.get(
                    "document_id"
                )
                or metadata.get(
                    "document_id"
                )
            )

            if not document_id:
                continue

            if document_id not in documents:

                file_name = (
                    result.get(
                        "file_name"
                    )
                    or metadata.get(
                        "file_name"
                    )
                    or metadata.get(
                        "source"
                    )
                    or "Unknown"
                )

                documents[
                    document_id
                ] = {
                    "document_id": document_id,
                    "file_name": file_name,
                    "result_count": 0,
                }

                order.append(
                    document_id
                )

            documents[
                document_id
            ][
                "result_count"
            ] += 1

        return [
            documents[
                document_id
            ]
            for document_id in order
        ]

    # ==================================================
    # COMPARISON GUIDE DETECTION
    # ==================================================

    def _is_comparison_guide(
        self,
        document,
    ):
        """
        Determine whether a document is a comparison/reference
        guide rather than a document being compared.

        This is deterministic and based only on the filename.
        """

        if not isinstance(
            document,
            dict,
        ):
            return False

        file_name = str(
            document.get(
                "file_name",
                "",
            )
        ).lower()

        guide_keywords = (
            "comparison_guide",
            "comparison-guide",
            "comparison guide",
            "comparison_reference",
            "comparison-reference",
            "comparison reference",
            "comparison_framework",
            "comparison-framework",
            "comparison framework",
        )

        return any(
            keyword in file_name
            for keyword in guide_keywords
        )

    # ==================================================
    # DOCUMENT ROLE
    # ==================================================

    def _get_document_role(
        self,
        document_id,
        document,
        current_document_id=None,
    ):
        """
        Return the semantic role of a document.
        """

        if (
            current_document_id
            and document_id
            == current_document_id
        ):
            return "CURRENT DOCUMENT"

        if self._is_comparison_guide(
            document
        ):
            return "COMPARISON GUIDE"

        return "COMPARISON DOCUMENT"

    # ==================================================
    # BUILD CONTEXT
    # ==================================================

    def build_context(
        self,
        results,
        current_document_id=None,
    ):
        """
        Build clearly separated comparison context.

        Each document gets its own section so the LLM can
        distinguish evidence belonging to different documents.
        """

        grouped = self.group_results_by_document(
            results
        )

        if not grouped:
            return ""

        document_metadata = (
            self._build_document_metadata(
                results
            )
        )

        metadata_by_id = {
            document[
                "document_id"
            ]: document
            for document in document_metadata
        }

        context_parts = []

        # --------------------------------------------------
        # Current document first
        # --------------------------------------------------

        ordered_document_ids = []

        if (
            current_document_id
            and current_document_id in grouped
        ):
            ordered_document_ids.append(
                current_document_id
            )

        # --------------------------------------------------
        # Comparison documents and guide documents
        # --------------------------------------------------

        for document_id in grouped:

            if document_id not in ordered_document_ids:
                ordered_document_ids.append(
                    document_id
                )

        for document_id in ordered_document_ids:

            document = metadata_by_id.get(
                document_id,
                {},
            )

            document_role = (
                self._get_document_role(
                    document_id=document_id,
                    document=document,
                    current_document_id=(
                        current_document_id
                    ),
                )
            )

            file_name = document.get(
                "file_name",
                "Unknown",
            )

            context_parts.append(
                "==================================================\n"
                f"{document_role}\n"
                "==================================================\n"
                f"Document ID: {document_id}\n"
                f"File name: {file_name}\n"
            )

            document_results = grouped[
                document_id
            ]

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
                    f"\nEvidence {index}\n"
                    f"Source: {source}\n"
                    f"Page: {page_number}\n"
                    f"Content Type: {content_type}\n"
                    f"Content:\n"
                    f"{content}\n"
                )

        return "\n".join(
            context_parts
        ).strip()

    # ==================================================
    # GET DOCUMENT IDS
    # ==================================================

    def get_document_ids(
        self,
        results,
    ):
        """
        Return unique document IDs in retrieval order.
        """

        grouped = self.group_results_by_document(
            results
        )

        return list(
            grouped.keys()
        )

    # ==================================================
    # GET COMPARISON DOCUMENT IDS
    # ==================================================

    def get_comparison_document_ids(
        self,
        results,
        current_document_id=None,
    ):
        """
        Return document IDs that represent actual comparison
        documents, excluding the current document and any
        comparison/reference guide.
        """

        document_metadata = (
            self._build_document_metadata(
                results
            )
        )

        comparison_ids = []

        for document in document_metadata:

            document_id = document.get(
                "document_id"
            )

            if not document_id:
                continue

            if (
                current_document_id
                and document_id
                == current_document_id
            ):
                continue

            if self._is_comparison_guide(
                document
            ):
                continue

            comparison_ids.append(
                document_id
            )

        return comparison_ids

    # ==================================================
    # GET HISTORICAL DOCUMENT IDS
    # ==================================================

    def get_historical_document_ids(
        self,
        results,
        current_document_id=None,
    ):
        """
        Return comparison/historical document IDs while
        excluding comparison guides.
        """

        return self.get_comparison_document_ids(
            results=results,
            current_document_id=(
                current_document_id
            ),
        )

    # ==================================================
    # HAS COMPARISON
    # ==================================================

    def has_comparison_evidence(
        self,
        results,
        current_document_id=None,
    ):
        """
        Return True only when evidence exists from the current
        document and at least one actual comparison document.

        Comparison guides do not count as comparison documents.
        """

        if not current_document_id:
            document_ids = (
                self.get_comparison_document_ids(
                    results=results,
                    current_document_id=None,
                )
            )

            return len(document_ids) >= 2

        comparison_ids = (
            self.get_comparison_document_ids(
                results=results,
                current_document_id=(
                    current_document_id
                ),
            )
        )

        current_present = (
            current_document_id
            in self.get_document_ids(
                results
            )
        )

        return (
            current_present
            and len(comparison_ids) >= 1
        )