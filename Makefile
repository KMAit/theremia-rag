.PHONY: dev build up down logs clean setup

# ── Development (local) ──────────────────────────────────────────────────────

setup:
	@echo "→ Setting up backend..."
	cd backend && cp -n .env.example .env || true
	cd backend && pip install -r requirements.txt
	@echo "→ Setting up frontend..."
	cd frontend && npm install
	@echo "✓ Done. Edit backend/.env with your OPENAI_API_KEY, then run: make dev"

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "→ Starting backend & frontend in parallel..."
	$(MAKE) -j2 dev-backend dev-frontend

# ── Docker ───────────────────────────────────────────────────────────────────

build:
	docker compose build

up:
	docker compose up -d
	@echo "✓ App running at http://localhost:3000"
	@echo "  API docs at  http://localhost:8000/docs"

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v
	rm -rf backend/theremia.db backend/chroma_db backend/uploads
