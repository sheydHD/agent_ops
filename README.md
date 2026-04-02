# AgentOps

A fully local RAG (Retrieval-Augmented Generation) pipeline with end-to-end LLM observability. Every inference call, retrieval step, and routing decision is traced to **Langfuse** and evaluated by **Arize Phoenix** — all running on your machine with zero cloud dependencies.

## Architecture

```
┌──────────────┐     ┌──────────────────────────────────────────────┐
│   Next.js    │────▶│  FastAPI Backend                             │
│   Chat UI    │◀────│                                              │
│  :3501       │     │  ┌────────────┐   ┌──────────┐   ┌────────┐  │
└──────────────┘     │  │Orchestrator│──▶│ RAG Agent│──▶│ Ollama │  │
                     │  │(semantic   │   │ (LCEL)   │   │ :11434 │  │
                     │  │ routing)   │   └──────────┘   └────────┘  │
                     │  └─────┬──────┘                              │
                     │        │                                     │
                     │  ┌─────▼──────┐                              │
                     │  │ ChromaDB   │                              │
                     │  │ (vectors)  │                              │
                     │  └────────────┘                              │
                     │                                              │
                     │  ┌──────────────────────────────────┐        │
                     │  │ OpenTelemetry (shared provider)  │        │
                     │  │  ├─▶ Langfuse v3  :3100          │        │
                     │  │  └─▶ Arize Phoenix :6006         │        │
                     │  └──────────────────────────────────┘        │
                     └──────────────────────────────────────────────┘
```

**Key components:**

| Service | Role | Port |
|---------|------|------|
| **Backend** | FastAPI + LangChain LCEL RAG pipeline | `8501` |
| **Frontend** | Next.js 14 chat interface | `3501` |
| **Langfuse v3** | Trace viewer, prompt management, scoring | `3100` |
| **Arize Phoenix** | Evaluation dashboard, span annotations | `6006` |
| **Ollama** | Local LLM inference (runs on host) | `11434` |
| **ChromaDB** | Vector store (embedded, persisted) | — |
| **PostgreSQL 17** | Langfuse persistence | `5433` |
| **ClickHouse 24** | Langfuse v3 analytics | `8123` |
| **Redis 7** | Langfuse background job queue | `6379` |
| **MinIO** | S3-compatible store for Langfuse media | — |

## Prerequisites

- **Docker** & **Docker Compose** v2+
- **Ollama** installed and running on the host (`ollama serve`)
- ~16 GB RAM recommended (Ollama + Docker services)

## Quickstart

```bash
# 1. Clone the repository
git clone git@github.com:sheydHD/agent_ops.git
cd agent_ops

# 2. Copy environment file
cp .env.example .env

# 3. Pull required Ollama models
make setup-models
# Or manually:
#   ollama pull qwen2.5:14b
#   ollama pull nomic-embed-text

# 4. Start all services
make up
```

On first run, wait ~2 minutes for Langfuse to initialize its database.

### Post-setup

