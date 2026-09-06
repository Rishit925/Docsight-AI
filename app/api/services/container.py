from app.embeddings.embedding_service import EmbeddingService
from app.vectorstore.chroma_store import ChromaStore

from app.api.services.document_service import (
    DocumentService,
)

from app.retrieval.retriever import Retriever


# ==================================================
# SHARED EMBEDDING SERVICE
# ==================================================

embedding_service = EmbeddingService()


# ==================================================
# SHARED VECTOR STORE
# ==================================================

vector_store = ChromaStore()


# ==================================================
# SHARED RETRIEVER
# ==================================================

retriever = Retriever(
    embedding_service=embedding_service,
    vector_store=vector_store,
)


# ==================================================
# SHARED DOCUMENT SERVICE
# ==================================================

document_service = DocumentService(
    embedding_service=embedding_service,
    vector_store=vector_store,
)