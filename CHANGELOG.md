# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** v0.2.0 was skipped — v0.3.0 covers the service layer refactor.

## [Unreleased]

## [0.4.0] — 2026-03-06

### Added
- Frontend JWT auth: login/register pages, route guard, auto-login after registration
- Zustand store with `persist` for token + user (localStorage)
- Axios interceptors: Bearer token injection on every request, auto-redirect on 401
- Toast notification system (`useToast`) replacing all `alert()` calls
- Logout button in Sidebar (bottom, with hover red state)

### Changed
- Docker set as recommended Quick Start option (Option 1)
- Default LLM provider changed to OpenAI (`gpt-4o-mini`)
- RAG parameters updated: `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `RETRIEVAL_K=5`
- Backend Dockerfile: BuildKit pip cache mount — first build slow (~20min), subsequent builds fast
- `openai` bumped to `1.57.0` to fix `proxies` conflict with `httpx`
- `httpx` pinned to `0.27.2` for stability
- RAG system prompt loosened: responds with partial context instead of refusing
- `.env.example` and `.env.docker` updated with correct defaults and OS-specific Ollama URLs
- README: Docker-first quick start, build time warnings, Makefile commands updated

### Fixed
- LLM model name not displayed correctly in chat messages
- PDF `onDropRejected` callback crashing without toast system
- Docker volume `driver: localx` typo causing container startup failure
- French comments in `docker-compose.yml` translated to English

## [0.3.0] — 2026-03-04

### Added
- GitHub Actions CI: lint (ruff, ESLint) on every push and PR
- Multi-provider LLM support: OpenAI, OpenRouter, Ollama — switchable via `LLM_PROVIDER` env var
- Multi-provider embeddings: OpenAI (`text-embedding-3-small`) and HuggingFace (`all-MiniLM-L6-v2`)
- Model selection UI: dropdown in chat to switch models per conversation
- Cost and token tracking aggregated per conversation

### Changed
- Full service layer refactor: Routes → Services → Repositories (no SQLAlchemy in routes)
- Single `commit()` per service method with explicit `rollback()` on failure
- N+1 prevention: `list_conversations` uses 2 queries instead of N+1
- Background PDF ingestion: upload returns immediately, indexing runs as `BackgroundTask`
- Provider abstraction: swapping LLM/embeddings touches only `rag_service.py` and `.env`

## [0.1.0] — 2026-03-01

### Added
- JWT authentication: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- User model with bcrypt password hashing
- Alembic migrations: `users` table, `user_id` FK on `documents` and `conversations`
- Full user isolation: all resources (documents, conversations, messages) scoped to authenticated user
- Security middleware: HTTP security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- In-memory rate limiting: 20 req/min on RAG endpoints, 10 req/min on uploads
- PDF magic bytes validation + filename sanitization on upload
- Input sanitization: control character stripping, model whitelist, document_ids deduplication
- Frontend base: React + Vite + TailwindCSS + TanStack Query + Zustand
- Chat UI with conversation management, document selection, cost/token tracking
- Documents UI with drag-and-drop upload, status polling, delete

### Changed
- CORS: explicit methods/headers instead of wildcards
- Swagger UI disabled in production (`DEBUG=false`)
- `init_db()` no longer calls `create_all` — schema managed by Alembic

### Security
- All API routes require `Authorization: Bearer <token>` header
- Ownership enforced on every route with `{id}` parameter (GET/PATCH/DELETE)
- JWT secret configurable via `JWT_SECRET_KEY` env var

## [0.0.1] — 2026-02-28

### Added
- Initial RAG API: FastAPI + LangChain + ChromaDB + OpenAI
- Document ingestion (PDF → chunks → embeddings → ChromaDB)
- Conversational Q&A with source citations
- Model selection (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo)
- Cost and token tracking per message and conversation
- Docker Compose setup with health checks and persistent volumes
- SQLite database with SQLAlchemy async

[Unreleased]: https://github.com/KMAit/theremia-rag/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/KMAit/theremia-rag/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/KMAit/theremia-rag/compare/v0.1.0...v0.3.0
[0.1.0]: https://github.com/KMAit/theremia-rag/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/KMAit/theremia-rag/releases/tag/v0.0.1