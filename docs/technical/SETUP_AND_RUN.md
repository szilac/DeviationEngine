# Deviation Engine – Setup and Run Guide

This guide covers everything you need to install, configure, and run Deviation Engine from source. If you prefer Docker, see [`docs/DOCKER_SETUP.md`](../DOCKER_SETUP.md).

---

## Prerequisites

### Required

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Python | 3.9+ | 3.11 or 3.12 recommended |
| Node.js | 18+ LTS | |
| npm | 9+ | Comes with Node.js |
| Git | any | |

### API Keys

You need at least one LLM provider key to use the application:

| Provider | Where to get it | Cost |
|----------|----------------|------|
| **Google Gemini** (recommended) | [aistudio.google.com](https://aistudio.google.com/) | Free tier available |
| **OpenRouter** | [openrouter.ai](https://openrouter.ai/) | Pay-per-use |
| **Anthropic Claude** | [console.anthropic.com](https://console.anthropic.com/) | Pay-per-use |
| **OpenAI** | [platform.openai.com](https://platform.openai.com/) | Pay-per-use |

**No API key?** If you already pay for a Claude Pro/Max or OpenAI subscription, see [Section 4.3 CLIProxy Setup](#43-cliproxy-setup-optional) to use it instead.

Optional keys:

| Service | Purpose | Where to get it |
|---------|---------|----------------|
| DeepL | Fast translation | [deepl.com/pro-api](https://www.deepl.com/pro-api) — 500k chars/month free |

---

## 1. Clone the Repository

```bash
git clone https://github.com/szilac/DeviationEngine.git
cd DeviationEngine
```

---

## 2. Backend Setup

### 2.1 Create a Virtual Environment

```bash
cd backend
python3 -m venv venv
```

Activate it:

```bash
# Linux / macOS
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

You should see `(venv)` in your terminal prompt.

### 2.2 Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Download the spaCy Language Model

Required for the **Historical Figure Chat** auto-scan feature:

```bash
python -m spacy download en_core_web_sm
```

This is a one-time download (~12 MB). The application will still start without it, but figure detection will not work.

### 2.4 Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` in a text editor and set your keys. At minimum, add one LLM provider key:

```bash
# Google Gemini (recommended)
GEMINI_API_KEY=your_gemini_api_key_here
DEFAULT_LLM_PROVIDER=google
DEFAULT_LLM_MODEL=gemini-2.5-flash
```

See [Section 5: Full Configuration Reference](#5-full-configuration-reference) for all available options.

---

## 3. Frontend Setup

Open a new terminal in the project root:

```bash
cd frontend
npm install
```

No `.env` file is needed for the frontend — it connects to `http://localhost:8000` by default.

---

## 4. Running the Application

You need two terminals running simultaneously: one for the backend and one for the frontend.

### Terminal 1 — Backend

```bash
cd backend
source venv/bin/activate   # or venv\Scripts\activate on Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend is ready when you see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

The frontend is ready when you see:

```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

### Open the App

Go to **http://localhost:5173** in your browser.

The API documentation (for reference) is available at **http://localhost:8000/docs**.

---

## 4.1 First-Time Setup Steps (Recommended)

After the app is running, do these steps once to unlock the full feature set.

### Index the Vector Store (Smart Search / RAG)

The RAG system needs the historical ground truth data indexed before it can retrieve relevant context efficiently. Without this, the system falls back to legacy full-context mode (higher token usage).

```bash
cd backend
source venv/bin/activate
python scripts/index_ground_truth.py
```

This takes 1–3 minutes and only needs to be done once. To force a re-index:

```bash
python scripts/index_ground_truth.py --force
```

### Verify in the UI

1. Open **Settings → Advanced Configuration → § IV. Debug & Vector Store**.
2. Confirm **Default Context Mode** shows `rag`.
3. Enable **RAG Debug Mode** temporarily to verify retrieval is working (optional).

---

## 4.2 NotebookLM Audio Setup (Optional)

NotebookLM Audio generates natural AI podcast discussions about your timelines using Google's NotebookLM service. This is an optional feature with no additional API key required — it uses your Google account.

### Install the CLI

```bash
pip install notebooklm-cli
```

### Authenticate

```bash
nlm login
```

Follow the browser prompt to sign in with your Google account. Your session is stored locally — you only need to do this once.

### Verify Authentication

```bash
nlm login --check
# Authentication valid!
```

### Enable in the App

1. Open **Settings → Advanced Configuration → § V. Integrations**.
2. Toggle **NotebookLM Podcast Generation**.
3. The **NotebookLM** tab will appear in the Audio Studio on any timeline.

---

## 4.3 CLIProxy Setup (Optional)

CLIProxyAPI is a local proxy that exposes your **Claude Pro/Max** or **OpenAI** subscription as an OpenAI-compatible API. Use this if you already pay for a subscription and want to avoid separate API token costs.

### Install

```bash
# Linux / macOS
bash <(curl -fsSL https://github.com/router-for-me/CLIProxyAPI/releases/latest/download/install.sh)
```

### Authenticate (one-time)

```bash
cliproxyapi --browser-auth
```

Follow the browser prompt. Your session is stored locally.

### Run the proxy

```bash
cliproxyapi
```

The proxy listens on `http://localhost:8317/v1`. Keep it running alongside Deviation Engine.

### Configure in the App

1. Open **Settings** → **Advanced Configuration** → **§ V. Integrations**
2. Toggle **CLIProxy — Subscription API Bridge**
3. Go to **Settings** → **§ I. Language Model** → select **CLIProxy (Subscription)**
4. Pick a model (`claude-sonnet-4-20250514`, `claude-opus-4-20250514`, or `gpt-4o` etc.) and save

To use a non-default URL, set `CLIPROXY_BASE_URL` in `backend/.env`.

> **Note**: Designed for Claude Max. Claude Pro users will work but may hit rate limits under heavy load.

---

## 5. Full Configuration Reference

All configuration lives in `backend/.env`. Copy from `.env.example` as a starting point.

### LLM Provider

```bash
# Set at least one key for your chosen provider
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Provider selection
DEFAULT_LLM_PROVIDER=google          # google | openrouter | anthropic | openai | cliproxy
DEFAULT_LLM_MODEL=gemini-2.5-flash   # see model lists below

# CLIProxy — optional, overrides the default localhost:8317 URL
CLIPROXY_BASE_URL=http://localhost:8317/v1
```

**Google Gemini models:**

| Model | Speed | Quality | Recommended for |
|-------|-------|---------|----------------|
| `gemini-2.5-flash-lite` | Fastest | Good | Skeleton generation, drafts |
| `gemini-2.5-flash` | Fast | Very good | Default, balanced use |
| `gemini-2.5-pro` | Slower | Best | Narratives, high-quality output |

**OpenRouter models (examples):**

- `openai/gpt-4o-mini` — fast and cheap
- `openai/gpt-4o` — high quality
- `anthropic/claude-3.5-sonnet` — strong reasoning

**Anthropic direct models:**

- `claude-sonnet-4-6` — balanced speed and quality
- `claude-opus-4-6` — highest quality
- `claude-haiku-4-5` — fastest, lowest cost

**OpenAI direct models:**

- `gpt-4o-mini` — fast and cheap
- `gpt-4o` — high quality
- `gpt-4.1` — latest generation

**CLIProxy models** (no API key — uses your subscription):

- `claude-sonnet-4-20250514`, `claude-opus-4-20250514`, `claude-haiku-4-5-20251001`
- `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`

See [Section 4.3](#43-cliproxy-setup-optional) for CLIProxy setup.

---

### Generation Settings

```bash
MAX_TOKENS=8192
TEMPERATURE=0.7
```

---

### Server

```bash
API_HOST=localhost
API_PORT=8000
```

---

### Translation (Optional — DeepL)

```bash
DEEPL_API_KEY=your_deepl_api_key_here:fx   # note the :fx suffix for free tier
DEEPL_API_TIER=free                         # free | pro
DEEPL_ENABLED=false                         # set to true to activate
```

Get a free key at [deepl.com/pro-api](https://www.deepl.com/pro-api) — 500,000 chars/month included.

LLM-based translation works without any key (uses your configured LLM provider).

---

### Vector Store / RAG

```bash
VECTOR_STORE_ENABLED=true
VECTOR_STORE_PATH=data/vector_store

# Embedding model (requires GEMINI_API_KEY)
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768

# Retrieval parameters
RAG_GROUND_TRUTH_TOP_K=10
RAG_PREVIOUS_GEN_TOP_K=8
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=50
RAG_QUERY_COUNT=4

# Context retrieval mode
CONTEXT_RETRIEVAL_MODE=rag   # rag | legacy
```

If `VECTOR_STORE_ENABLED=false` or the vector store has not been indexed, the system automatically falls back to `legacy` mode.

---

### Debug Options

```bash
DEBUG=false                 # true enables SQL query logging
RAG_DEBUG_MODE=false        # true logs RAG retrieval details to terminal
DEBUG_AGENT_PROMPTS=false   # true saves full agent prompts to backend/data/agent_prompts/
```

---

## 6. Per-Agent Model Configuration

Each of the 9 AI agents can use a different LLM model, letting you balance cost and quality:

1. Open **Settings → Advanced Configuration → § II. Per-Agent Models**.
2. Configure any agents: Historian, Storyteller, Skeleton, Skeleton Historian, Illustrator, Script Writer, Translator, Character Profiler, Impersonator.
3. Save configuration.

**Tip**: Use cheaper/faster models for structure-heavy agents (Skeleton, Historian) and better models for creative output (Storyteller, Impersonator).

Agent config can also be set via API; see the [API documentation](http://localhost:8000/docs) when the backend is running.

---

## 7. Data Management

### Database

The SQLite database is created automatically on first run:

```
backend/data/timelines.db
```

No migration steps are required for a fresh install.

### Audio Files

Generated audio files are stored at:

```
backend/data/audio/
```

### Resetting All Data

To wipe all timelines and media, and clear stored API keys (provider/model settings are kept; keys fall back to `.env`):

```bash
cd backend
source venv/bin/activate
python scripts/purge_data.py --yes
```

To also remove ground truth data (requires re-indexing afterwards):

```bash
python scripts/purge_data.py --include-ground-truth --yes
```

You can also trigger a purge from the UI: **Settings → Advanced Configuration → § IV. Debug & Vector Store → Purge All Data**.

---

## 8. Docker Alternative

If you prefer not to manage Python and Node.js environments manually, Docker is available:

```bash
cp .env.example .env
# Edit .env and add your API key
docker-compose up -d
```

The app will be accessible at **http://localhost**.

See [`docs/DOCKER_SETUP.md`](../DOCKER_SETUP.md) for the full Docker guide including backup, port configuration, and server hosting.

---

## 9. Troubleshooting

### Backend won't start

- Confirm the virtual environment is active (`(venv)` in prompt).
- Confirm `pip install -r requirements.txt` completed without errors.
- Check that `.env` exists and has at least one API key set.

### "No module named 'spacy'" / figure scan not working

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

### Frontend shows "Failed to fetch" or empty data

- Confirm the backend is running on port 8000.
- Check the backend terminal for Python errors.
- Open http://localhost:8000/docs to verify the API is up.

### Generation fails with API error

- Verify your API key is correct in `.env` (no extra spaces or quotes).
- Check whether the provider is rate-limited.
- Try switching to a different provider in **Settings** (Provider Setup).

### RAG not working / "vector store unavailable"

- Run `python scripts/index_ground_truth.py` from the `backend/` directory.
- Confirm `GEMINI_API_KEY` is set (required for embeddings even if using another LLM provider).
- Check `VECTOR_STORE_ENABLED=true` in `.env`.

### NotebookLM Audio not generating

- Run `nlm login --check` to verify authentication.
- Confirm the feature is enabled in **Settings → Advanced Configuration → § V. Integrations**.
- Remember: generation takes 5–20 minutes (processed by Google externally).

### CLIProxy provider returns errors

- Confirm `cliproxyapi` is running in a separate terminal.
- Check that you authenticated: `cliproxyapi --browser-auth` (re-run if session expired).
- Confirm the feature is enabled in **Settings → Advanced Configuration → § V. Integrations → CLIProxy**.
- Verify the proxy URL matches — default is `http://localhost:8317/v1`. Set `CLIPROXY_BASE_URL` in `.env` if you changed the port.

### Port conflicts

If something is already running on port 8000 or 5173, stop it or change ports:

- Backend: change `API_PORT` in `.env` and pass `--port <new>` to uvicorn.
- Frontend: edit `vite.config.ts` → `server.port`.

---

## 10. Quick Reference

```bash
# Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev

# One-time: index vector store
cd backend && python scripts/index_ground_truth.py

# One-time: spaCy model
python -m spacy download en_core_web_sm

# One-time: NotebookLM auth
pip install notebooklm-cli && nlm login

# One-time: CLIProxy auth (if using subscription instead of API key)
cliproxyapi --browser-auth

# Reset all data
cd backend && python scripts/purge_data.py --yes
```

| URL | Purpose |
|-----|---------|
| http://localhost:5173 | Frontend UI |
| http://localhost:8000/docs | Interactive API docs |
| http://localhost:8000/health | Backend health check |