1. Open **Langfuse** at [http://localhost:3100](http://localhost:3100) and create an account
2. Create a project and copy the **Public Key** and **Secret Key**
3. Update `.env` with your keys:
   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```
4. Restart the backend: `make restart-backend`
5. Open the chat UI at [http://localhost:3501](http://localhost:3501)

## How It Works

### Semantic Routing

The orchestrator classifies every incoming query:

1. Performs a similarity search against ChromaDB
2. If top-k results exceed the relevance threshold → **RAG path** (inject retrieved context)
3. Otherwise → **General path** (direct LLM response)

Pre-fetched documents are passed downstream to avoid redundant retrieval.

### Observability

A single OpenTelemetry `TracerProvider` with two OTLP exporters sends identical span data to both backends:

- **Langfuse**: Traces, sessions, user tracking, prompt management, numeric scoring
- **Phoenix**: Span annotations, evaluation labels, quality metrics

Every response includes direct links to its trace in both dashboards.

### Automated Scoring & Evaluation

Each request is automatically scored:

- **Retrieval quality** (RAG path): measures how many relevant docs were retrieved
- **Routing confidence** (General path): validates the routing decision
- **Response completeness**: answer length heuristic
- **Faithfulness** (RAG path): LLM-as-judge background evaluation that checks if the answer is faithful to the retrieved context

Users can also submit thumbs-up/down feedback from the chat UI, which is recorded as a Langfuse score.

### Prompt Management

Prompts can be managed in the Langfuse UI and selected from the chat interface dropdown. The backend fetches prompt templates via the Langfuse SDK at query time.

## Project Structure

```
agent_ops/
├── apps/
│   ├── backend/                # FastAPI + LangChain RAG pipeline
│   │   ├── src/
│   │   │   ├── agents/         # Orchestrator + RAG agent (LCEL)
│   │   │   ├── api/            # Routes (chat, health, prompts) + middleware
│   │   │   ├── config/         # Settings (pydantic) + logging
│   │   │   └── services/       # LLM, RAG, telemetry, Langfuse prompts
│   │   ├── tests/              # pytest test suite
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/               # Next.js 14 chat UI
│       ├── src/
│       │   ├── components/     # Chat interface components
│       │   ├── hooks/          # useChat hook
│       │   ├── services/       # API client (axios)
│       │   └── types/          # TypeScript interfaces
│       └── Dockerfile
├── data/                       # Documents for RAG ingestion (PDF/TXT)
├── docker-compose.yml          # Base: all 8 services
├── docker-compose.override.yml # Dev: ports, volumes, hot-reload
├── Makefile                    # Common commands
└── .env.example                # Environment template
```

## Available Commands

```bash
# Services
make up                # Start all services (dev mode)
make down              # Stop all services
make logs              # Follow all logs
make logs-backend      # Follow backend logs only
make health            # Backend health check
make setup-models      # Pull required Ollama models
make rebuild           # Rebuild containers (no cache)
make restart-backend   # Restart backend only
make restart-frontend  # Restart frontend only
make restart-apps      # Restart backend + frontend
make clean             # Remove all volumes (full reset)

# Code Quality
make lint              # Run all linters (backend + frontend)
make format            # Format all code (backend + frontend)
make typecheck         # Run all type checks (mypy + tsc)
make check             # Run all checks (lint + format + typecheck) — CI equivalent

# Testing
make test              # Run all tests
make test-backend      # Run backend tests only

# Pre-commit
make pre-commit-install # Install pre-commit hooks
make pre-commit         # Run pre-commit on all files
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a message, receive RAG-augmented response |
| `POST` | `/api/feedback` | Submit thumbs-up / thumbs-down for a trace |
| `POST` | `/api/admin/dataset` | Add a trace to a Langfuse evaluation dataset |
| `GET` | `/api/prompts` | List available Langfuse-managed prompts |
| `GET` | `/health` | Service health check (Ollama, ChromaDB, Langfuse, Phoenix) |
| `GET` | `/docs` | Interactive API documentation (Swagger UI) |

### `POST /api/chat`

```json
{
  "message": "What are aerogels?",
  "conversation_id": "optional-session-id",
  "user_id": "optional-user-id",
  "prompt_name": "optional-langfuse-prompt"
}
```

Response includes the answer, source documents, routing metadata, token metrics, per-document relevance scores, and direct trace URLs.

### `POST /api/feedback`

```json
{
  "trace_id": "abc123...",
  "sentiment": "positive",
  "comment": "optional comment"
}
```

Records user feedback as a Langfuse score on the trace.

## Running Tests

```bash
# Backend tests (from project root)
make test-backend

# Or manually:
cd apps/backend
pip install -r requirements-dev.txt
pytest tests/ -v

# Frontend (lint + typecheck)
cd apps/frontend
pnpm lint
pnpm typecheck

# Run all code quality checks at once
make check
```

## Configuration

All configuration is via environment variables. See [`.env.example`](.env.example) for the full list.

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `qwen2.5:14b` | Ollama model for inference |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `RELEVANCE_THRESHOLD` | `0.7` | Semantic routing cutoff (0–1) |
| `LANGFUSE_PUBLIC_KEY` | — | From Langfuse project settings |
| `LANGFUSE_SECRET_KEY` | — | From Langfuse project settings |
| `PHOENIX_ENABLED` | `true` | Enable/disable Phoenix |
| `FAITHFULNESS_EVAL_ENABLED` | `true` | Enable LLM-as-judge faithfulness evaluation |
| `LANGFUSE_DATASET_NAME` | `agentops-demo` | Default dataset name for evaluation items |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LOG_FORMAT` | `text` | `text` for dev, `json` for production |

## Adding Documents

Drop `.txt` or `.pdf` files into the `data/` directory. The backend ingests them into ChromaDB on startup if the vector store is empty. To re-ingest, run `make clean` then `make up`.

## License

MIT
