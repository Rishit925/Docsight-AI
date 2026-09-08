# Docsight AI

<p align="center">
  <strong>Multimodal Document Intelligence & Retrieval-Augmented Generation Platform</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/Qdrant-FF3B30?style=for-the-badge&logo=qdrant&logoColor=white" alt="Qdrant">
  <img src="https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Google_Cloud_Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Google Cloud Run">
  <img src="https://img.shields.io/badge/Cloudflare-F38020?style=for-the-badge&logo=cloudflare&logoColor=white" alt="Cloudflare">
</p>

<p align="center">
  <a href="https://docsight-ai.rishitmahindru218.workers.dev">Live Demo</a>
  &nbsp;•&nbsp;
  <a href="https://github.com/Rishit925/Docsight-AI">GitHub Repository</a>
  &nbsp;•&nbsp;
  <a href="https://docsight-api-683710113441.europe-west3.run.app">Backend API</a>
</p>

---

## Overview

Docsight AI is a full-stack multimodal document intelligence application built around Retrieval-Augmented Generation (RAG).

It allows users to upload PDF documents, extract and understand their content, ask context-aware questions, compare documents, maintain conversational context, and access page-level sources for generated answers.

The system combines document processing, local embeddings, semantic retrieval, reranking, query routing, multimodal analysis, conversational memory, and LLM-based generation into a single application.

## Features

- 📄 Multimodal PDF ingestion with text, table, and image extraction
- 🔍 RAG-based question answering
- 🧠 Local semantic embeddings using `all-MiniLM-L6-v2`
- 🎯 Semantic retrieval and reranking
- 🧭 Query routing
- 💬 Conversational memory for follow-up questions
- 📊 Multi-document comparison
- 🔗 Page-level source citations with direct PDF links
- 📁 Document upload, history, processing, and deletion
- ☁️ Persistent cloud storage
- ⚡ Cloud-based vector search

## Tech Stack

| Category | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, Axios |
| Backend | Python, FastAPI |
| Embeddings | Sentence Transformers, `all-MiniLM-L6-v2` |
| Retrieval | RAG, Semantic Search, Reranking, Query Routing |
| Text Generation | Google Gemini |
| Multimodal Analysis | OpenAI |
| Document Processing | PDF Text, Table & Image Extraction |
| Database | PostgreSQL via Supabase |
| File Storage | Supabase Storage |
| Vector Database | Qdrant Cloud |
| Containerization | Docker |
| Backend Deployment | Google Cloud Run |
| Frontend Deployment | Cloudflare Workers |

## Architecture

### System Diagram

```text
                     ┌──────────────────────┐
                     │    React + Vite       │
                     │      Cloudflare       │
                     └──────────┬────────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │       FastAPI         │
                     │    Google Cloud Run   │
                     └──────────┬────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │ Qdrant Cloud │      │   Supabase    │      │ AI Providers │
   │ Vector Store │      │ PostgreSQL + │      │ Gemini +     │
   │              │      │   Storage    │      │ OpenAI       │
   └──────────────┘      └──────────────┘      └──────────────┘
```

### Data / Request Flow

```text
PDF Upload
    ↓
Text / Tables / Images Extraction
    ↓
Document Processing
    ↓
Chunking + Local Embeddings
    ↓
Qdrant Vector Search
    ↓
Query Routing
    ↓
Semantic Retrieval + Reranking
    ↓
Relevant Context
    ↓
Gemini Generation
    ↓
Answer + Source Citations
```

### Deployment Flow

```text
Cloudflare Workers
        │
        ▼
React + Vite Frontend
        │
        ▼
Google Cloud Run
        │
        ├── FastAPI Backend
        ├── Supabase PostgreSQL
        ├── Supabase Storage
        ├── Qdrant Cloud
        ├── Google Gemini
        └── OpenAI
```

## Core Capabilities

### Multimodal Understanding

Docsight AI goes beyond text-only document processing by extracting relevant images from PDFs and using OpenAI multimodal analysis when visual information is important. This allows the system to work with information contained in:

- Charts
- Diagrams
- Scanned sections
- Visual layouts
- Embedded document images

### Conversational Memory

The application maintains document-specific conversation context, allowing users to ask follow-up questions without repeatedly providing previous information.

### Document Comparison

Docsight AI can analyze multiple documents together and generate structured comparisons highlighting relevant similarities, differences, changes, and findings.

### Source Grounding

Generated answers can include page-level document sources. Users can open a source directly from the application and navigate to the corresponding page of the original PDF.

## Project Structure

```text
Docsight-AI/
│
├── app/
│   ├── api/              # FastAPI routes and API layer
│   ├── ingestion/        # Document extraction and processing
│   ├── retrieval/        # Retrieval, reranking and query routing
│   ├── generation/       # LLM generation
│   ├── memory/           # Conversational memory
│   ├── services/         # Core application services
│   └── ...
│
├── frontend/
│   ├── src/              # React application
│   ├── public/
│   └── package.json
│
├── tests/                # Application tests
├── data/                 # Local development data
├── vectorstore/          # Local vector storage
├── Dockerfile            # Backend container configuration
├── requirements.txt      # Python dependencies
├── .env.example          # Environment configuration template
└── .gitignore
```

## Links

| Resource | URL |
|---|---|
| Live Demo | [docsight-ai.rishitmahindru218.workers.dev](https://docsight-ai.rishitmahindru218.workers.dev) |
| Backend API | [docsight-api-683710113441.europe-west3.run.app](https://docsight-api-683710113441.europe-west3.run.app) |
| GitHub Repository | [github.com/Rishit925/Docsight-AI](https://github.com/Rishit925/Docsight-AI) |