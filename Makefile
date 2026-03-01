.PHONY: help setup venv env install backend-install frontend-install \
        migrate db-current revision downgrade \
        dev dev-backend dev-frontend \
        build up down logs clean

# ---- Paths / commands
BACKEND_DIR  := backend
FRONTEND_DIR := frontend
VENV_DIR     := $(BACKEND_DIR)/.venv

help:
	@echo "Targets:"
	@echo "  make setup              -> create venv, create .env if missing, install deps"
	@echo "  make dev                -> run backend + frontend in parallel"
	@echo "  make dev-backend        -> run FastAPI locally"
	@echo "  make dev-frontend       -> run Vite locally"
	@echo "  make migrate            -> alembic upgrade head"
	@echo "  make db-current         -> show current alembic revision"
	@echo "  make revision m='msg'   -> create alembic revision"
	@echo "  make downgrade rev='-1' -> downgrade one revision"
	@echo "  make up/down/logs       -> docker compose"
	@echo "  make clean              -> remove db/chroma/uploads + docker volumes"

# ---- Setup
setup: venv env install
	@echo "✓ Setup done. Edit backend/.env with your OPENAI_API_KEY then run: make dev"

venv:
	@set -e; \
	if [ ! -d "$(VENV_DIR)" ]; then \
	    echo "→ Creating venv in $(VENV_DIR)..."; \
	    python3 -m venv "$(VENV_DIR)"; \
	fi; \
	if [ ! -x "$(VENV_DIR)/bin/pip" ]; then \
	    echo "✗ pip not found after venv creation."; \
	    echo "  Try: sudo apt install python3-pip python3.12-venv"; \
	    exit 1; \
	fi; \
	"$(VENV_DIR)/bin/pip" -q install --upgrade pip setuptools wheel

env:
	@set -e; \
	if [ ! -f "$(BACKEND_DIR)/.env" ]; then \
	    echo "→ Creating backend/.env from .env.example"; \
	    cp "$(BACKEND_DIR)/.env.example" "$(BACKEND_DIR)/.env"; \
	fi

backend-install: venv
	@echo "→ Installing backend deps..."
	@"$(VENV_DIR)/bin/pip" install -r "$(BACKEND_DIR)/requirements.txt"

frontend-install:
	@echo "→ Installing frontend deps..."
	@cd "$(FRONTEND_DIR)" && npm install

install: backend-install frontend-install

# ---- DB / Alembic
migrate: venv
	@echo "→ Running migrations..."
	@cd "$(BACKEND_DIR)" && "../$(VENV_DIR)/bin/alembic" -c alembic.ini upgrade head

db-current: venv
	@cd "$(BACKEND_DIR)" && "../$(VENV_DIR)/bin/alembic" -c alembic.ini current

revision: venv
	@test "$(m)" != "" || (echo "Usage: make revision m='your message'"; exit 1)
	@cd "$(BACKEND_DIR)" && "../$(VENV_DIR)/bin/alembic" -c alembic.ini revision -m "$(m)"

downgrade: venv
	@test "$(rev)" != "" || (echo "Usage: make downgrade rev='-1'"; exit 1)
	@cd "$(BACKEND_DIR)" && "../$(VENV_DIR)/bin/alembic" -c alembic.ini downgrade "$(rev)"

# ---- Dev
dev-backend: venv
	@cd "$(BACKEND_DIR)" && "../$(VENV_DIR)/bin/uvicorn" app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@cd "$(FRONTEND_DIR)" && npm run dev

dev:
	@echo "→ Starting backend & frontend in parallel..."
	@$(MAKE) -j2 dev-backend dev-frontend

# ---- Docker
build:
	docker compose build

up:
	docker compose up -d
	@echo "✓ App running at http://localhost:3000"
	@echo "  API docs at http://localhost:8000/docs (only if DEBUG=true)"

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v
	rm -rf "$(BACKEND_DIR)/theremia.db" "$(BACKEND_DIR)/chroma_db" "$(BACKEND_DIR)/uploads"