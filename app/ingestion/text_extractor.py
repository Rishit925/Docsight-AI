class TextExtractor:
    """Extracts text from each page of a PDF."""

    def extract(self, document):
        """
        Extract text page-by-page.

        Returns:
            list: List of dictionaries containing page text and metadata.
        """

        pages = []

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            if not text:
                continue

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                }
            )

        return pages