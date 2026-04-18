#!/usr/bin/env python3
"""
Deviation Engine launcher.

Sets up the environment on first run and starts the application.
Requires: Python 3.9+, Node.js + npm
"""

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from subprocess import CalledProcessError

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.resolve()
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / "venv"
ENV_FILE = BACKEND / ".env"
ENV_EXAMPLE = BACKEND / ".env.example"
REQUIREMENTS = BACKEND / "requirements.txt"
FRONTEND_SRC = FRONTEND / "src"
FRONTEND_DIST = FRONTEND / "dist"
FRONTEND_MODULES = FRONTEND / "node_modules"

if sys.platform == "win32":
    VENV_PYTHON = VENV / "Scripts" / "python.exe"
    VENV_PIP = VENV / "Scripts" / "pip.exe"
else:
    VENV_PYTHON = VENV / "bin" / "python"
    VENV_PIP = VENV / "bin" / "pip"

APP_URL = "http://localhost:8000"
NODE = shutil.which("node") or "node"
NPM = shutil.which("npm") or "npm"
_WIN = sys.platform == "win32"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def step(text: str) -> None:
    print(f"\n[*] {text}")


def ok(text: str) -> None:
    print(f"    OK  {text}")


def warn(text: str) -> None:
    print(f"   WARN  {text}")


def error(text: str) -> None:
    print(f"\n  ERROR: {text}\n")


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, shell=_WIN)


# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------

def check_prerequisites() -> None:
    header("Checking prerequisites")

    ver = sys.version_info
    if ver < (3, 9):
        error(f"Python 3.9+ required, found {ver.major}.{ver.minor}. Get it from https://python.org")
        sys.exit(1)
    ok(f"Python {ver.major}.{ver.minor}.{ver.micro}")

    if not shutil.which("node"):
        error("Node.js not found. Install from https://nodejs.org (LTS version recommended)")
        sys.exit(1)
    node_ver = subprocess.check_output([NODE, "--version"], text=True, shell=_WIN).strip()
    ok(f"Node.js {node_ver}")

    if not shutil.which("npm"):
        error("npm not found. It should come with Node.js. Reinstall from https://nodejs.org")
        sys.exit(1)
    npm_ver = subprocess.check_output([NPM, "--version"], text=True, shell=_WIN).strip()
    ok(f"npm {npm_ver}")


# ---------------------------------------------------------------------------
# 2. First-run setup
# ---------------------------------------------------------------------------

