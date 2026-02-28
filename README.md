# Theremia — Document Intelligence Platform

A production-ready fullstack RAG application: upload PDF documents and chat with them through an AI-powered conversational interface.

**Stack:** FastAPI · React · LangChain · ChromaDB · OpenAI · SQLite · Docker

---

## Features

### Core
- **Document management** — Upload PDFs, track indexing status (processing → ready), view metadata (pages, chunks, size), delete with vector cleanup
- **Conversational Q&A** — Chat interface with full message history, markdown rendering, loading states
- **Multi-conversation** — Create, switch, rename, delete conversations; auto-titled from first question
- **REST API** — Clean versioned API (`/api/v1/...`) with Pydantic validation and proper HTTP status codes

### Bonus implemented
- **Source citations** — Every AI answer shows the exact document chunks retrieved, with relevance score and page number
- **Model selection** — Switch between GPT-4o, GPT-4o Mini, GPT-4 Turbo, GPT-3.5 Turbo per conversation
- **Cost tracking** — Token usage and USD cost tracked per message and aggregated per conversation, displayed in real time
- **Document scoping** — Each conversation can target a specific subset of documents

---

## Quick Start

### Option 1 — Docker (recommended)

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/theremia-rag.git
cd theremia-rag

# 2. Configure
cp backend/.env.example backend/.env
# Edit backend/.env and add your OpenAI API key:
# OPENAI_API_KEY=sk-...

# 3. Run
docker compose up --build

# App:  http://localhost:3000
# API:  http://localhost:8000/docs
```

### Option 2 — Local development

**Prerequisites:** Python 3.12+, Node.js 20+

```bash
# Setup everything at once
make setup

# Edit backend/.env and add OPENAI_API_KEY=sk-...

# Run backend + frontend in parallel
make dev

# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```

Or manually:

```bash
# Backend
cd backend
cp .env.example .env    # then add your OPENAI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | Your OpenAI API key |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./theremia.db` | Async SQLite URL |
| `CHROMA_PERSIST_DIR` | No | `./chroma_db` | ChromaDB storage path |
| `UPLOAD_DIR` | No | `./uploads` | PDF upload directory |
| `DEFAULT_LLM_MODEL` | No | `gpt-4o-mini` | Default LLM model |
| `ALLOWED_ORIGINS` | No | `["http://localhost:5173"]` | CORS origins |
| `MAX_FILE_SIZE_MB` | No | `50` | Max upload size |
| `CHUNK_SIZE` | No | `1000` | RAG chunk size in tokens |
| `RETRIEVAL_K` | No | `5` | Top-K chunks retrieved |
| `DEBUG` | No | `false` | SQLAlchemy echo |

---

## API Reference

Full interactive docs at `http://localhost:8000/docs` (Swagger UI).

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents` | Upload PDF (multipart) |
| `GET` | `/api/v1/documents` | List all documents |
| `GET` | `/api/v1/documents/{id}` | Get document details |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + vectors |
| `POST` | `/api/v1/conversations` | Create conversation |
| `GET` | `/api/v1/conversations` | List conversations |
| `PATCH` | `/api/v1/conversations/{id}` | Update title/model/docs |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation |
| `GET` | `/api/v1/conversations/{id}/messages` | Get message history |
| `POST` | `/api/v1/conversations/{id}/messages` | Ask question (RAG) |
| `GET` | `/api/v1/conversations/models` | Available LLM models |
| `GET` | `/api/v1/health` | Health check |

---

## Architecture

```
theremia-rag/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app + lifespan
│       ├── core/
│       │   ├── config.py        # Pydantic Settings
│       │   └── database.py      # Async SQLAlchemy engine
│       ├── models/
│       │   ├── document.py      # SQLAlchemy ORM
│       │   ├── conversation.py  # ORM: Conversation + Message
│       │   └── schemas.py       # Pydantic request/response
│       ├── services/
│       │   └── rag_service.py   # LangChain + ChromaDB logic
│       └── api/routes/
│           ├── documents.py
│           ├── conversations.py
│           ├── messages.py      # RAG query endpoint
│           └── health.py
│
└── frontend/src/
    ├── components/
    │   ├── layout/Sidebar.tsx   # Nav + conversation list
    │   ├── chat/ChatPage.tsx    # Chat UI + sources
    │   └── documents/DocumentsPage.tsx
    ├── lib/
    │   ├── api.ts               # Axios API client
    │   └── utils.ts
    ├── store/index.ts           # Zustand global state
    └── types/index.ts           # TypeScript interfaces
```

### Key design decisions

**Backend:**
- **Async throughout** — `asyncio`, `aiosqlite`, `aiofiles` for non-blocking I/O. Document ingestion runs as a FastAPI `BackgroundTask` so uploads return immediately.
- **SQLite + ChromaDB** — Simple, zero-infra persistence. Production upgrade path: swap SQLite for Postgres, ChromaDB for Qdrant.
- **RAG as a service** — `rag_service.py` is cleanly isolated. Swapping LangChain for LlamaIndex, or ChromaDB for another vector store, touches only this file.
- **Per-conversation document scoping** — Collections are per-document, retrieved and merged at query time. Enables conversations to target specific document subsets.
- **Cost tracking** — OpenAI token usage from `response_metadata` is captured per message and aggregated on the conversation.

**Frontend:**
- **TanStack Query** — Server state is managed via React Query (caching, background refetch, polling for `processing` docs).
- **Zustand** — Minimal global state (active conversation, sidebar open). Avoids prop drilling without Redux overhead.
- **Optimistic UX** — Upload progress via axios `onUploadProgress`. Processing documents auto-refetch every 2s until ready.
- **Collapsible sidebar** — Stays out of the way on smaller screens.

---

## Makefile Commands

```bash
make setup          # Install all dependencies
make dev            # Run backend + frontend concurrently
make up             # Start Docker stack
make down           # Stop Docker stack
make logs           # Tail Docker logs
make clean          # Remove Docker volumes + local data
```
