# Theremia — Document Intelligence Platform (RAG)

Upload PDF documents and chat with them through a conversational interface grounded in your files.

**Default mode:** OpenAI GPT-4o-mini + HuggingFace embeddings
**Stack:** FastAPI · React · LangChain · ChromaDB · SQLite · Docker

---

## Features

- **Document management** — Upload PDFs, track indexing status (`processing → ready`), view metadata (pages, chunks, size), delete with vector cleanup
- **Conversational Q&A** — Chat with your documents, full message history, markdown rendering
- **Multi-conversation** — Create, rename, switch, delete conversations with per-conversation document scoping
- **Source citations** — Every answer shows the exact chunks retrieved, with relevance score
- **Provider switch** — LLM and embeddings providers are configurable: Ollama, OpenAI, OpenRouter, HuggingFace
- **Cost tracking (OpenAI/OpenRouter)** — Token usage and USD cost tracked per message and aggregated per conversation
- **JWT auth** — Stateless authentication, all data isolated per user

---

## Quick Start

### Option 1 — Docker (recommended)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) — nothing else needed.

```bash
git clone https://github.com/KMAit/theremia-rag.git
cd theremia-rag

cp backend/.env.example backend/.env.docker
# Edit backend/.env.docker — set at minimum:
#   OPENAI_API_KEY=sk-...
#   JWT_SECRET_KEY=$(openssl rand -hex 32)

docker compose up --build
```

- App: http://localhost:3000
- API docs: http://localhost:8000/docs

> ⚠️ Docker uses `.env.docker`, not `.env` — paths differ between local and container environments.

> 🐢 **First RAG query will be slow** — HuggingFace downloads the embedding model (~90MB) on first use. Subsequent queries are fast.

> 🐧 Linux only — if you get a Docker permission error: `sudo usermod -aG docker $USER && newgrp docker`

---

### Option 2 — Local dev, OpenAI mode

**Prerequisites:** Python 3.12+, Node.js 20+

```bash
git clone https://github.com/KMAit/theremia-rag.git
cd theremia-rag

make setup
# Edit backend/.env:
#   LLM_PROVIDER=openai
#   OPENAI_API_KEY=sk-...
#   JWT_SECRET_KEY=$(openssl rand -hex 32)

make dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

---

### Option 3 — Local dev, free mode (Ollama)

**Prerequisites:** Python 3.12+, Node.js 20+, [Ollama](https://ollama.com) installed and running.

```bash
ollama pull llama3.1:8b

git clone https://github.com/KMAit/theremia-rag.git
cd theremia-rag

make setup
# Edit backend/.env (see "Environment Variables" below)

make dev
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` (local) or `backend/.env.docker` (Docker) and edit as needed.

### Docker / OpenAI config (recommended)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
DEFAULT_LLM_MODEL=gpt-4o-mini

EMBEDDINGS_PROVIDER=huggingface
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

JWT_SECRET_KEY=change_me_to_a_random_64_char_string
ALLOWED_ORIGINS=["http://localhost:3000"]
```

### free config (Ollama + HuggingFace)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

EMBEDDINGS_PROVIDER=huggingface
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

JWT_SECRET_KEY=change_me_to_a_random_64_char_string
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### OpenRouter config

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_LLM_MODEL=gpt-4o-mini

EMBEDDINGS_PROVIDER=huggingface
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

JWT_SECRET_KEY=change_me_to_a_random_64_char_string
```

### All variables

| Variable | Default                                  | Description |
|---|------------------------------------------|---|
| `LLM_PROVIDER` | `openai`                                 | `openai` · `openrouter` · `ollama` |
| `EMBEDDINGS_PROVIDER` | `huggingface`                                 | `openai` · `huggingface` |
| `OPENAI_API_KEY` | —                                        | Required if `LLM_PROVIDER=openai` |
| `OPENROUTER_API_KEY` | —                                        | Required if `LLM_PROVIDER=openrouter` |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1`           | |
| `OLLAMA_BASE_URL` | `http://localhost:11434`                 | |
| `OLLAMA_MODEL` | `llama3.1:8b`                            | Used when `LLM_PROVIDER=ollama` |
| `DEFAULT_LLM_MODEL` | `gpt-4o-mini`                            | Used when `LLM_PROVIDER=openai` or `openrouter` |
| `DEFAULT_EMBEDDING_MODEL` | `text-embedding-3-small`                 | Used for OpenAI embeddings |
| `HF_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Used for HuggingFace embeddings |
| `JWT_SECRET_KEY` | ⚠️ change me                             | Generate: `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256`                                  | |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                                     | |
| `DATABASE_URL` | `sqlite+aiosqlite:///./theremia.db`      | |
| `CHROMA_PERSIST_DIR` | `./chroma_db`                            | |
| `UPLOAD_DIR` | `./uploads`                              | |
| `MAX_FILE_SIZE_MB` | `50`                                     | |
| `CHUNK_SIZE` | `1000`                                   | RAG chunk size in tokens |
| `CHUNK_OVERLAP` | `200`                                    | |
| `RETRIEVAL_K` | `5`                                      | Top-K chunks retrieved per query |
| `DEBUG` | `false`                                  | Enable dev features |
| `ALLOWED_ORIGINS` | `["http://localhost:5173"]`              | CORS |

