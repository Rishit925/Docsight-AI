from app.embeddings.embedding_service import EmbeddingService
from app.vectorstore.chroma_store import ChromaStore


class Retriever:
    """
    Modality-aware document retriever.

    Retrieval pipeline:

        User Query
           ↓
        Query Intent
           ↓
        Modality-specific retrieval
           ↓
        Candidate Fusion
           ↓
        Semantic + Intent Reranking
           ↓
        Comparison/entity matching
           ↓
        Deduplication
           ↓
        Final Results

    Supported routes:
        text
        table
        image
        multimodal
    """

    # ==================================================
    # ROUTE CONTENT TYPES
    # ==================================================

    ROUTE_CONTENT_TYPES = {
        "text": ["text"],
        "table": ["table", "text"],
        "image": ["image", "text"],
        "multimodal": ["text", "table", "image"],
    }

    # ==================================================
    # CONTENT TYPE PRIORITY
    # ==================================================

    CONTENT_TYPE_PRIORITY = {
        "text": {
            "text": 1.0,
            "table": 0.10,
            "image": 0.05,
        },

        "table": {
            "table": 1.0,
            "text": 0.25,
            "image": 0.0,
        },

        "image": {
            "image": 1.0,
            "text": 0.25,
            "table": 0.0,
        },

        "multimodal": {
            "text": 0.40,
            "table": 1.0,
            "image": 1.0,
        },
    }

    # ==================================================
    # QUERY INTENT KEYWORDS
    # ==================================================

    TABLE_INTENT_KEYWORDS = {
        "table",
        "tables",
        "tabular",
        "row",
        "rows",
        "column",
        "columns",
        "cell",
        "cells",
        "dataset",
        "tabulation",
    }

    IMAGE_INTENT_KEYWORDS = {
        "image",
        "images",
        "picture",
        "pictures",
        "photo",
        "photos",
        "diagram",
        "diagrams",
        "figure",
        "figures",
        "illustration",
        "illustrations",
        "visual",
        "visuals",
        "chart",
        "charts",
        "graph",
        "graphs",
        "shown",
        "shows",
        "pictured",
        "displayed",
    }

    COMPARISON_KEYWORDS = {
        "compare",
        "comparison",
        "comparative",
        "difference",
        "differences",
        "versus",
        "vs",
    }

    # ==================================================
    # INITIALIZATION
    # ==================================================

    def __init__(
        self,
        embedding_service=None,
        vector_store=None,
    ):
        """
        Initialize the retriever.
        """

        self.embedding_service = (
            embedding_service
            or EmbeddingService()
        )

        self.vector_store = (
            vector_store
            or ChromaStore()
        )

    # ==================================================
    # MAIN RETRIEVAL
    # ==================================================

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        route: str = "text",
        document_id=None,
    ):
        """
        Retrieve relevant chunks.
        """

        # ------------------------------------------
        # Validate query
        # ------------------------------------------

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        # ------------------------------------------
        # Validate top_k
        # ------------------------------------------

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        # ------------------------------------------
        # Validate route
        # ------------------------------------------

        if route not in self.ROUTE_CONTENT_TYPES:
            raise ValueError(
                f"Unknown route: {route}"
            )

        # ------------------------------------------
        # Detect query intent
        # ------------------------------------------

        intent = self._detect_intent(
            query
        )

        # ------------------------------------------
        # Create query embedding
        # ------------------------------------------

        query_embedding = (
            self.embedding_service.embed_text(
                query
            )
        )

        # ------------------------------------------
        # Retrieve candidates
        # ------------------------------------------

        candidates = (
            self._retrieve_candidates(
                query_embedding=query_embedding,
                route=route,
                document_id=document_id,
                top_k=top_k,
            )
        )

        # ------------------------------------------
        # Rerank candidates
        # ------------------------------------------

        ranked_results = self._rerank(
            candidates=candidates,
            route=route,
            intent=intent,
        )

        # ------------------------------------------
        # Deduplicate
        # ------------------------------------------

        ranked_results = (
            self._deduplicate(
                ranked_results
            )
        )

        # ------------------------------------------
        # Return final results
        # ------------------------------------------

        return ranked_results[:top_k]

    # ==================================================
    # CANDIDATE RETRIEVAL
    # ==================================================

    def _retrieve_candidates(
        self,
        query_embedding,
        route,
        document_id,
        top_k,
    ):
        """
        Retrieve candidates independently by modality.
        """

        candidates = []

        candidate_k = max(
            top_k * 4,
            10,
        )

        # ==================================================
        # MULTIMODAL
        # ==================================================

        if route == "multimodal":

            text_results = (
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=candidate_k,
                    content_types=["text"],
                    document_id=document_id,
                )
            )

            candidates.extend(
                self._parse_results(
                    text_results
                )
            )

            table_results = (
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=candidate_k,
                    content_types=["table"],
                    document_id=document_id,
                )
            )

            candidates.extend(
                self._parse_results(
                    table_results
                )
            )

            image_results = (
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=candidate_k,
                    content_types=["image"],
                    document_id=document_id,
                )
            )

            candidates.extend(
                self._parse_results(
                    image_results
                )
            )

            return candidates

        # ==================================================
        # TABLE
        # ==================================================

        if route == "table":

            table_results = (
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=candidate_k,
                    content_types=["table"],
                    document_id=document_id,
                )
            )

            candidates.extend(
                self._parse_results(
                    table_results
                )
            )

            text_results = (
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=candidate_k,
                    content_types=["text"],
                    document_id=document_id,
                )
            )

            candidates.extend(
                self._parse_results(
                    text_results
                )
            )

            return candidates

        # ==================================================
        # IMAGE
        # ==================================================

        if route == "image":

            image_results = (
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=candidate_k,
                    content_types=["image"],
                    document_id=document_id,
                )
            )

            candidates.extend(
                self._parse_results(
                    image_results
                )
            )

            text_results = (
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=candidate_k,
                    content_types=["text"],
                    document_id=document_id,
                )
            )

            candidates.extend(
                self._parse_results(
                    text_results
                )
            )

            return candidates

        # ==================================================
        # TEXT
        # ==================================================

        text_results = (
            self.vector_store.search(
                query_embedding=query_embedding,
                top_k=candidate_k,
                content_types=["text"],
                document_id=document_id,
            )
        )

        candidates.extend(
            self._parse_results(
                text_results
            )
        )

        return candidates

    # ==================================================
    # QUERY INTENT
    # ==================================================

    def _detect_intent(
        self,
        query,
    ):
        """
        Detect query intent.
        """

        query_lower = query.lower()

        words = set(
            query_lower
            .replace("?", " ")
            .replace(",", " ")
            .replace(".", " ")
            .replace(":", " ")
            .replace(";", " ")
            .replace("(", " ")
            .replace(")", " ")
            .split()
        )

        table_match = bool(
            words.intersection(
                self.TABLE_INTENT_KEYWORDS
            )
        )

        image_match = bool(
            words.intersection(
                self.IMAGE_INTENT_KEYWORDS
            )
        )

        comparison_match = bool(
            words.intersection(
                self.COMPARISON_KEYWORDS
            )
        )

        if (
            table_match
            and image_match
        ):
            primary_intent = "multimodal"

        elif table_match:
            primary_intent = "table"

        elif image_match:
            primary_intent = "image"

        else:
            primary_intent = "text"

        return {
        "table": table_match,
        "image": image_match,
        "comparison": comparison_match,
        "primary": primary_intent,
        "original_query": query,
        }

    # ==================================================
    # COMPARISON ENTITY EXTRACTION
    # ==================================================

    def _extract_comparison_entities(
        self,
        query,
    ):
        """
        Extract important comparison entities
        from the query.

        This is intentionally simple and transparent.

        It recognizes common Docsight comparison
        patterns such as:

            Traditional AI vs Machine Learning
            Machine Learning and Deep Learning
            differences between AI, ML and DL
        """

        query_lower = query.lower()

        entities = []

        # ------------------------------------------
        # Artificial Intelligence
        # ------------------------------------------

        if (
            "traditional ai"
            in query_lower
        ):
            entities.append(
                "traditional ai"
            )

        elif (
            "artificial intelligence"
            in query_lower
        ):
            entities.append(
                "artificial intelligence"
            )

        # ------------------------------------------
        # Machine Learning
        # ------------------------------------------

        if (
            "machine learning"
            in query_lower
        ):
            entities.append(
                "machine learning"
            )

        # ------------------------------------------
        # Deep Learning
        # ------------------------------------------

        if (
            "deep learning"
            in query_lower
        ):
            entities.append(
                "deep learning"
            )

        # ------------------------------------------
        # Common abbreviations
        # ------------------------------------------

        if (
            "ml"
            in query_lower.split()
            and "machine learning"
            not in entities
        ):
            entities.append(
                "machine learning"
            )

        if (
            "dl"
            in query_lower.split()
            and "deep learning"
            not in entities
        ):
            entities.append(
                "deep learning"
            )

        return entities

    # ==================================================
    # ENTITY MATCH SCORE
    # ==================================================

    def _calculate_entity_match_score(
        self,
        content,
        intent,
    ):
        """
        Calculate how many comparison entities
        from the query are actually present
        in the candidate content.

        Returns:
            0.0 to 1.0
        """

        if not intent.get(
            "comparison",
            False,
        ):
            return 0.0

        entities = (
            intent.get(
                "comparison_entities",
                [],
            )
        )

        if not entities:
            return 0.0

        content_lower = str(
            content or ""
        ).lower()

        matched = 0

        for entity in entities:

            if entity in content_lower:
                matched += 1

        return (
            matched
            / len(entities)
        )

    # ==================================================
    # PARSE RESULTS
    # ==================================================

    def _parse_results(
        self,
        results,
    ):
        """
        Convert ChromaDB results into
        normal dictionaries.
        """

        documents = results.get(
            "documents",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        parsed = []

        for index, document in enumerate(
            documents
        ):

            metadata = {}

            if index < len(
                metadatas
            ):
                metadata = (
                    metadatas[index]
                    or {}
                )

            distance = None

            if index < len(
                distances
            ):
                distance = (
                    distances[index]
                )

            content_type = (
                metadata.get(
                    "content_type",
                    "text",
                )
            )

            parsed.append(
                {
                    "content": document,
                    "metadata": metadata,
                    "distance": distance,
                    "content_type": content_type,
                }
            )

        return parsed

    # ==================================================
    # RERANK
    # ==================================================

    def _rerank(
        self,
        candidates,
        route,
        intent,
    ):
        """
        Rerank candidates.

        Specialized routes use:

            Semantic similarity       50%
            Content type priority     20%
            Query intent              20%
            Entity matching           10%

        Normal text retrieval uses:

            Semantic similarity       60%
            Content type priority     15%
            Query intent              25%
        """

        priority_map = (
            self.CONTENT_TYPE_PRIORITY[
                route
            ]
        )

        # ------------------------------------------
        # Extract comparison entities once
        # ------------------------------------------

        intent[
            "comparison_entities"
        ] = self._extract_comparison_entities(
            intent.get(
                "original_query",
                "",
            )
        )

        for candidate in candidates:

            distance = candidate.get(
                "distance"
            )

            content_type = (
                candidate.get(
                    "content_type",
                    "text",
                )
            )

            # ------------------------------------------
            # Semantic score
            # ------------------------------------------

            if distance is None:

                semantic_score = 0.0

            else:

                distance = float(
                    distance
                )

                semantic_score = (
                    1.0
                    / (1.0 + distance)
                )

            # ------------------------------------------
            # Content type priority
            # ------------------------------------------

            type_priority = (
                priority_map.get(
                    content_type,
                    0.0,
                )
            )

            # ------------------------------------------
            # Intent score
            # ------------------------------------------

            intent_score = (
                self._calculate_intent_score(
                    content_type=content_type,
                    intent=intent,
                    route=route,
                )
            )

            # ------------------------------------------
            # Entity matching
            # ------------------------------------------

            entity_match_score = (
                self._calculate_entity_match_score(
                    content=candidate.get(
                        "content",
                        "",
                    ),
                    intent=intent,
                )
            )

            # ------------------------------------------
            # Final score
            # ------------------------------------------

            if (
                route in {
                    "table",
                    "image",
                    "multimodal",
                }
            ):

                final_score = (
                    semantic_score * 0.50
                    + type_priority * 0.20
                    + intent_score * 0.20
                    + entity_match_score * 0.10
                )

            else:

                final_score = (
                    semantic_score * 0.60
                    + type_priority * 0.15
                    + intent_score * 0.25
                )

            candidate[
                "semantic_score"
            ] = round(
                semantic_score,
                4,
            )

            candidate[
                "type_priority"
            ] = round(
                type_priority,
                4,
            )

            candidate[
                "intent_score"
            ] = round(
                intent_score,
                4,
            )

            candidate[
                "entity_match_score"
            ] = round(
                entity_match_score,
                4,
            )

            candidate[
                "rerank_score"
            ] = round(
                final_score,
                4,
            )

        # ------------------------------------------
        # Sort
        # ------------------------------------------

        candidates.sort(
            key=lambda item: (
                item[
                    "rerank_score"
                ],
                item[
                    "semantic_score"
                ],
            ),
            reverse=True,
        )

        return candidates

    # ==================================================
    # INTENT SCORE
    # ==================================================

    def _calculate_intent_score(
        self,
        content_type,
        intent,
        route,
    ):
        """
        Calculate explicit modality intent.
        """

        table_requested = (
            intent["table"]
        )

        image_requested = (
            intent["image"]
        )

        comparison_requested = (
            intent["comparison"]
        )

        # ==================================================
        # TABLE + IMAGE
        # ==================================================

        if (
            table_requested
            and image_requested
        ):

            if content_type in {
                "table",
                "image",
            }:
                return 1.0

            if content_type == "text":
                return 0.40

            return 0.0

        # ==================================================
        # TABLE
        # ==================================================

        if table_requested:

            if content_type == "table":
                return 1.0

            if content_type == "text":
                return 0.25

            return 0.0

        # ==================================================
        # IMAGE
        # ==================================================

        if image_requested:

            if content_type == "image":
                return 1.0

            if content_type == "text":
                return 0.25

            return 0.0

        # ==================================================
        # COMPARISON
        # ==================================================

        if comparison_requested:

            if route == "table":

                if content_type == "table":
                    return 1.0

                if content_type == "text":
                    return 0.30

            elif route == "image":

                if content_type == "image":
                    return 1.0

                if content_type == "text":
                    return 0.30

            elif route == "multimodal":

                if content_type in {
                    "table",
                    "image",
                }:
                    return 1.0

                if content_type == "text":
                    return 0.40

        # ==================================================
        # NORMAL TEXT
        # ==================================================

        if content_type == "text":
            return 1.0

        if content_type == "table":
            return 0.05

        if content_type == "image":
            return 0.0

        return 0.0

    # ==================================================
    # DEDUPLICATION
    # ==================================================

    def _deduplicate(
        self,
        candidates,
    ):
        """
        Remove duplicate chunks.
        """

        unique = {}

        for candidate in candidates:

            metadata = candidate.get(
                "metadata",
                {},
            )

            chunk_id = metadata.get(
                "chunk_id"
            )

            if chunk_id:

                if chunk_id not in unique:
                    unique[
                        chunk_id
                    ] = candidate

                continue

            fallback_key = (
                metadata.get(
                    "document_id",
                    "",
                ),
                metadata.get(
                    "page_number",
                    "",
                ),
                candidate.get(
                    "content_type",
                    "text",
                ),
                candidate.get(
                    "content",
                    "",
                ),
            )

            if (
                fallback_key
                not in unique
            ):
                unique[
                    fallback_key
                ] = candidate

        return list(
            unique.values()
        )