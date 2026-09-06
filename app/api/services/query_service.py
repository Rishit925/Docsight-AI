from app.retrieval.query_router import QueryRouter
from app.retrieval.retriever import Retriever
from app.generation.answer_generator import AnswerGenerator
from app.database.conversation_store import ConversationStore
from app.memory.conversation_memory import ConversationMemory
from app.memory.query_rewriter import QueryRewriter
from app.memory.historical_query_detector import (
    HistoricalQueryDetector,
)
from app.memory.historical_retriever import (
    HistoricalRetriever,
)
from app.comparison.comparison_service import (
    ComparisonService,
)


class QueryService:
    """
    Coordinates the complete Docsight question-answering
    pipeline.

    Pipeline:

        User Question
              ↓
        ConversationMemory
              ↓
        QueryRewriter
              ↓
        HistoricalQueryDetector
              ↓
        QueryRouter
              ↓
        ┌─────────────────────────────────────────┐
        │                                         │
        │ Normal                     Historical   │
        │   ↓                            ↓        │
        │ Retriever              HistoricalRetriever
        │                                ↓        │
        │                         ComparisonService
        │                                │        │
        └──────────────┬─────────────────┘
                       ↓
                 AnswerGenerator
                       ↓
                ConversationStore
                       ↓
               Structured Response
    """

    def __init__(
        self,
        router=None,
        retriever=None,
        generator=None,
        conversation_store=None,
        conversation_memory=None,
        query_rewriter=None,
        historical_query_detector=None,
        historical_retriever=None,
        comparison_service=None,
    ):
        self.router = (
            router
            or QueryRouter()
        )

        self.retriever = (
            retriever
            or Retriever()
        )

        self.generator = (
            generator
            or AnswerGenerator()
        )

        self.conversation_store = (
            conversation_store
            or ConversationStore()
        )

        self.conversation_memory = (
            conversation_memory
            or ConversationMemory()
        )

        self.query_rewriter = (
            query_rewriter
            or QueryRewriter()
        )

        self.historical_query_detector = (
            historical_query_detector
            or HistoricalQueryDetector()
        )

        self.historical_retriever = (
            historical_retriever
            or HistoricalRetriever(
                retriever=self.retriever
            )
        )

        self.comparison_service = (
            comparison_service
            or ComparisonService()
        )

    # ==================================================
    # ASK
    # ==================================================

    def ask(
        self,
        question: str,
        document_id: str = None,
        top_k: int = 5,
    ):
        """
        Process a user question using document retrieval,
        conversation memory, query rewriting, and historical
        comparison when required.
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        question = question.strip()

        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1."
            )

        # --------------------------------------------------
        # 1. Retrieve previous conversation
        # --------------------------------------------------

        history = []

        if document_id:
            history = (
                self.conversation_memory.get_history(
                    document_id
                )
            )

        # --------------------------------------------------
        # 2. Rewrite query using conversation context
        # --------------------------------------------------

        rewrite_result = (
            self.query_rewriter.rewrite(
                question=question,
                history=history,
            )
        )

        optimized_query = rewrite_result[
            "optimized_query"
        ]

        used_memory = rewrite_result[
            "used_memory"
        ]

        # --------------------------------------------------
        # 3. Detect historical/comparative intent
        # --------------------------------------------------

        historical_result = (
            self.historical_query_detector.detect(
                optimized_query
            )
        )

        is_historical = historical_result[
            "is_historical"
        ]

        # --------------------------------------------------
        # 4. Route optimized query
        # --------------------------------------------------

        route_info = self.router.route(
            optimized_query
        )

        route = route_info[
            "route"
        ]

        content_types = route_info[
            "content_types"
        ]

        # --------------------------------------------------
        # 5. Retrieve relevant document chunks
        # --------------------------------------------------

        historical_result_data = None
        comparison_data = None

        if is_historical:

            historical_result_data = (
                self.historical_retriever.retrieve(
                    question=optimized_query,
                    current_document_id=document_id,
                    include_current=True,
                    route=route,
                )
            )

            results = historical_result_data[
                "results"
            ]

            # ----------------------------------------------
            # Build structured comparison data
            # ----------------------------------------------

            comparison_data = (
                self.comparison_service.build_comparison(
                    results=results,
                    current_document_id=document_id,
                )
            )

        else:

            results = self.retriever.retrieve(
                query=optimized_query,
                top_k=top_k,
                route=route,
                document_id=document_id,
            )

        # --------------------------------------------------
        # 6. Build conversation context
        # --------------------------------------------------

        conversation_context = ""

        if used_memory and document_id:
            conversation_context = (
                self.conversation_memory.build_context(
                    document_id
                )
            )

        # --------------------------------------------------
        # 7. Build historical/comparison context
        # --------------------------------------------------

        historical_context = ""

        if is_historical:

            if comparison_data:
                historical_context = (
                    comparison_data.get(
                        "comparison_context",
                        "",
                    )
                )

        # --------------------------------------------------
        # 8. Generate answer
        # --------------------------------------------------

        answer = self._generate_answer(
            question=question,
            results=results,
            route=route,
            conversation_context=conversation_context,
            historical_context=historical_context,
            is_historical=is_historical,
            comparison_data=comparison_data,
        )

        # --------------------------------------------------
        # 9. Build sources
        # --------------------------------------------------

        sources = self._build_sources(
            results
        )

        # --------------------------------------------------
        # 10. Save conversation
        # --------------------------------------------------

        if document_id:

            self.conversation_store.add_message(
                document_id=document_id,
                question=question,
                answer=answer,
                route=route,
                content_types=content_types,
            )

        # --------------------------------------------------
        # 11. Return response
        # --------------------------------------------------

        response = {
            "question": question,
            "answer": answer,
            "route": route,
            "content_types": content_types,
            "sources": sources,
        }

        # Add comparison metadata only for historical
        # questions.
        if (
            is_historical
            and comparison_data is not None
        ):
            response[
                "comparison"
            ] = {
                "enabled": True,

                "document_count": (
                    comparison_data.get(
                        "document_count",
                        0,
                    )
                ),

                "current_document": (
                    comparison_data.get(
                        "current_document"
                    )
                ),

                "comparison_documents": (
                    comparison_data.get(
                        "comparison_documents",
                        [],
                    )
                ),

                "comparison_guides": (
                    comparison_data.get(
                        "comparison_guides",
                        [],
                    )
                ),

                # Kept for backward compatibility.
                "historical_documents": (
                    comparison_data.get(
                        "historical_documents",
                        [],
                    )
                ),
            }

        return response

    # ==================================================
    # GENERATE ANSWER
    # ==================================================

    def _generate_answer(
        self,
        question,
        results,
        route,
        conversation_context="",
        historical_context="",
        is_historical=False,
        comparison_data=None,
    ):
        """
        Generate an answer using the existing
        AnswerGenerator interface.

        Conversation context is included when the
        question depends on previous conversation.

        Historical context is included when the question
        requires information from previous documents.

        Comparison instructions are added only for
        historical/comparative questions.
        """

        additional_context = []

        # --------------------------------------------------
        # Conversation memory
        # --------------------------------------------------

        if conversation_context:

            additional_context.append(
                "Use the following previous conversation "
                "only when it helps understand the current "
                "question.\n\n"
                "Previous conversation:\n"
                f"{conversation_context}"
            )

        # --------------------------------------------------
        # Historical/comparison context
        # --------------------------------------------------

        if historical_context:

            document_count = 0

            if comparison_data:
                document_count = (
                    comparison_data.get(
                        "document_count",
                        0,
                    )
                )

            comparison_instructions = (
                "The following evidence comes from "
                f"{document_count} document(s).\n\n"

                "For this historical or comparative "
                "question:\n"

                "1. Distinguish the current document "
                "from comparison documents.\n"

                "2. If a comparison guide or reference "
                "document is present, identify it as a "
                "COMPARISON GUIDE. Use it as a comparison "
                "framework. Use its dimensions, criteria, "
                "metrics, advantages, limitations, "
                "structure, or other relevant guidance "
                "to decide how the documents should be "
                "compared.\n"

                "3. Do NOT treat the comparison guide "
                "as one of the documents being compared.\n"

                "4. Do NOT require the comparison guide "
                "itself to contain a direct comparison "
                "between the user's documents.\n"

                "5. Determine the actual differences, "
                "similarities, changes, or trends from "
                "the retrieved content of the documents "
                "being compared.\n"

                "6. Base factual claims only on the "
                "provided document evidence.\n"

                "7. Do not invent facts, differences, "
                "numbers, or conclusions that are not "
                "supported by the documents.\n"

                "8. When the available evidence supports "
                "a comparison, provide the comparison "
                "instead of saying that the documents "
                "must already contain an explicit "
                "comparison.\n"

                "9. If a specific comparison dimension "
                "cannot be evaluated from the retrieved "
                "evidence, clearly state that the evidence "
                "is insufficient for that dimension.\n\n"

                "Comparison evidence:\n"
                f"{historical_context}"
            )

            additional_context.append(
                comparison_instructions
            )

        # --------------------------------------------------
        # No additional context
        # --------------------------------------------------

        if not additional_context:

            return self.generator.generate_answer(
                question=question,
                results=results,
                route=route,
            )

        # --------------------------------------------------
        # Build contextual question
        # --------------------------------------------------

        contextual_question = (
            "\n\n".join(
                additional_context
            )
            + "\n\n"
            "Current question:\n"
            f"{question}"
        )

        context_limit = None

        if (
            is_historical
            and comparison_data
        ):
            context_limit = len(results)

        return self.generator.generate_answer(
            question=contextual_question,
            results=results,
            route=route,
            max_context_chunks=context_limit,
        )

    # ==================================================
    # BUILD SOURCES
    # ==================================================

    def _build_sources(
        self,
        results,
    ):
        """
        Build unique source references.

        For comparison questions, document_id and
        file_name allow the frontend to distinguish
        evidence from different documents.
        """

        sources = []
        seen = set()

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

            source = (
                result.get(
                    "source"
                )
                or metadata.get(
                    "source"
                )
                or "Unknown"
            )

            page_number = (
                result.get(
                    "page_number"
                )
                or metadata.get(
                    "page_number"
                )
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

            document_id = (
                result.get(
                    "document_id"
                )
                or metadata.get(
                    "document_id"
                )
            )

            file_name = result.get(
                "file_name"
            )

            key = (
                str(document_id),
                str(source),
                str(page_number),
                str(content_type),
            )

            if key in seen:
                continue

            seen.add(key)

            source_data = {
                "source": source,
                "page_number": page_number,
                "content_type": content_type,
            }

            if document_id:
                source_data[
                    "document_id"
                ] = document_id

            if file_name:
                source_data[
                    "file_name"
                ] = file_name

            sources.append(
                source_data
            )

        return sources