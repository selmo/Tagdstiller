# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI app (`main.py`), API `routers/`, business `services/`, `db/` models/migrations, `extractors/`, and `tests/`. SQLite file: `backend/docextract.db`.
- `frontend/`: React + TypeScript app (`src/`, `public/`).
- `scripts/`: Helpers to start/stop services (`start_backend.sh`, `start_frontend.sh`, `start_all.sh`).
- `test/`: CLI scripts and sample files for parser checks.
- Docs & guides: `docs/`, `README.md`, `LOCAL_ANALYSIS_USAGE.md`.

## Build, Test, and Development Commands
- Backend env: Conda recommended (see `CLAUDE.md`).
- Run backend (dev, port 8001): `./scripts/start_backend.sh`
- Manual backend: `uvicorn backend.main:app --reload --port 8001`
- Frontend setup: `cd frontend && npm install`
- Run frontend (dev, port 3001): `./scripts/start_frontend.sh`
- Full system (FE + BE): `./scripts/start_all.sh`
- Backend tests: `cd backend && pytest -v`
- API/integration tests: `bash test/test_local_analysis.sh`, `bash test/test_all_parsers.sh`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent; `snake_case` for functions/vars, `PascalCase` for classes. Prefer type hints and docstrings for public functions.
- TypeScript/React: `PascalCase` components (e.g., `ProjectCard.tsx`), `camelCase` functions/vars; colocate component styles/assets in `src/`.
- Keep modules cohesive: API routes in `backend/routers/`, business logic in `backend/services/`, DB models in `backend/db/`.

## Testing Guidelines
- Framework: `pytest` (configured via `backend/pytest.ini`, discovery under `backend/tests/`).
- Naming: files `test_*.py`, functions `test_*`.
- Run: `cd backend && pytest -v --tb=short`.
- Integration samples live in `test/`; regenerate artifacts by re-running the scripts above.

## Commit & Pull Request Guidelines
- Commits: clear, imperative mood with optional scope. Example: `feat(extraction): add Docling metadata parser`. Link issues with `#123`.
- PRs: include summary, rationale, testing steps, affected endpoints/UX, and screenshots or logs when relevant.
- Keep changes focused and incremental; avoid unrelated refactors.

## Security & Configuration Tips
- Do not commit secrets. Use `.env.local` (frontend) and environment variables for backend settings.
- CORS and DB defaults: see `backend/main.py` and `backend/db/`. Back up `backend/docextract.db` before schema changes.
