import re


class QueryRewriter:
    """
    Converts context-dependent questions into more
    self-contained queries using recent conversation history.

    This component intentionally uses local rules instead of
    an LLM so that query rewriting does not consume API tokens.
    """

    def __init__(self, max_history_messages=3):
        self.max_history_messages = max(
            1,
            int(max_history_messages),
        )

    def rewrite(
        self,
        question,
        history=None,
    ):
        """
        Rewrite a question when it depends on previous
        conversation context.

        Returns:

            {
                "original_query": str,
                "optimized_query": str,
                "used_memory": bool,
            }
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        question = question.strip()

        if not history:
            return {
                "original_query": question,
                "optimized_query": question,
                "used_memory": False,
            }

        recent_history = history[
            -self.max_history_messages:
        ]

        previous_question = self._get_previous_question(
            recent_history
        )

        if not previous_question:
            return {
                "original_query": question,
                "optimized_query": question,
                "used_memory": False,
            }

        if not self._needs_context(question):
            return {
                "original_query": question,
                "optimized_query": question,
                "used_memory": False,
            }

        topic = self._extract_topic(
            previous_question
        )

        if not topic:
            return {
                "original_query": question,
                "optimized_query": question,
                "used_memory": True,
            }

        optimized_query = self._rewrite_question(
            question=question,
            topic=topic,
        )

        return {
            "original_query": question,
            "optimized_query": optimized_query,
            "used_memory": True,
        }

    def _get_previous_question(
        self,
        history,
    ):
        """
        Find the most recent valid user question.
        """

        for message in reversed(history):
            if not isinstance(message, dict):
                continue

            question = str(
                message.get(
                    "question",
                    "",
                )
            ).strip()

            if question:
                return question

        return ""

    def _needs_context(
        self,
        question,
    ):
        """
        Detect whether the current question is likely
        related to the previous conversation.

        Context-dependent examples:

            What are its advantages?
            How is it different?
            What about its applications?
            Explain that again.
            What are some applications?

        The last example is intentionally included because
        short follow-up questions often rely on the previous topic.
        """

        text = question.lower().strip()

        contextual_patterns = [
            r"\bit\b",
            r"\bits\b",
            r"\bthey\b",
            r"\bthem\b",
            r"\btheir\b",
            r"\bthis\b",
            r"\bthat\b",
            r"\bthese\b",
            r"\bthose\b",
            r"\bthe same\b",
            r"\bmentioned\b",
            r"\babove\b",
            r"\bbefore\b",
            r"\bprevious\b",
            r"\bearlier\b",
            r"\bagain\b",
            r"\bmore about\b",
            r"\bapplications?\b",
            r"\badvantages?\b",
            r"\bdisadvantages?\b",
            r"\bbenefits?\b",
            r"\blimitations?\b",
            r"\bexamples?\b",
        ]

        for pattern in contextual_patterns:
            if re.search(
                pattern,
                text,
            ):
                return True

        return False

    def _extract_topic(
        self,
        previous_question,
    ):
        """
        Extract a simple topic from common question forms.

        Examples:

            "What is machine learning?"
                -> "machine learning"

            "What are neural networks?"
                -> "neural networks"

            "Explain deep learning."
                -> "deep learning"
        """

        text = previous_question.strip()

        patterns = [
            r"what\s+is\s+(.+?)[?.!]*$",
            r"what\s+are\s+(.+?)[?.!]*$",
            r"explain\s+(.+?)[?.!]*$",
            r"define\s+(.+?)[?.!]*$",
            r"tell\s+me\s+about\s+(.+?)[?.!]*$",
            r"describe\s+(.+?)[?.!]*$",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if match:
                topic = match.group(1).strip()

                topic = re.sub(
                    r"[?.!]+$",
                    "",
                    topic,
                ).strip()

                if topic:
                    return topic

        return ""

    def _rewrite_question(
        self,
        question,
        topic,
    ):
        """
        Build a grammatically cleaner standalone query.
        """

        text = question.strip()

        # ----------------------------------------------
        # Possessive references
        # ----------------------------------------------

        match = re.match(
            r"^what\s+are\s+its\s+(.+?)[?.!]*$",
            text,
            re.IGNORECASE,
        )

        if match:
            detail = match.group(1).strip()

            return (
                f"What are the {detail} "
                f"of {topic}?"
            )

        match = re.match(
            r"^what\s+is\s+its\s+(.+?)[?.!]*$",
            text,
            re.IGNORECASE,
        )

        if match:
            detail = match.group(1).strip()

            return (
                f"What is the {detail} "
                f"of {topic}?"
            )

        # ----------------------------------------------
        # "How is it..." pattern
        # ----------------------------------------------

        rewritten = re.sub(
            r"\bit\b",
            topic,
            text,
            flags=re.IGNORECASE,
        )

        # ----------------------------------------------
        # Other direct references
        # ----------------------------------------------

        rewritten = re.sub(
            r"\bthis\b",
            topic,
            rewritten,
            flags=re.IGNORECASE,
        )

        rewritten = re.sub(
            r"\bthat\b",
            topic,
            rewritten,
            flags=re.IGNORECASE,
        )

        rewritten = re.sub(
            r"\bthese\b",
            topic,
            rewritten,
            flags=re.IGNORECASE,
        )

        rewritten = re.sub(
            r"\bthose\b",
            topic,
            rewritten,
            flags=re.IGNORECASE,
        )

        rewritten = re.sub(
            r"\bthey\b",
            topic,
            rewritten,
            flags=re.IGNORECASE,
        )

        rewritten = re.sub(
            r"\bthem\b",
            topic,
            rewritten,
            flags=re.IGNORECASE,
        )

        rewritten = re.sub(
            r"\btheir\b",
            f"the {topic}'s",
            rewritten,
            flags=re.IGNORECASE,
        )

        # ----------------------------------------------
        # Remove accidental double spaces
        # ----------------------------------------------

        rewritten = re.sub(
            r"\s+",
            " ",
            rewritten,
        ).strip()

        return rewritten