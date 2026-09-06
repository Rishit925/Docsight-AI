import re


class Reranker:
    """
    Reranks retrieved chunks using:
    - semantic similarity
    - query keywords
    - content type
    - query intent
    - useful metadata signals
    """

    def rerank(
        self,
        query,
        chunks,
        route=None,
        top_k=5,
    ):
        if not query or not chunks:
            return []

        query_lower = query.lower()

        query_words = self._extract_keywords(
            query_lower
        )

        scored_chunks = []

        for chunk in chunks:

            score = self._calculate_score(
                query_lower=query_lower,
                query_words=query_words,
                chunk=chunk,
                route=route,
            )

            chunk_copy = dict(chunk)

            chunk_copy["rerank_score"] = score

            scored_chunks.append(
                chunk_copy
            )

        scored_chunks.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

        return scored_chunks[:top_k]

    # ==================================================
    # SCORE
    # ==================================================

    def _calculate_score(
        self,
        query_lower,
        query_words,
        chunk,
        route,
    ):

        content = chunk.get(
            "content",
            "",
        )

        content_lower = content.lower()

        metadata = chunk.get(
            "metadata",
            {},
        )

        content_type = metadata.get(
            "content_type",
            "text",
        )

        distance = chunk.get(
            "distance",
            1.0,
        )

        # --------------------------------------------------
        # Base semantic score
        #
        # Smaller distance = better result.
        # Convert it into a similarity-like score.
        # --------------------------------------------------

        semantic_score = 1.0 / (
            1.0 + distance
        )

        score = semantic_score * 5.0

        # --------------------------------------------------
        # Keyword matching
        # --------------------------------------------------

        keyword_matches = 0

        for word in query_words:

            if word in content_lower:
                keyword_matches += 1

        if query_words:

            keyword_ratio = (
                keyword_matches
                / len(query_words)
            )

            score += keyword_ratio * 4.0

        # --------------------------------------------------
        # Exact phrase matching
        # --------------------------------------------------

        important_phrases = (
            self._extract_phrases(
                query_lower
            )
        )

        for phrase in important_phrases:

            if phrase in content_lower:
                score += 3.0

        # --------------------------------------------------
        # Route-aware content type boosting
        # --------------------------------------------------

        if route == "table":

            if content_type == "table":
                score += 5.0

            elif content_type == "text":
                score += 1.0

            elif content_type == "image":
                score -= 2.0

        elif route == "image":

            if content_type == "image":
                score += 5.0

            elif content_type == "text":
                score += 1.0

            elif content_type == "table":
                score -= 2.0

        elif route == "multimodal":

            if content_type in {
                "table",
                "image",
            }:
                score += 3.0

        # --------------------------------------------------
        # Comparison intent
        # --------------------------------------------------

        comparison_terms = {
            "compare",
            "comparison",
            "difference",
            "differences",
            "versus",
            "vs",
            "contrast",
            "different",
        }

        comparison_query = any(
            term in query_lower
            for term in comparison_terms
        )

        if comparison_query:

            comparison_content_terms = {
                "comparison",
                "compare",
                "difference",
                "differences",
                "versus",
                "vs",
                "traditional ai",
                "machine learning",
                "deep learning",
            }

            comparison_matches = sum(
                1
                for term
                in comparison_content_terms
                if term in content_lower
            )

            score += (
                comparison_matches
                * 0.8
            )

        # --------------------------------------------------
        # Table-specific signals
        # --------------------------------------------------

        table_terms = {
            "dimension",
            "core approach",
            "key algorithms",
            "optimisation",
            "regularisation",
            "key strength",
            "key weakness",
            "advantages",
            "limitations",
            "primary use case",
            "category",
            "language",
        }

        table_signal_count = sum(
            1
            for term in table_terms
            if term in content_lower
        )

        if comparison_query:

            score += (
                table_signal_count
                * 0.5
            )

        # --------------------------------------------------
        # Penalize obvious low-value chunks
        # --------------------------------------------------

        low_value_terms = {
            "table of contents",
            "prepared by:",
            "©",
            "edition",
            "pages",
        }

        low_value_matches = sum(
            1
            for term in low_value_terms
            if term in content_lower
        )

        score -= (
            low_value_matches
            * 1.0
        )

        # --------------------------------------------------
        # Penalize very short title-like chunks
        # --------------------------------------------------

        word_count = len(
            content.split()
        )

        if word_count < 30:

            score -= 1.5

        return score

    # ==================================================
    # KEYWORDS
    # ==================================================

    def _extract_keywords(
        self,
        text,
    ):

        words = re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text,
        )

        stop_words = {
            "what",
            "is",
            "are",
            "the",
            "a",
            "an",
            "of",
            "to",
            "in",
            "on",
            "for",
            "and",
            "or",
            "does",
            "do",
            "how",
            "why",
            "between",
            "with",
            "from",
            "this",
            "that",
            "these",
            "those",
        }

        return [
            word
            for word in words
            if word not in stop_words
        ]

    # ==================================================
    # PHRASES
    # ==================================================

    def _extract_phrases(
        self,
        text,
    ):

        phrases = []

        known_phrases = [
            "traditional ai",
            "machine learning",
            "deep learning",
            "artificial intelligence",
            "core approach",
            "key algorithms",
            "key strength",
            "key weakness",
            "advantages and limitations",
            "primary use case",
        ]

        for phrase in known_phrases:

            if phrase in text:
                phrases.append(
                    phrase
                )

        return phrases