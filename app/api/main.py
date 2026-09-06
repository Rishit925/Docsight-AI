from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.documents import router as documents_router
from app.api.routes.questions import router as questions_router
from app.api.routes.health import router as health_router
from app.api.routes.conversations import router as conversations_router


app = FastAPI(
    title="Docsight AI",
    description=(
        "Multimodal document intelligence and "
        "retrieval-augmented question answering API."
    ),
    version="1.0.0",
)


# ==================================================
# CORS
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():
    """
    Basic API information endpoint.
    """

    return {
        "status": "ok",
        "service": "docsight-api",
        "message": "Docsight AI API is running.",
    }


# ==================================================
# HEALTH
# ==================================================

app.include_router(
    health_router,
)


# ==================================================
# DOCUMENTS
# ==================================================

app.include_router(
    documents_router,
    prefix="/api",
    tags=["Documents"],
)


# ==================================================
# QUESTIONS
# ==================================================

app.include_router(
    questions_router,
    prefix="/api",
    tags=["Questions"],
)


# ==================================================
# CONVERSATIONS
# ==================================================

app.include_router(
    conversations_router,
    prefix="/api",
    tags=["Conversations"],
)