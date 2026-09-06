from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Creates embeddings using a local Sentence Transformer model."""

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name

        print(f"Loading embedding model: {model_name}")

        self.model = SentenceTransformer(model_name)

        print("Embedding model loaded successfully.")

    def embed_text(self, text: str):
        """Generate an embedding for a single piece of text."""

        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")

        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
        )

        return embedding.tolist()

    def embed_documents(self, texts: list[str]):
        """Generate embeddings for multiple texts."""

        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True,
        )

        return embeddings.tolist()

    def get_dimension(self):
        """Return the size of the embedding vector."""

        return self.model.get_embedding_dimension()