def prompt_optional(label: str) -> str:
    try:
        value = input(f"  {label} (press Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        value = ""
    return value.replace("\n", "").replace("\r", "")


def setup_env() -> None:
    if ENV_FILE.exists():
        return

    header("First-run setup — API keys")
    print(
        "\n  Deviation Engine needs at least one LLM API key to generate timelines.\n"
        "  Get a free Gemini key at: https://aistudio.google.com/app/apikey\n"
    )

    gemini_key = prompt_optional("Gemini API key (recommended)")
    openrouter_key = prompt_optional("OpenRouter API key")
    anthropic_key = prompt_optional("Anthropic API key (for direct Claude access)")
    openai_key = prompt_optional("OpenAI API key (for direct ChatGPT access)")

    if not gemini_key and not openrouter_key and not anthropic_key and not openai_key:
        warn("No LLM key provided — the app will start but cannot generate timelines.")
        warn("Edit backend/.env later and add at least one LLM API key.")

    print("\n  Optional services (all skippable):")
    pollinations_key = prompt_optional("Pollinations API key (for image generation)")
    deepl_key = prompt_optional("DeepL API key (for fast translation)")

    # CLIProxy subscription bridge
    print(
        "\n  CLIProxy — use a Claude Pro/Max or OpenAI subscription instead of paying API costs:\n"
        "  Do you want to use CLIProxyAPI? It routes requests through your existing subscription.\n"
    )
    use_cliproxy = prompt_optional("Enable CLIProxy? [y/N]").lower() in ("y", "yes")
    if use_cliproxy:
        print(
            "\n  ─────────────────────────────────────────────────────────\n"
            "  CLIProxy Setup Instructions\n"
            "  ─────────────────────────────────────────────────────────\n"
            "\n"
            "  1. Install CLIProxyAPI (Linux/macOS):\n"
            "     bash <(curl -fsSL https://github.com/router-for-me/CLIProxyAPI\n"
            "                       /releases/latest/download/install.sh)\n"
            "\n"
            "  2. Authenticate once (opens a browser):\n"
            "     cliproxyapi --browser-auth\n"
            "\n"
            "  3. Start the proxy (keep it running alongside Deviation Engine):\n"
            "     cliproxyapi\n"
            "\n"
            "  4. In the app: go to Settings → V. Integrations → enable CLIProxy.\n"
            "     Then go to § I. Language Model and select 'CLIProxy (Subscription)'.\n"
            "\n"
            "  The proxy listens on http://localhost:8317/v1 by default.\n"
            "  You can override this with the CLIPROXY_BASE_URL environment variable.\n"
            "  ─────────────────────────────────────────────────────────\n"
        )

    env_content = ENV_EXAMPLE.read_text(encoding="utf-8")

    substitutions = {
        "GEMINI_API_KEY=your_gemini_api_key_here": f"GEMINI_API_KEY={gemini_key}",
        "OPENROUTER_API_KEY=your_openrouter_api_key_here": f"OPENROUTER_API_KEY={openrouter_key}",
        "ANTHROPIC_API_KEY=your_anthropic_api_key_here": f"ANTHROPIC_API_KEY={anthropic_key}",
        "OPENAI_API_KEY=your_openai_api_key_here": f"OPENAI_API_KEY={openai_key}",
        "POLLINATIONS_API_KEY=your_pollinations_api_key_here": f"POLLINATIONS_API_KEY={pollinations_key}",
        "DEEPL_API_KEY=your_deepl_api_key_here:fx": f"DEEPL_API_KEY={deepl_key}",
    }
    for placeholder, replacement in substitutions.items():
        env_content = env_content.replace(placeholder, replacement)

    if deepl_key:
        env_content = env_content.replace("DEEPL_ENABLED=false", "DEEPL_ENABLED=true")

    # Set default provider based on which key was provided first
    if not gemini_key:
        if anthropic_key:
            env_content = env_content.replace(
                "DEFAULT_LLM_PROVIDER=google", "DEFAULT_LLM_PROVIDER=anthropic"
            )
        elif openai_key:
            env_content = env_content.replace(
                "DEFAULT_LLM_PROVIDER=google", "DEFAULT_LLM_PROVIDER=openai"
            )
        elif openrouter_key:
            env_content = env_content.replace(
                "DEFAULT_LLM_PROVIDER=google", "DEFAULT_LLM_PROVIDER=openrouter"
            )

    ENV_FILE.write_text(env_content, encoding="utf-8")
    ok("backend/.env created")


# ---------------------------------------------------------------------------
# 3. Virtual environment + Python dependencies
# ---------------------------------------------------------------------------

def setup_venv() -> None:
    header("Python dependencies")

    if not VENV.exists():
        step("Creating virtual environment...")
        run([sys.executable, "-m", "venv", str(VENV)])
        ok("Virtual environment created")

    step("Installing/updating Python packages...")
    try:
        run([str(VENV_PIP), "install", "--quiet", "-r", str(REQUIREMENTS)])
    except CalledProcessError:
        error("Failed to install Python packages. Check your internet connection and try again.")
        sys.exit(1)
    ok("Python packages ready")

    step("Ensuring spaCy language model (en_core_web_sm)...")
    try:
        run([str(VENV_PYTHON), "-m", "spacy", "download", "en_core_web_sm", "--quiet"])
    except CalledProcessError:
        error("Failed to download spaCy model. Check your internet connection and try again.")
        sys.exit(1)
    ok("spaCy model ready")


# ---------------------------------------------------------------------------
# 4. Frontend build (smart)
# ---------------------------------------------------------------------------

def needs_rebuild() -> bool:
    index_html = FRONTEND_DIST / "index.html"
    if not index_html.exists():
        return True
    dist_mtime = index_html.stat().st_mtime

    # Watch source files
    for src_file in FRONTEND_SRC.rglob("*"):
        if src_file.is_file() and src_file.stat().st_mtime > dist_mtime:
            return True

    # Watch root config files
    config_patterns = ["package.json", "package-lock.json", "index.html"]
    for name in config_patterns:
        f = FRONTEND / name
        if f.is_file() and f.stat().st_mtime > dist_mtime:
            return True
    for f in FRONTEND.glob("*.config.*"):
        if f.is_file() and f.stat().st_mtime > dist_mtime:
            return True

    return False


def build_frontend() -> None:
    header("Frontend")

    if not FRONTEND_MODULES.exists():
        step("Installing npm packages (first run, may take a minute)...")
        try:
            run([NPM, "install", "--silent"], cwd=FRONTEND)
        except CalledProcessError:
            error("npm install failed. Check your internet connection and try again.")
            sys.exit(1)
        ok("npm packages installed")

    if needs_rebuild():
        step("Building frontend (this takes ~30 seconds)...")
        try:
            run([NPM, "run", "build"], cwd=FRONTEND)
        except CalledProcessError:
            error("Frontend build failed. Run 'npm run build' in the frontend/ directory to see details.")
            sys.exit(1)
        ok("Frontend built")
    else:
        ok("Frontend is up to date — skipping build")


# ---------------------------------------------------------------------------
# 5. Launch
# ---------------------------------------------------------------------------

def launch() -> None:
    header("Starting Deviation Engine")
    print(f"\n  Application will open at: {APP_URL}\n")

    uvicorn_cmd = [
        str(VENV_PYTHON), "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
    ]

    proc = subprocess.Popen(uvicorn_cmd, cwd=BACKEND)

    print("  Waiting for server to start...")
    health_url = f"{APP_URL}/api/health"
    for attempt in range(60):  # up to 30 seconds
        time.sleep(0.5)
        if proc.poll() is not None:
            error(f"Server failed to start (exit code {proc.returncode}). Check the output above for details.")
            sys.exit(1)
        try:
            urllib.request.urlopen(health_url, timeout=2)
            break
        except (urllib.error.URLError, OSError):
            pass
    else:
        error("Server did not become ready within 30 seconds. Try running 'uvicorn app.main:app' manually in the backend/ directory.")
        proc.terminate()
        sys.exit(1)

    webbrowser.open(APP_URL)
    print(f"  Opened {APP_URL} in your browser.\n")
    print("  Press Ctrl+C to stop.\n")
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n\n  Shutting down...")
        proc.terminate()
        proc.wait()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        check_prerequisites()
        setup_env()
        setup_venv()
        build_frontend()
        launch()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
