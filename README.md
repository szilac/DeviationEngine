# Deviation Engine

**AI-powered alternate history timeline generator**

Create plausible "what-if" scenarios by changing a single moment in history between 1880–2004. Watch how the world could have evolved differently — with comprehensive analysis, narrative stories, images, and audio content.

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is Deviation Engine?

Deviation Engine lets you explore alternate histories by asking: *"What if this one thing had been different?"*

**Example scenarios**:

- *"What if the Titanic never sank?"*
- *"What if the 1929 stock market crash was prevented?"*
- *"What if Franz Ferdinand survived the assassination attempt?"*
- *"What if the Spanish Flu pandemic was contained?"*

The AI analyzes historical context, generates detailed timelines, creates comprehensive analytical reports, and can write engaging narrative prose about your alternate world.

---

## Quick Start

1. Install [Python 3.9+](https://python.org) and [Node.js LTS](https://nodejs.org)
2. Double-click `start.sh` (Mac/Linux) or `start.bat` (Windows)
3. Enter your API key when prompted — get a free Gemini key at [Google AI Studio](https://aistudio.google.com/app/apikey)
4. The app opens in your browser automatically

On subsequent runs, just double-click the launcher again — no setup needed.

> **Manual setup:** See the [Development](#development) section below for running the backend and frontend servers separately.

---

## Development

### What You Need

- **Node.js** 18+ and npm
- **Python** 3.9+
- **API Key**: [Google Gemini API](https://aistudio.google.com/) (free tier available) OR [OpenRouter](https://openrouter.ai/) OR Anthropic/OpenAI direct keys
- **Optional**: [DeepL API Key](https://www.deepl.com/pro-api) for fast translations (500k chars/month free)
- **Optional**: [notebooklm-cli](https://github.com/jnsahaj/notebooklm-cli) for NotebookLM AI audio
- **Optional**: [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) to use a Claude Pro/Max or OpenAI subscription instead of paying per-token API costs

### Installation

```bash
# Clone the repository
git clone https://github.com/szilac/DeviationEngine.git
cd DeviationEngine
```

```bash
# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API key
```

> **Note — Historical Figure Scan:** The character detection feature uses spaCy for NLP-based name recognition. Install it once after `pip install -r requirements.txt`:
> ```bash
> python -m spacy download en_core_web_sm
> ```
> The app will start without it, but the effectiveness of **Scan Timeline** button in the Characters panel will be reduced (inferior fall-back option).

```bash
# Frontend setup (in a new terminal)
cd frontend
npm install
```

### Running the Application

**Terminal 1 — Backend:**

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173> in your browser.

---

## Capabilities

### Timeline Generation

- **Structured Analysis**: Political, economic, social, and technological impact reports across 8 sections
- **Narrative Prose**: Engaging storytelling in multiple styles (omniscient, custom perspective)
- **Skeleton Workflow**: Generate editable event skeletons before committing to a full report
- **Timeline Extensions**: Add more years to any existing timeline

### Audio Content

Two independent audio pipelines, both accessible from the **Audio Studio** panel:

**Script + Google TTS** — Full control over narration:

- AI generates an audio-optimized script from your timeline content
- 4 professional presets: Documentary, Podcast, News Bulletin, Storytelling
- Edit and review the script before generating audio
- Google TTS for high-quality narration with multi-language support

**NotebookLM Audio** — Google's AI podcast engine (see [NotebookLM Setup](#notebooklm-audio-setup) below):

- Deep-dive discussions and debate formats
- Sounds more natural and conversational than TTS
- Supports multiple formats: Deep Dive, Brief, Critique, Debate
- Configurable length and language, with optional focus instructions

### Historical Figure Chat

Bring the people of your alternate timeline to life:

- **Auto-detection**: Scan any timeline to find historical figures mentioned in the content
- **Custom characters**: Add your own characters with user-provided biographies
- **AI profile generation**: Creates structured biographical profiles (personality, beliefs, speaking style, relationships)
- **Year-scoped profiles**: Capture character development at different points in time
- **In-character conversations**: Chat with figures as they exist in your alternate world — they only know what happened up to their year context
- **RAG-powered responses**: ChromaDB vector retrieval ensures responses reference actual timeline events

### Temporal Atlas

Explore all your timelines on a unified D3.js canvas:

- Branching visualisation with colour-coded alternate paths
- Deviation point diamond medallion on the main time axis
- Particle animation showing causal energy propagation
- Animated floating rope branches with cursor interaction

### Ripple Map

Explore the causal web of your alternate history with an interactive force-directed graph:

- Nodes coloured by domain (political, economic, social, technological, cultural, military) and sized by magnitude
- Linear and radial layout modes
- Directional edges showing causal relationships
- Filter by domain, confidence level, or generation

<details>
<summary><strong>More capabilities: Images, Translation, Export, RAG</strong></summary>

### Image Generation

- AI creates period-appropriate image prompts
- Edit prompts before generating
- Free image generation via Pollinations.ai (no API key needed)
- Gallery view with lightbox

### Translation

- 11 languages supported
- Two methods: DeepL (fast ~5s) or AI Translation (native quality ~30s)
- Content-aware translations for different content types

### Export & Import

- Export timelines as portable `.devtl` files
- Import timelines from other installations
- Export individual generations as Markdown

### AI-Powered Historical Context (RAG)

- **Smart Search Mode**: Vector-based RAG retrieves only relevant historical context (~90% token reduction vs full context)
- **Full Context Mode**: Traditional approach loading all historical data from the period
- Configurable globally or per-timeline
- Uses Google Gemini embeddings with ChromaDB vector store

</details>

---

## NotebookLM Audio Setup

NotebookLM Audio uses Google's [NotebookLM](https://notebooklm.google.com/) to generate AI-powered podcast discussions about your alternate history. The result sounds far more natural and engaging than standard TTS — two AI hosts genuinely discuss your content rather than simply reading it.

### Why NotebookLM?

| | Script + Google TTS | NotebookLM Audio |
| --- | --- | --- |
| **Sound** | Narrated, documentary-style | Natural conversation between two AI hosts |
| **Formats** | 4 scripted presets | Deep Dive, Brief, Critique, Debate |
| **Control** | Full script editing | Focus instructions only |
| **Speed** | ~5–10 minutes | 5–20 minutes (processed by Google) |
| **Cost** | Free (with rate limit) | Free (uses your Google account) |
| **API key required** | Yes (Google TTS) | No — uses `nlm` CLI + your Google login |

### Installation

```bash
pip install notebooklm-cli
```

Authenticate with your Google account:

```bash
nlm login
```

Follow the browser prompt to sign in. Your session is stored locally — you only need to do this once.

Verify the setup:

```bash
nlm login --check
# Authentication valid!
```

### Enabling in Deviation Engine

1. Go to **Settings** → **Audio**
2. Toggle **Enable NotebookLM Audio**
3. The **NotebookLM** tab appears in the Audio Studio panel on any timeline

### How It Works

When you submit a generation request, Deviation Engine:

1. **Creates** a temporary NotebookLM notebook via `nlm notebook create`
2. **Uploads** your selected timeline content (reports and/or narrative prose) as markdown sources
3. **Triggers** audio generation with your chosen format and settings via `nlm audio create`
4. **Polls** for completion every 30 seconds (Google typically takes 5–20 minutes)
5. **Downloads** the finished `.m4a` audio and stores it locally
6. **Cleans up** the temporary notebook from your NotebookLM account

### Audio Formats

| Format | Description |
| --- | --- |
| **Deep Dive** | Two-host podcast exploring the alternate history in depth |
| **Brief** | Concise summary of key events and implications |
| **Critique** | Critical analysis examining strengths and weaknesses of the scenario |
| **Debate** | Two perspectives debating the plausibility and consequences |

### Focus Instructions

You can optionally guide the discussion, for example:

- *"Focus on the economic consequences"*
- *"Discuss as if you lived through these events"*
- *"Emphasise the human stories rather than political analysis"*

---

## CLIProxy Setup

CLIProxyAPI is a local proxy server that wraps the Claude Code or OpenAI CLI and exposes an OpenAI-compatible API at `http://localhost:8317/v1`. If you already pay for a **Claude Pro/Max** or **OpenAI** subscription, you can use it with Deviation Engine at no extra token cost.

### Installation

```bash
# Linux / macOS
bash <(curl -fsSL https://github.com/router-for-me/CLIProxyAPI/releases/latest/download/install.sh)
```

### Authenticate (once)

```bash
cliproxyapi --browser-auth
```

This opens a browser to authenticate with your subscription. Your session is stored locally.

### Run the proxy

```bash
cliproxyapi
```

Keep this running alongside Deviation Engine. The proxy listens on `http://localhost:8317/v1` by default.

### Enable in Deviation Engine

1. Go to **Settings** → **§ V. Integrations**
2. Toggle **CLIProxy — Subscription API Bridge**
3. Read the inline setup steps and confirm the proxy is running
4. Go to **§ I. Language Model** → select **CLIProxy (Subscription)**
5. Choose a model (e.g. `claude-sonnet-4-20250514`) and save

You can override the default URL with the `CLIPROXY_BASE_URL` environment variable in `backend/.env`.

> **Note**: CLIProxy is designed for Claude Max subscriptions. Claude Pro users will work but may hit rate limits during heavy generation sessions.

---

## Usage Guide

### Creating Your First Timeline

#### Option 1: Skeleton Workflow (Recommended)

1. **Navigate to Console** → select **Skeleton Workflow**
2. **Enter Details**: date (1880–2004), description, simulation years, scenario type
3. **Generate Skeleton** — wait ~30–60 seconds for 15–25 key events
4. **Review Events**: edit descriptions, add or delete events
5. **Approve** to lock in your structure
6. **Generate Report**: choose narrative mode and generate full analysis

#### Option 2: Direct Generation (Faster)

1. Go to **Console** → select **Direct Generation**
2. Fill in details and choose narrative mode
3. Click **Generate Timeline** — wait ~60–120 seconds

### Extending Timelines

1. Open any saved timeline
2. Scroll to **Extend This Timeline**
3. Choose Skeleton or Direct extension
4. Set additional years (1–30) and optional context

### Creating Audio Content

**Script + Google TTS:**

1. Open any timeline → **Audio Studio**
2. Select generations and choose a preset
3. Generate and review the script
4. Approve and generate audio

**NotebookLM Audio:**

1. Open any timeline → **Audio Studio** → **NotebookLM** tab
2. Select generations to include (reports and/or narrative)
3. Choose format, length, and language
4. Optionally add focus instructions
5. Click **Generate NotebookLM Audio** and wait 5–20 minutes
6. The audio appears in Past Generations when complete

### Chatting with Historical Figures

1. Open any timeline with at least one generation
2. Find the **Historical Figures** panel
3. Click **Scan Timeline** to auto-detect figures (or **Add Custom**)
4. Click **Generate Profile**, set a cutoff year, wait ~30–60 seconds
5. Once **Ready**, click **Chat** and pick a year context

<details>
<summary><strong>More workflows: Images, Translation, Export</strong></summary>

### Generating Images

1. Open any timeline → **Images** tab
2. Click **Generate Images**
3. Configure: number (3–20), focus areas (political, economic, etc.)
4. Review and edit prompts (optional), then approve and generate

### Translating Content

1. Open any timeline and use the language selector
2. Choose method: DeepL (fast) or AI Translation (quality)
3. Click translate — toggle **Show Original** to switch back

**Supported Languages**: Hungarian, German, Spanish, Italian, French, Portuguese, Polish, Dutch, Japanese, Chinese

### Exporting Timelines

- Export as `.devtl` portable file from the timeline menu
- Import on any other Deviation Engine installation
- Export individual generations as Markdown

</details>

---

## Configuration

### LLM Provider Setup

Edit `.env` in the backend directory (copy from `.env.example`):

#### Google Gemini (Recommended)

```bash
GEMINI_API_KEY=your_gemini_api_key
DEFAULT_LLM_PROVIDER=google
DEFAULT_LLM_MODEL=gemini-2.5-flash-lite
```

[Get free API key](https://aistudio.google.com/)

#### OpenRouter

```bash
OPENROUTER_API_KEY=your_openrouter_api_key
DEFAULT_LLM_PROVIDER=openrouter
DEFAULT_LLM_MODEL=openai/gpt-4o-mini
```

[Get OpenRouter key](https://openrouter.ai/)

#### Anthropic Claude (Direct)

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-sonnet-4-6
```

#### OpenAI (Direct)

```bash
OPENAI_API_KEY=your_openai_api_key
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o
```

#### CLIProxy — Use Your Subscription (No API Key Needed)

If you already pay for a **Claude Pro/Max** or **OpenAI** subscription, CLIProxyAPI lets you route Deviation Engine through that subscription instead of paying separate API token costs.

See the [CLIProxy Setup](#cliproxy-setup) section below.

You can also switch providers via **Settings** in the web UI.

<details>
<summary><strong>Translation, RAG, and per-agent configuration</strong></summary>

### Translation Setup (Optional)

**DeepL** (fast):

```bash
DEEPL_API_KEY=your_deepl_api_key:fx
DEEPL_API_TIER=free
DEEPL_ENABLED=true
```

[Get free DeepL API key](https://www.deepl.com/pro-api) — 500,000 chars/month free

**AI Translation**: No setup needed, uses your configured LLM.

Configure via **Settings** → **Translation Settings**.

### Vector Store / RAG Configuration

**Smart Search (Recommended)**:

```bash
VECTOR_STORE_ENABLED=true
CONTEXT_RETRIEVAL_MODE=rag
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
```

**Full Context (Legacy)**:

```bash
CONTEXT_RETRIEVAL_MODE=legacy
```

Smart Search reduces API costs by ~90% vs Full Context. Index ground truth data with:

```bash
python scripts/index_ground_truth.py
```

Configure globally in **Settings** → **Debug** → **Default Context Mode**.

### Per-Agent Model Configuration

Use different AI models for each agent to balance cost and quality:

1. Go to **Settings** → **Per-Agent Model Settings**
2. Configure any of the 9 agents: Historian, Storyteller, Skeleton, Skeleton Historian, Illustrator, Script Writer, Translator, Character Profiler, Impersonator
3. Save configuration

**Tip**: Use cheaper models for structure-heavy agents (Skeleton, Historian) and premium models for creative output (Storyteller, Impersonator).

</details>

---

<details>
<summary><strong>Tips & Best Practices</strong></summary>

### Writing Good Deviation Descriptions

**Good Examples**:

- *"Archduke Franz Ferdinand's driver takes the correct turn in Sarajevo"*
- *"The Wright Brothers' first flight fails due to strong winds"*
- *"Marie Curie receives full credit for discovering radioactivity"*

**Avoid**:

- Too vague: *"Something happens in 1929"*
- Too broad: *"All of World War 1 never happens"*
- Outside range: *"The internet is invented in 1975"* (must be 1880–2004)

### Choosing Simulation Years

- **Short (1–10 years)**: Immediate effects, more detail
- **Medium (10–30 years)**: Balance of scope and detail
- **Long (30–50 years)**: Long-term implications, broader view

### Narrative Modes

- **None**: Structured report only (~60 seconds)
- **Basic**: Good balance of quality and speed (~90 seconds)
- **Advanced Omniscient**: Best quality, neutral perspective (~120 seconds)
- **Advanced Custom POV**: Unique perspective, e.g. *"From the viewpoint of a journalist in Berlin"*

### Image Generation Tips

- Start with 5–10 images to see results quickly
- Use focus areas for themed galleries (political, economic, social)
- Edit prompts before generating for better quality
- Add style notes like *"photorealistic 1920s documentary"*

</details>

<details>
<summary><strong>LLM & Performance Tips</strong></summary>

### Recommended Models

The **Gemini Flash** family (2.5, 3.0) is the recommended starting point for all agents. These models offer a generous free-tier rate limit and a very large context window (up to 1 million tokens), which suits the long prompts Deviation Engine generates. For most users this is the best default choice.

### Handling Rate Limits

If you hit the rate limit on one Gemini Flash version, switch to the other — **Gemini 2.5 Flash** and **Gemini 3.0 Flash** operate on separate quotas and produce nearly identical output quality. Simply update the affected agent's model in **Settings → Per-Agent Model Settings** and continue.

### Transient Failures

LLM providers occasionally fail to respond during periods of high server load. If a generation fails unexpectedly, wait a few minutes and try again — this resolves most transient issues. The app will notify you of failures; check the backend terminal for more detailed error output.

### Per-Agent Model Recommendations

Every agent can use a different LLM model. Configure them in **Settings → Per-Agent Model Settings**:

| Agent | Recommendation |
| --- | --- |
| **Skeleton, Historian, Ripple Analyst** | Structure-heavy tasks — capable reasoning models work well |
| **Storyteller, Character Profiler** | Creative output — higher-quality models produce noticeably better results |
| **Translator** | Must use a multilingual model; Gemini Flash and GPT-series are reliable choices |
| **Impersonator** | Conversational tasks — smaller, faster models (e.g. Gemini Flash Lite, GPT-4o mini) work fine and reduce cost and latency |

### OpenRouter

OpenRouter requires a small credit balance rather than a subscription. Costs are very low — a modest top-up typically lasts a long time at normal usage levels. Through OpenRouter you can route requests to almost any major LLM. When experimenting, pay attention to each model's **context window** and **per-token pricing** to avoid unexpected costs.

### Context Mode: RAG vs Full Context

Configurable per-generation in the **Advanced Options** panel on the Deviation Console, and globally in **Settings → Debug → Default Context Mode**:

| Mode | Token Usage | Quality | Best For |
| --- | --- | --- | --- |
| **RAG (Smart Search)** | Very low (~99% reduction) | Good — occasionally less consistent if retrieval misses relevant context | Default; cost-conscious use |
| **Full Context** | High | Rich and consistent — may overwhelm models with small context windows | High-quality generations with capable, large-context models |

Full Context sends the complete ground truth data for the deviation period and, for extensions, all previous generation reports. This produces richer and more coherent results but significantly increases token usage and cost.

</details>

<details>
<summary><strong>Advanced Features & CLI Utilities</strong></summary>

### Debug Settings

Access via **Settings** → **Debug**:

- **Default Context Mode**: Set global RAG vs Legacy mode for new timelines
- **RAG Debug Mode**: Log detailed retrieval information to backend terminal
- **Agent Prompt Logging**: Save complete agent prompts to `backend/data/agent_prompts/`
- **Vector RAG Toggle**: Enable/disable vector store (requires restart)
- **Data Purge**: Reset all user data; clears stored API keys while preserving provider/model config and ground truth

### CLI Utilities

**Index Ground Truth** (populate vector store):

```bash
cd backend
python scripts/index_ground_truth.py [--force] [--debug]
```

**Purge All Data** (reset application):

```bash
cd backend
python scripts/purge_data.py [--include-ground-truth] [--yes]
```

### Scenario-Specific AI Behaviour

The skeleton agent adapts its strategy based on scenario type:

- **Local Deviation**: Strict historical realism, butterfly effects
- **Global Deviation**: Systemic shock modelling, resource reallocation
- **Reality Fracture**: Chaotic response to broken physics
- **Geological Shift**: Environmental pressure analysis
- **External Intervention**: Paranoia, forbidden knowledge, shadow wars

</details>

---

## Limitations

- Single-user — no authentication (personal use only)
- AI content is plausible fiction, not historically verified
- Deviation dates limited to 1880–2004
- NotebookLM Audio generation takes 5–20 minutes (processed by Google)
- Vector store requires Gemini API key for embeddings

---

## Support

- **Issues**: [GitHub Issues](https://github.com/szilac/DeviationEngine/issues)
- **API Docs**: <http://localhost:8000/docs> (when backend is running)
- **Setup & Run Guide**: See [docs/technical/SETUP_AND_RUN.md](docs/technical/SETUP_AND_RUN.md)
- **User Guide**: See [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com/), [React 19](https://reactjs.org/), [Pydantic-AI](https://ai.pydantic.dev/), and [D3.js](https://d3js.org/). Powered by [Google Gemini](https://deepmind.google/technologies/gemini/), [OpenRouter](https://openrouter.ai/), Anthropic Claude, or OpenAI — or via [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) using your existing subscription. NotebookLM audio via [notebooklm-cli](https://github.com/jnsahaj/notebooklm-cli). UI designed with the Quantum Manuscript design system — Tailwind CSS v4, Motion, IM Fell English / Crimson Pro typography.

---

*Explore history. Change a moment. See the ripples.*
