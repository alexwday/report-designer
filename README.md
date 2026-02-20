# Report Designer

LLM-powered document generation tool for Canadian bank financial reports. Uses MCP (Model Context Protocol) to expose data retrievers as tools.

## Quick Start

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you plan to use Postgres mode, also install:

```bash
pip install -r requirements-postgres.txt
```

### 2) Create `.env` from `.env.example`

```bash
cp .env.example .env
```

Set required values in `.env`:

- `OPENAI_API_KEY`, or OAuth settings (`OAUTH_URL`, `CLIENT_ID`, `CLIENT_SECRET`, `AZURE_BASE_URL`)
- Database mode:
  - Default/self-contained: `DB_BACKEND=sqlite` (auto-creates local DB, seeds mock datasets, and includes the prebuilt `Advanced Multi-Lens Banking Intelligence Playbook` template on startup)
  - Optional external DB: `DB_BACKEND=postgres` plus `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`

Optional LLM runtime overrides (env-only):

- `AGENT_MODEL`: override model in local/API-key mode
- `AGENT_MODEL_OAUTH`: override model in OAuth mode
- `AGENT_MAX_TOKENS`: pass `max_tokens` on local/API-key calls
- `AGENT_MAX_TOKENS_OAUTH`: pass `max_tokens` on OAuth calls

### 3) Run the server

```bash
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 42110
```

### 4) Run the frontend (separate terminal)

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 42174
```

Then open `http://127.0.0.1:42174` in your browser. API docs are at `http://127.0.0.1:42110/api/v1/docs`.

### 5) Optional data bootstrap

```bash
# Only needed for Postgres mode (sqlite auto-seeds on startup)
python scripts/database/load_data.py
python scripts/database/seed_registry.py
```

## Project Structure

```
schemas/           SQL table definitions
scripts/database/  Database setup and data generation
src/               Application code (MCP server, retrievers)
docs/              Documentation
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and data models
- [TODO](docs/TODO.md) - Project roadmap and progress
