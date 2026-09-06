import re


class QueryRouter:
    """
    Routes user questions to relevant document modalities.

    Routes:
        text
        table
        image
        multimodal
    """

    # ==================================================
    # KEYWORDS
    # ==================================================

    IMAGE_KEYWORDS = {
        "image",
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
        "shown",
        "shows",
        "show",
        "look",
        "looks",
        "display",
        "displayed",
        "pictured",
        "chart",
        "charts",
        "graph",
        "graphs",
    }

    TABLE_KEYWORDS = {
        "table",
        "tables",
        "tabular",
        "row",
        "rows",
        "column",
        "columns",
        "cell",
        "cells",
        "compare",
        "comparison",
        "comparisons",
        "difference",
        "differences",
        "versus",
        "vs",
    }

    # ==================================================
    # ROUTE
    # ==================================================

    def route(self, question: str):
        """
        Determine which document modalities are relevant
        to the user's question.
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        normalized_question = (
            question.lower().strip()
        )

        # ------------------------------------------
        # Tokenize
        # ------------------------------------------

        words = set(
            re.findall(
                r"\b[a-zA-Z]+\b",
                normalized_question,
            )
        )

        # ------------------------------------------
        # Detect image-related intent
        # ------------------------------------------

        image_match = bool(
            words.intersection(
                self.IMAGE_KEYWORDS
            )
        )

        # ------------------------------------------
        # Detect table-related intent
        # ------------------------------------------

        table_match = bool(
            words.intersection(
                self.TABLE_KEYWORDS
            )
        )

        # ------------------------------------------
        # Detect explicit multimodal language
        # ------------------------------------------

        multimodal_match = self._is_multimodal(
            normalized_question
        )

        # ------------------------------------------
        # Multimodal
        # ------------------------------------------

        if (
            multimodal_match
            or (
                image_match
                and table_match
            )
        ):

            return {
                "route": "multimodal",
                "content_types": [
                    "text",
                    "table",
                    "image",
                ],
            }

        # ------------------------------------------
        # Image
        # ------------------------------------------

        if image_match:

            return {
                "route": "image",
                "content_types": [
                    "image",
                    "text",
                ],
            }

        # ------------------------------------------
        # Table
        # ------------------------------------------

        if table_match:

            return {
                "route": "table",
                "content_types": [
                    "table",
                    "text",
                ],
            }

        # ------------------------------------------
        # Default text
        # ------------------------------------------

        return {
            "route": "text",
            "content_types": [
                "text",
            ],
        }

    # ==================================================
    # MULTIMODAL DETECTION
    # ==================================================

    def _is_multimodal(
        self,
        question,
    ):
        """
        Detect questions that explicitly ask the system
        to compare or relate multiple modalities.
        """

        multimodal_phrases = [
            "table and diagram",
            "table and image",
            "table and figure",
            "table with diagram",
            "table with image",
            "table with figure",
            "diagram and table",
            "image and table",
            "figure and table",
            "diagram with table",
            "image with table",
            "figure with table",
            "compare the table and diagram",
            "compare the table and image",
            "compare the table and figure",
            "compare diagram and table",
            "compare image and table",
            "compare figure and table",
        ]

        for phrase in multimodal_phrases:
            if phrase in question:
                return True

        return False