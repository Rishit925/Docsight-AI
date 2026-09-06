import re


class HistoricalQueryDetector:
    """
    Detects whether a user question requires information
    from previous documents or historical document context.

    This component intentionally uses local rules instead
    of an LLM so that query analysis does not consume
    Gemini API requests.
    """

    # ==================================================
    # HISTORICAL / COMPARATIVE PATTERNS
    # ==================================================

    HISTORICAL_PATTERNS = [
        r"\bprevious\b",
        r"\bpreviously\b",
        r"\bearlier\b",
        r"\bprior\b",
        r"\bhistorical\b",
        r"\bhistory\b",
        r"\blast\s+(month|quarter|year|week|period)\b",
        r"\bprior\s+(month|quarter|year|period)\b",
        r"\bprevious\s+(month|quarter|year|period)\b",
        r"\bcompared\s+with\b",
        r"\bcompared\s+to\b",
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\bdifference\b",
        r"\bdifferences\b",
        r"\btrend\b",
        r"\btrends\b",
        r"\bpattern\b",
        r"\bpatterns\b",
        r"\bchange\b",
        r"\bchanged\b",
        r"\bincreased\b",
        r"\bdecreased\b",
        r"\bincrease\b",
        r"\bdecrease\b",
        r"\bgrowth\b",
        r"\bdecline\b",
        r"\bdeviation\b",
        r"\bdeviated\b",
        r"\bvs\.?\b",
        r"\bversus\b",
        r"\byear[- ]over[- ]year\b",
        r"\bmonth[- ]over[- ]month\b",
        r"\bquarter[- ]over[- ]quarter\b",
        r"\bfrom\s+last\b",
        r"\bsince\s+last\b",
        r"\bthan\s+before\b",
        r"\bthan\s+previously\b",
    ]

    # ==================================================
    # DOCUMENT REFERENCE PATTERNS
    # ==================================================

    DOCUMENT_PATTERNS = [
        r"\bdocuments?\b",
        r"\breports?\b",
        r"\bfiles?\b",
        r"\brecords?\b",
        r"\bperiods?\b",
    ]

    # ==================================================
    # MAIN DETECTION
    # ==================================================

    def detect(
        self,
        question,
    ):
        """
        Determine whether the question requires
        historical or cross-document context.

        Returns:

            {
                "is_historical": bool,
                "reason": str,
                "signals": list[str]
            }
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        text = question.strip().lower()

        signals = []

        # ----------------------------------------------
        # Check historical/comparative patterns
        # ----------------------------------------------

        for pattern in self.HISTORICAL_PATTERNS:

            if re.search(
                pattern,
                text,
            ):
                signals.append(
                    pattern
                )

        # ----------------------------------------------
        # Check document references
        # ----------------------------------------------

        document_reference = False

        for pattern in self.DOCUMENT_PATTERNS:

            if re.search(
                pattern,
                text,
            ):
                document_reference = True
                break

        # ----------------------------------------------
        # Determine classification
        # ----------------------------------------------

        if signals:
            return {
                "is_historical": True,
                "reason": "historical_or_comparative_language",
                "signals": signals,
            }

        if document_reference:
            return {
                "is_historical": True,
                "reason": "cross_document_reference",
                "signals": [],
            }

        return {
            "is_historical": False,
            "reason": "current_document_question",
            "signals": [],
        }

    # ==================================================
    # SIMPLE BOOLEAN INTERFACE
    # ==================================================

    def is_historical(
        self,
        question,
    ):
        """
        Return only the historical classification.
        """

        result = self.detect(
            question
        )

        return result[
            "is_historical"
        ]