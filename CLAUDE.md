# CLAUDE.md — AI Assistant Guide for MCP Kali Server

This document provides context for AI coding assistants working in this repository.

---

## Project Overview

**MCP Kali Server** is a two-component bridge that exposes Kali Linux security tools to AI assistants via the [Model Context Protocol (MCP)](https://github.com/anthropics/mcp).

- **Component 1 — `kali_server.py`**: A Flask REST API server that runs on a Kali Linux host and wraps security tools (nmap, gobuster, sqlmap, etc.) into HTTP endpoints.
- **Component 2 — `mcp_server.py`**: An MCP server that runs on the client machine (e.g., alongside Claude Desktop), translates MCP tool calls into HTTP requests to `kali_server.py`.

**Forked from:** [Wh0am123/MCP-Kali-Server](https://github.com/Wh0am123/MCP-Kali-Server)
**Fork direction:** Expanding AI integrations, multi-agent orchestration, and extended security automation.
**Status:** v0.1.0 Alpha — for educational and authorized security testing only.

---

## Repository Structure

```
forked-u-MCP-Kali-Server/
├── kali_server.py        # Flask API server (runs on Kali Linux)
├── mcp_server.py         # MCP client/bridge (runs on AI client machine)
├── test_basic.py         # pytest unit tests
├── requirements.txt      # Pinned runtime dependencies
├── pyproject.toml        # Build config, tool settings (black, isort, pylint, pytest)
├── Dockerfile            # Multi-stage Docker image (python:3.11-slim, non-root user)
├── docker-compose.yml    # Service definition with resource limits
├── .env.example          # Template for environment variables
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci.yml                        # Lint, test, Docker build, security scan
│       ├── codeql.yml                    # CodeQL static analysis
│       ├── codelql.yml                   # Duplicate CodeQL workflow (legacy)
│       ├── release.yml                   # Release automation
│       └── branch-protection-reminder.yml
├── CONTRIBUTING.md       # Development process, style guide, commit format
├── SECURITY.md           # Security policy and vulnerability reporting
├── CHANGELOG.md
├── RELEASE_NOTES.md
├── RELEASE_PROCESS.md
├── BRANCH_PROTECTION.md
└── LICENSE               # MIT
```

---

## Architecture

```
AI Client (Claude Desktop / 5ire)
        │  MCP protocol (stdio)
        ▼
  mcp_server.py  ←── KaliToolsClient
        │  HTTP POST/GET
        ▼
  kali_server.py  ←── Flask app
        │  subprocess (shell=False)
        ▼
  Kali Linux tools (nmap, gobuster, etc.)
```

### `kali_server.py` — Flask API Server

**Entry point:** `if __name__ == "__main__": app.run(host="0.0.0.0", port=API_PORT)`
**Key class:** `CommandExecutor` — wraps `subprocess.Popen` with threading for stdout/stderr and graceful timeout handling (terminate → kill).

**API endpoints:**

| Endpoint | Method | Tool |
|---|---|---|
| `/health` | GET | Tool availability check |
| `/api/command` | POST | Allowlisted safe commands (see `COMMAND_ALLOWLIST`) |
| `/api/tools/nmap` | POST | nmap |
| `/api/tools/gobuster` | POST | gobuster |
| `/api/tools/dirb` | POST | dirb |
| `/api/tools/nikto` | POST | nikto |
| `/api/tools/sqlmap` | POST | sqlmap |
| `/api/tools/metasploit` | POST | msfconsole (via temp `.rc` resource file at `/tmp/mcp_msf_resource.rc`) |
| `/api/tools/hydra` | POST | hydra |
| `/api/tools/john` | POST | john |
| `/api/tools/wpscan` | POST | wpscan |
| `/api/tools/enum4linux` | POST | enum4linux |
| `/mcp/capabilities` | GET | Stub (not yet implemented) |
| `/mcp/tools/kali_tools/<tool_name>` | POST | Stub (not yet implemented) |

**Configuration (environment variables):**

| Variable | Default | Description |
|---|---|---|
| `API_PORT` | `5000` | Flask bind port |
| `DEBUG_MODE` | `0` | Enable Flask debug mode |
| `COMMAND_TIMEOUT` | `180` | Subprocess timeout in seconds |

### `mcp_server.py` — MCP Bridge

**Entry point:** `main()` — parses args, creates `KaliToolsClient`, calls `setup_mcp_server()`, runs `mcp.run()` (stdio transport).
**Key class:** `KaliToolsClient` — HTTP client with `safe_get()` and `safe_post()` helpers that return `{"error": ..., "success": False}` on failure instead of raising.

**MCP tools registered (via `@mcp.tool()`):**

| Tool name | Maps to endpoint |
|---|---|
| `nmap_scan` | `POST /api/tools/nmap` |
| `gobuster_scan` | `POST /api/tools/gobuster` |
| `dirb_scan` | `POST /api/tools/dirb` |
| `nikto_scan` | `POST /api/tools/nikto` |
| `sqlmap_scan` | `POST /api/tools/sqlmap` |
| `metasploit_run` | `POST /api/tools/metasploit` |
| `hydra_attack` | `POST /api/tools/hydra` |
| `john_crack` | `POST /api/tools/john` |
| `wpscan_analyze` | `POST /api/tools/wpscan` |
| `enum4linux_scan` | `POST /api/tools/enum4linux` |
| `server_health` | `GET /health` |
| `execute_command` | `POST /api/command` |

**CLI arguments:**

```
--server   URL of kali_server (default: http://localhost:5000)
--timeout  Request timeout in seconds (default: 300)
--debug    Enable DEBUG log level
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Kali Linux (for `kali_server.py`) or any Linux (for `mcp_server.py`)
- Docker (optional)

### Install

```bash
# Runtime only
pip install -r requirements.txt

# With dev tools (pytest, black, isort, pylint, flake8, bandit, etc.)
pip install -e ".[dev]"
```

### Environment

```bash
cp .env.example .env
# Edit .env — do NOT commit this file
```

---

## Running the Servers

### kali_server.py (on Kali machine)

```bash
python3 kali_server.py
python3 kali_server.py --port 8080 --debug
```

### mcp_server.py (on client machine)

```bash
python3 mcp_server.py --server http://KALI_IP:5000
python3 mcp_server.py --server http://KALI_IP:5000 --debug
```

### Docker

```bash
docker-compose up -d              # Uses docker-compose.yml
docker build -t mcp-kali-server . # Manual build
docker run -p 5000:5000 mcp-kali-server
```

### Claude Desktop Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kali_mcp": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp_server.py", "--server", "http://KALI_IP:5000/"]
    }
  }
}
```

---

## Testing

```bash
# Run all tests
pytest -v

# With coverage
pytest --cov=. --cov-report=html

# Run specific file
pytest test_basic.py -v

# Max failures before stopping
pytest --maxfail=1
```

Tests live in `test_basic.py` using class-based pytest style (`class TestFeatureName`). The test suite covers:
- Module imports (`TestKaliServerImports`)
- Default configuration values (`TestConfiguration`)
- `CommandExecutor` initialization (`TestCommandExecutor`)
- Flask route registration (`TestAPIEndpoints`)

**Note:** Tests verify structure only — they do not make actual HTTP calls or spawn subprocesses. Integration tests require a live Kali Linux environment.

---

## Code Quality

All linting and formatting settings are in `pyproject.toml`.

```bash
# Format
black .
isort .

# Lint (max line length: 120)
flake8 . --max-line-length=120
pylint kali_server.py mcp_server.py

# Security scan
bandit -r kali_server.py mcp_server.py

# Dependency vulnerability check
pip-audit
safety check
```

**Key settings:**
- Line length: **120 characters** (black, isort, flake8, pylint all set to 120)
- Python target: **3.11**
- bandit skips: `B404` (subprocess import), `B603` (subprocess without shell)

---

## CI/CD (GitHub Actions)

Three jobs defined in `.github/workflows/ci.yml`, triggered on push/PR to `main`:

| Job | Steps |
|---|---|
| `lint-and-test` | flake8, pylint, pytest with coverage, upload to Codecov |
| `security` | bandit, pip-audit, safety check |
| `docker` | `docker build`, sanity run |

CodeQL static analysis runs in `.github/workflows/codeql.yml`.

Branch protection on `main` requires passing status checks before merge.

---

## Code Style Conventions

Follow PEP 8 with these specifics (see `CONTRIBUTING.md`):

**Naming:**
- Classes: `PascalCase` (e.g., `KaliToolsClient`, `CommandExecutor`)
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE` (e.g., `API_PORT`, `COMMAND_TIMEOUT`)
- Private methods: `_leading_underscore`

**Type hints:** Use `from typing import Dict, Any, Optional` — all public functions should be typed.

**Docstrings:** Google/NumPy style with `Args:` and `Returns:` sections.

**Error handling:** Catch exceptions, log with `logger.error()`, return `{"error": "...", "success": False}` — never propagate raw exceptions to callers.

**Commit message format:**
```
type: brief description

Detailed explanation if needed.

Fixes #issue_number
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `security`

---

## Security Considerations for AI Assistants

This repository exists for **educational and authorized security testing only**. When working in this codebase:

1. **Do not add new tool integrations** that bypass the existing allowlist pattern in `COMMAND_ALLOWLIST` (`kali_server.py:34-41`).
2. **Do not disable authentication prompts or add open network bindings** — the server already binds to `0.0.0.0` which must only be used in isolated/authorized environments.
3. **Input validation gaps exist** — several endpoints append `additional_args` directly into command strings (`kali_server.py:201, 240, 270, 299, 331, 428, 470, 500, 527`). Be aware of this when writing tests or documentation.
4. **Secrets must never be committed** — use `.env` (gitignored) and `.env.example` for configuration.
5. The `/api/command` endpoint uses an allowlist (`COMMAND_ALLOWLIST`) — the `execute_command` MCP tool in `mcp_server.py` sends a `command` key but the server expects an `action` key. This is a known interface mismatch.
6. The Dockerfile runs as a non-root user `mcpuser` (UID 1000) — preserve this in any Dockerfile changes.

---

## Known Issues / Stubs

- `/mcp/capabilities` and `/mcp/tools/kali_tools/<tool_name>` endpoints in `kali_server.py` are stubs that return `None` (`kali_server.py:564-573`).
- `COMMAND_ALLOWLIST` only covers 5 safe commands — the generic `execute_command` MCP tool sends a `command` string key but the endpoint expects an `action` key from the allowlist.
- `kali_server.py` health check calls `execute_command(f"which {tool}")` passing a string, but `CommandExecutor.__init__` types `command` as `list` — works only when `Popen` receives a string with `shell=False` on some platforms.

---

## Dependency Versions (pinned in requirements.txt)

| Package | Version |
|---|---|
| Flask | 2.3.2 |
| gunicorn | 22.0.0 |
| psycopg2-binary | 2.9.6 |
| requests | 2.32.4 |
| pytest | 7.4.0 |
| mcp | >=0.9.0 |

Dev dependencies (from `pyproject.toml [project.optional-dependencies]`): pytest-cov, pylint, flake8, bandit, safety, pip-audit, black, isort.