---

## API Reference

Full interactive docs at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Get JWT token |
| `POST` | `/api/v1/documents/` | Upload PDF |
| `GET` | `/api/v1/documents/` | List documents |
| `GET` | `/api/v1/documents/{id}` | Get document details |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + vectors |
| `POST` | `/api/v1/conversations/` | Create conversation |
| `GET` | `/api/v1/conversations/` | List conversations |
| `GET` | `/api/v1/conversations/{id}` | Get conversation |
| `PATCH` | `/api/v1/conversations/{id}` | Update title / model / docs |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation |
| `GET` | `/api/v1/conversations/{id}/messages` | Get message history |
| `POST` | `/api/v1/conversations/{id}/messages` | Ask a question (RAG) |
| `GET` | `/api/v1/conversations/models` | List available LLM models |
| `GET` | `/api/v1/health` | Health check |

---

## Architecture

```
theremia-rag/
├── backend/
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── auth.py          # JWT dependency
│       │   ├── config.py        # Pydantic Settings
│       │   ├── database.py      # Async SQLAlchemy engine
│       │   ├── exceptions.py
│       │   └── security.py      # Security headers middleware
│       ├── models/
│       │   ├── conversation.py  # ORM: Conversation + Message
│       │   ├── document.py      # ORM: Document
│       │   ├── user.py          # ORM: User
│       │   └── schemas.py       # Pydantic request/response schemas
│       ├── repositories/        # Data access layer — no commits
│       │   ├── conversation_repository.py
│       │   ├── document_repository.py
│       │   └── message_repository.py
│       ├── services/            # Business logic — owns commit/rollback
│       │   ├── auth_service.py
│       │   ├── conversation_service.py
│       │   ├── document_service.py
│       │   ├── message_service.py
│       │   └── rag_service.py   # LangChain + ChromaDB + provider selection
│       └── api/routes/          # HTTP only — no DB queries, no ORM imports
│           ├── auth.py
│           ├── conversations.py
│           ├── documents.py
│           ├── messages.py
│           └── health.py
│
└── frontend/src/
    ├── components/
    │   ├── auth/                # Login + Register pages
    │   ├── chat/ChatPage.tsx
    │   ├── documents/DocumentsPage.tsx
    │   └── layout/Sidebar.tsx
    ├── hooks/useToast.ts        # Toast notifications
    ├── lib/api.ts               # Axios client + interceptors
    ├── store/index.ts           # Zustand global state (auth + UI)
    └── types/index.ts
```

### Key design decisions

- **Layered architecture** — Routes (HTTP) → Services (business logic + transactions) → Repositories (data access). No SQLAlchemy in routes, no FastAPI in services.
- **Single commit per service method** — Each service method owns exactly one `commit()`, with explicit `rollback()` on failure.
- **N+1 prevention** — `list_conversations` uses 2 queries (conversations + GROUP BY message count) instead of N+1 per conversation.
- **Background ingestion** — PDF upload returns immediately; vector indexing runs as a `BackgroundTask` and updates document status asynchronously.
- **Provider abstraction** — Swapping LLM or embeddings provider touches only `rag_service.py` and `.env`. Routes and services are provider-agnostic.
- **Persistent auth** — JWT token stored via Zustand `persist` (localStorage). Axios interceptors inject Bearer token on every request and redirect to login on 401.

---

## Makefile Commands

```bash
make setup              # Create venv, copy .env if missing, install deps
make dev                # Run backend + frontend in parallel
make dev-backend        # Run FastAPI only
make dev-frontend       # Run Vite only
make migrate            # alembic upgrade head
make revision m='msg'   # Create new alembic migration
make db-current         # Show current migration revision
make downgrade rev='-1' # Downgrade one revision
make up                 # Start Docker stack (detached)
make down               # Stop Docker stack
make logs               # Tail Docker logs
make clean              # Remove local db/chroma/uploads + Docker volumes
```