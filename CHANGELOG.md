# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/USERNAME/theremia-rag/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/USERNAME/theremia-rag/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/USERNAME/theremia-rag/releases/tag/v0.0.1