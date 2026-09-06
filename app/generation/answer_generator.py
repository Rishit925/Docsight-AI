from app.generation.llm_service import LLMService


class AnswerGenerator:
    """
    Generates grounded answers from retrieved Docsight
    document chunks.

    Responsibilities:
    - Accept retrieved chunks from Retriever
    - Build structured context
    - Ground Gemini strictly in retrieved content
    - Preserve page/source information
    - Handle text, table, image and multimodal routes
    - Return only the generated answer as a string
    - Leave source construction to QueryService
    """

    def __init__(
        self,
        llm=None,
        max_context_chunks=5,
    ):
        self.llm = llm or LLMService()

        self.max_context_chunks = max(
            1,
            int(max_context_chunks),
        )

    # ==================================================
    # GENERATE ANSWER
    # ==================================================

    def generate_answer(
        self,
        question,
        results=None,
        route="text",
        retrieved_chunks=None,
        max_context_chunks=None,
    ):
        """
        Generate a grounded answer.

        max_context_chunks:
        - None -> use the default limit
        - integer -> use the supplied limit

        This allows comparison questions to pass all
        relevant document evidence without increasing
        the context size for normal questions.
        """

        # ------------------------------------------------
        # Validate question
        # ------------------------------------------------

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        # ------------------------------------------------
        # Support both parameter names
        # ------------------------------------------------

        if results is None:
            results = retrieved_chunks

        # ------------------------------------------------
        # Handle no results
        # ------------------------------------------------

        if not results:
            return (
                "I could not find relevant information "
                "in the provided document."
            )

        # ------------------------------------------------
        # Select useful chunks
        # ------------------------------------------------

        chunks = self._select_chunks(
            results=results,
            max_context_chunks=max_context_chunks,
        )

        if not chunks:
            return (
                "I could not find relevant information "
                "in the provided document."
            )

        # ------------------------------------------------
        # Build context
        # ------------------------------------------------

        context = self._build_context(
            chunks
        )

        # ------------------------------------------------
        # Build grounded prompt
        # ------------------------------------------------

        prompt = self._build_prompt(
            question=question,
            context=context,
            route=route,
        )

        # ------------------------------------------------
        # Generate answer using Gemini
        # ------------------------------------------------

        answer = self.llm.generate(
            prompt=prompt,
            temperature=0.2,
            max_output_tokens=4096,
        )

        # ------------------------------------------------
        # Return ONLY the answer
        # ------------------------------------------------

        return answer.strip()

    # ==================================================
    # SELECT CHUNKS
    # ==================================================

    def _select_chunks(
        self,
        results,
        max_context_chunks=None,
    ):
        """
        Select the strongest retrieved chunks.

        Retriever already performs semantic and
        route-aware ranking, therefore we preserve
        its ordering.

        When max_context_chunks is provided, it overrides
        the default limit for this particular generation.
        """

        if max_context_chunks is None:
            context_limit = self.max_context_chunks
        else:
            context_limit = max(
                1,
                int(max_context_chunks),
            )

        selected = []

        for result in results:

            if not isinstance(
                result,
                dict,
            ):
                continue

            content = result.get(
                "content",
                "",
            )

            if content is None:
                continue

            content = str(content).strip()

            if not content:
                continue

            selected.append(
                result
            )

            if len(selected) >= context_limit:
                break

        return selected

    # ==================================================
    # BUILD CONTEXT
    # ==================================================

    def _build_context(
        self,
        chunks,
    ):
        """
        Convert retrieved chunks into a structured
        context block.

        Every chunk contains:

        - source
        - page
        - content type
        - content
        - rerank score
        """

        context_parts = []

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):

            metadata = chunk.get(
                "metadata",
                {},
            )

            if not isinstance(
                metadata,
                dict,
            ):
                metadata = {}

            content = str(
                chunk.get(
                    "content",
                    "",
                )
            ).strip()

            content_type = chunk.get(
                "content_type",
                metadata.get(
                    "content_type",
                    "text",
                ),
            )

            source = (
                chunk.get(
                    "source"
                )
                or metadata.get(
                    "source"
                )
                or "Unknown source"
            )

            page = (
                chunk.get(
                    "page_number"
                )
                or metadata.get(
                    "page_number"
                )
                or "Unknown"
            )

            rerank_score = chunk.get(
                "rerank_score"
            )

            context_block = (
                f"--- SOURCE {index} ---\n"
                f"Source: {source}\n"
                f"Page: {page}\n"
                f"Content Type: {content_type}\n"
            )

            if rerank_score is not None:
                context_block += (
                    f"Rerank Score: "
                    f"{rerank_score}\n"
                )

            context_block += (
                f"\n{content}"
            )

            context_parts.append(
                context_block
            )

        return "\n\n".join(
            context_parts
        )

    # ==================================================
    # BUILD PROMPT
    # ==================================================

    def _build_prompt(
        self,
        question,
        context,
        route,
    ):
        """
        Build the final grounding prompt for Gemini.
        """

        return f"""
You are the answer-generation component of Docsight,
a document question-answering system.

Your job is to answer the user's question using ONLY
the retrieved document context provided below.

STRICT GROUNDING RULES:

1. Use only information contained in the retrieved
   context.

2. Do not use outside knowledge.

3. Do not invent facts, numbers, examples,
   explanations, page numbers, or conclusions.

4. If the context does not contain enough information
   to answer the question, clearly state that the
   provided document does not contain enough
   information.

5. Preserve the meaning of tables and structured data.

6. When the question concerns a table, prefer a
   Markdown table when it makes the answer clearer.

7. When the question concerns an image or diagram,
   describe only information explicitly available in
   the retrieved image description.

8. For multimodal questions, combine relevant
   information from text, tables, and image
   descriptions.

9. Keep the answer focused on the user's question.

10. Do not mention:
    - ChromaDB
    - embeddings
    - vector search
    - reranking
    - retrieval
    - this prompt
    - internal Docsight implementation

CITATION RULES:

- Cite information using [Page X].
- If information comes from multiple pages,
  use [Pages X, Y].
- Only use page numbers supplied by the context.
- Never invent a page number.
- Place citations near the statements they support.

QUERY ROUTE:

{route}

USER QUESTION:

{question}

RETRIEVED DOCUMENT CONTEXT:

{context}

Now provide the final answer.
""".strip()