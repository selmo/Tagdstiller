# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI app (`main.py`), domain `routers/`, `services/`, `db/`, `extractors/`, and `tests/`. SQLite file: `backend/docextract.db`.
- `frontend/`: React + TypeScript app (`src/`, `public/`).
- `scripts/`: Helpers to start/stop services (`start_backend.sh`, `start_frontend.sh`, `start_all.sh`).
- `test/`: CLI test scripts and sample files for parsers.
- `docs/` and top-level guides (`README.md`, `LOCAL_ANALYSIS_USAGE.md`).

## Build, Test, and Development Commands
- Backend setup: Conda environment recommended (see CLAUDE.md for full setup)
- Run backend (dev): `./scripts/start_backend.sh` (포트 8001)
- Frontend setup: `cd frontend && npm install`
- Run frontend (dev): `./scripts/start_frontend.sh` (포트 3001)
- Full system: `./scripts/start_all.sh` (백엔드 + 프론트엔드 동시 실행)
- Backend tests: `cd backend && pytest -v`
- API tests: `bash test/test_local_analysis.sh`, `bash test/test_all_parsers.sh`
- Manual backend start: `uvicorn backend.main:app --reload --port 8001`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent; `snake_case` for functions/vars, `PascalCase` for classes; prefer type hints and docstrings for public functions.
- TypeScript/React: `PascalCase` components (`ProjectCard.tsx`), `camelCase` functions/vars; colocate component styles/assets in `src/`.
- Keep modules cohesive: API routes in `backend/routers/`, business logic in `backend/services/`, DB models in `backend/db/`.

## Testing Guidelines
- Framework: `pytest` (configured via `backend/pytest.ini`, test discovery under `backend/tests/`).
- Naming: `test_*.py`, functions `test_*`.
- Run: `cd backend && pytest -v --tb=short`.
- Integration samples in `test/` provide CLI checks and example fixtures; regenerate artifacts by re-running the scripts.

## Commit & Pull Request Guidelines
- Commits: clear, imperative mood, scope when helpful. Example: `feat(extraction): add Docling metadata parser`.
- Link issues with `#123` when applicable. Keep changes focused and incremental.
- PRs: include summary, rationale, testing steps, affected endpoints/UX, and screenshots or logs when relevant.

## Security & Configuration Tips
- Do not commit secrets. Use `.env.local` (frontend) and environment variables for backend settings.
- CORS and DB defaults are in `backend/main.py`/`backend/db`; adjust for deployments. Back up `backend/docextract.db` before schema changes.
