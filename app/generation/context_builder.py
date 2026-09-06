class ContextBuilder:
    """Builds structured context for the LLM."""

    def build(self, retrieved_chunks):
        """
        Convert retrieved chunks into structured context.
        """

        if not retrieved_chunks:
            return "No relevant information was found."

        context_parts = []

        for index, chunk in enumerate(
            retrieved_chunks,
            start=1,
        ):
            metadata = chunk["metadata"]

            source = metadata["source"]
            page = metadata["page_number"]
            content_type = metadata["content_type"]

            context_parts.append(
                f"""
SOURCE {index}
Document: {source}
Page: {page}
Content Type: {content_type}

Content:
{chunk["content"]}
"""
            )

        return "\n".join(context_parts)