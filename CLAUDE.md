# CLAUDE.md

Guidance for AI assistants (Claude Code and others) working in this repository.
Read this before making changes.

---

## 1. What this project is

**MCP Kali Server** is a [Model Context Protocol](https://github.com/anthropics/mcp)
bridge that exposes Kali Linux offensive-security tooling (nmap, gobuster, dirb,
nikto, sqlmap, metasploit, hydra, john, wpscan, enum4linux) to an MCP client such
as Claude Desktop or 5ire.

It is a fork of [Wh0am123/MCP-Kali-Server](https://github.com/Wh0am123/MCP-Kali-Server),
intended to evolve toward expanded AI integrations, multi-agent orchestration, and
extended security automation. Current version: **0.1.0 (Alpha)**.

> **⚠️ Authorization is mandatory.** This software executes real offensive tools.
> It is for authorized penetration testing, CTF, and education only. All work in
> this repo is defensive/dual-use under that framing — see §7 (Governing security
> model) before adding or changing any tool-execution capability.

---

## 2. Architecture

Two cooperating processes, split across a network boundary:

```
┌─────────────────────────┐         ┌──────────────────────────────────┐
│  MCP Client             │  stdio  │  mcp_server.py  (FastMCP)         │
│  (Claude Desktop, 5ire) │ ◄─────► │  - registers @mcp.tool() funcs    │
└─────────────────────────┘         │  - KaliToolsClient (HTTP client)  │
                                     └───────────────┬──────────────────┘
                                                     │  HTTP/JSON (port 5000)
                                                     ▼
                                     ┌──────────────────────────────────┐
                                     │  kali_server.py  (Flask REST API) │
                                     │  - /api/tools/<tool> endpoints    │
                                     │  - /api/command (allowlisted)     │
                                     │  - /health                        │
                                     │  - CommandExecutor → subprocess   │
                                     │  RUNS ON THE KALI MACHINE         │
                                     └──────────────────────────────────┘
```

- **`kali_server.py`** — Flask API server. Runs *on the Kali box*. Receives JSON,
  builds shell commands, runs them via `CommandExecutor` (threaded stdout/stderr
  reads + timeout handling), returns structured `{stdout, stderr, return_code,
  success, timed_out, partial_results}`. Listens on `0.0.0.0:5000`.
- **`mcp_server.py`** — FastMCP server. Runs *on the MCP client side*. Each
  `@mcp.tool()` function forwards parameters to the Flask API via
  `KaliToolsClient.safe_post`/`safe_get`. Started over stdio by the MCP client.

There is no shared in-process state; the contract between the two halves is the
HTTP JSON API. When you add or change a tool, you almost always edit **both**
files: the Flask endpoint in `kali_server.py` *and* the matching `@mcp.tool()` in
`mcp_server.py`. Keep parameter names and defaults in sync across the boundary.

---

## 3. Repository layout

| Path | Purpose |
|------|---------|
| `kali_server.py` | Flask REST API; command execution; tool endpoints. |
| `mcp_server.py` | FastMCP server + `KaliToolsClient`; MCP tool definitions. |
| `test_basic.py` | Pytest smoke tests (imports, config, `CommandExecutor`, route registration). |
| `pyproject.toml` | Packaging, console scripts, and tool config (black, isort, pylint, pytest, coverage, bandit). |
| `requirements.txt` | Pinned runtime deps (note: looser ranges in `pyproject.toml`). |
| `Dockerfile` | Multi-stage build, non-root `mcpuser`, healthcheck. Default CMD runs the API server. |
| `docker-compose.yml` | Single `kali-server` service, resource limits, `no-new-privileges`. |
| `.env.example` | Env var template (`API_PORT`, `DEBUG_MODE`, `COMMAND_TIMEOUT`, `KALI_SERVER_URL`, `REQUEST_TIMEOUT`). |
| `.github/workflows/` | CI (`ci.yml`), release (`release.yml`), CodeQL (`codeql.yml`), branch-protection reminder. |
| `CONTRIBUTING.md` | Code style, commit format, PR process — **authoritative for conventions**. |
| `SECURITY.md` | Vulnerability reporting and security guidance. |
| `BRANCH_PROTECTION.md` | Branch protection setup for `main`. |
| `CHANGELOG.md` / `RELEASE_*.md` | Version history and release process. |

---

## 4. Development workflow

**Setup**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"        # installs pytest, pylint, flake8, bandit, black, isort, etc.
cp .env.example .env           # then edit
```

**Run locally**
```bash
python3 kali_server.py --port 5000 --debug          # API server (on Kali)
python3 mcp_server.py --server http://LINUX_IP:5000  # MCP server (on client)
```

**Quality gates** (run all before committing — mirrors `CONTRIBUTING.md` and CI):
```bash
black . && isort .                       # format (line-length 120)
flake8 . --max-line-length=120           # lint
pylint kali_server.py mcp_server.py      # lint
bandit -r kali_server.py mcp_server.py   # security scan
pytest -v                                # tests
pytest --cov=. --cov-report=term         # tests with coverage
```

**Docker**
```bash
docker-compose up -d                     # or: docker build -t mcp-kali-server . && docker run -p 5000:5000 mcp-kali-server
```

---

## 5. Conventions (enforced by `pyproject.toml` + `CONTRIBUTING.md`)

- **Python ≥ 3.11.** Line length **120**. 4-space indent, no tabs.
- **Formatting:** Black + isort (`profile = "black"`). Run them; don't hand-format.
- **Naming:** `PascalCase` classes, `snake_case` functions/vars, `UPPER_SNAKE_CASE`
  constants, `_leading_underscore` for private helpers.
- **Type hints** on all public functions; `Dict[str, Any]`, `Optional[...]` from `typing`.
- **Docstrings:** triple-quoted with `Args:` / `Returns:` / `Raises:` sections
  (Google-ish style — match the existing endpoints/tools exactly).
- **Logging:** use the module `logger`; never log secrets, passwords, or hashes.
- **Error handling:** every endpoint wraps work in try/except, logs the traceback,
  and returns a JSON error with an appropriate HTTP status. Don't leak internals to
  the client beyond what existing endpoints already do.
- **Commit messages:** `type: brief description` where type ∈
  `feat|fix|docs|style|refactor|test|chore|security`. Reference issues (`Fixes #N`).
  Add a `Security: <level>` trailer for security-relevant fixes.
- **Every code change** should update tests, and docs (`README.md` / `CHANGELOG.md`)
  when behavior or interfaces change.

---

## 6. CI / release / branch rules

- **CI (`ci.yml`)** runs on push/PR to `main`: job **Lint and Test** (flake8 +
  pylint non-blocking, then `pytest --cov ... --maxfail=1`), job **Security
  Scanning** (bandit, pip-audit, safety — non-blocking), job **Docker Build**.
- **`main` is protected:** no force-push/delete, required status checks
  (**Lint and Test**, **CodeQL / Analyze**), required PR review. Do not push to
  `main` directly.
- **Release (`release.yml`)** triggers on `v*` tags: runs tests, builds + saves a
  Docker image, creates a GitHub release. Follow SemVer.
- **Branch discipline for assistants:** develop on the assigned feature branch,
  commit with clear messages, push with `git push -u origin <branch>`, then open a
  **draft PR**. Never push to a branch you weren't told to.

---

## 7. Governing security model — the Kali MCP is an audited cyber range

This project must be treated **not** as a convenience wrapper around offensive
tools, but as an **audited cyber-range control plane**. Defense-by-restriction
alone is insufficient against agent-driven operations; bounded offensive
capability has to be mastered inside controlled, instrumented environments and
distilled into defensive-only outputs. Two facts drive the design:

1. **Multi-step intent is invisible at the single-call level.** A harmful
   operation can be spread across recon → enumeration → probing → validation →
   reporting, where each call looks benign but the *trajectory* is offensive or
   out of scope. Per-call guardrails are necessary but **insufficient**;
   governance must operate at the engagement, session, and trajectory level.
2. **Local/open-weight models remove vendor-side visibility.** Once a model is
   local, fine-tuned, or externally orchestrated, platform safeguards cannot be
   assumed to observe the sequence. **The control boundary must live in the MCP
   server, the engagement policy, and the execution environment.**

> **The tool call is not the unit of trust. The lifecycle trace is.**

**Minimum control model (the target architecture):**

```
Engagement Policy → Tool Request → Scope Check → Execution Gate
   → Evidence Capture → Audit Chain → Trajectory Review
   → Defensive Distillation → Authorised Export
```

Every run should be bound to: engagement ID, target scope, operator identity,
tool profile, timestamp, command intent, input parameters, output summary, and
the policy decision. The audit chain is the lifecycle spine. The MCP boundary is
where **authorization, scope, tool access, evidence capture, and export control**
are enforced — the model proposes, the server decides admissibility under the
current Rules of Engagement.

The Kali MCP plays three roles at once:
- **Tool gateway** — real offensive tools are never exposed to the model unmediated.
- **Governance boundary** — every action is checked against engagement scope,
  safety policy, and cumulative trajectory.
- **Distillation pipeline** — offensive runs may only *leave* the boundary as
  defensive artifacts.

**Authorised exports (defensive memory only):** vulnerability summaries,
root-cause analysis, hardening guidance, patch suggestions, regression tests,
detection logic (Sigma / YARA / Suricata-style rules), misconfiguration reports,
risk registers, sanitized attack-path diagrams.

**Disallowed exports:** reusable exploit chains, target-specific attack playbooks,
weaponized payloads, credential material, stealth/persistence instructions, or
unredacted traces that let offensive capability leave the range.

> Thesis: **The Kali MCP is the audited cyber range. The audit chain is the
> lifecycle spine. Distillation is the only authorised export path. Offensive
> runs leave containment as defensive artifacts, never as transferable capability.**

**What this means for changes you make here today:**
- New capabilities should move the code *toward* this model (scope checks,
  engagement binding, structured audit logging, allowlists), never away from it.
- Prefer **allowlists over free-form execution.** The `/api/command` endpoint
  already gates on `COMMAND_ALLOWLIST` — extend that pattern; don't reintroduce
  unrestricted command execution.
- Validate and constrain every parameter that reaches a subprocess. Never build
  shell strings from unsanitized `additional_args` without a clear, reviewed
  reason. Treat command injection as the primary threat.
- When emitting results/reports, bias toward defensive artifacts; do not generate
  weaponized or target-specific offensive playbooks.

---

## 8. Known issues & gotchas (verify before relying on these paths)

These are real inconsistencies in the current code. Be careful — and fixing them
is welcome, but do so deliberately with tests:

- **`CommandExecutor` expects a `list`, but tool endpoints pass a `str`.**
  `CommandExecutor.execute()` calls `subprocess.Popen(self.command, shell=False)`.
  `/api/command` correctly passes a list from `COMMAND_ALLOWLIST` (e.g.
  `["ls", "-l"]`). But `nmap()`, `gobuster()`, etc. build an f-string and call
  `execute_command("nmap ...")`. With `shell=False` a string is treated as a single
  program name, so those endpoints do **not** work as written. Any fix must
  preserve the `shell=False` + allowlist security posture (e.g. tokenize safely,
  not switch to `shell=True`).
- **`/api/command` contract mismatch.** The Flask endpoint requires
  `{"action": "<allowlist-key>"}`, but `KaliToolsClient.execute_command` (and the
  `execute_command` MCP tool) send `{"command": "<string>"}`. The README also still
  documents `{"command": "whoami"}`. The MCP `execute_command` tool therefore won't
  succeed against the allowlisted endpoint — reconcile client, server, and docs
  together if you touch this.
- **Default drift:** `mcp_server.nmap_scan` defaults `scan_type="-sV"` while
  `kali_server.nmap` defaults `"-sCV"`. README's example uses `scan_type: "quick"`
  which is not a valid nmap flag. Keep defaults consistent across the boundary and
  with docs.
- **Unimplemented stubs:** `/mcp/capabilities` and `/mcp/tools/kali_tools/<tool>`
  in `kali_server.py` are `pass` (no-ops).
- **Duplicate workflow:** `.github/workflows/codeql.yml` and `codelql.yml` are
  identical (the latter is a typo'd duplicate).
- **Dependency version skew:** `requirements.txt` pins (e.g. `gunicorn==22.0.0`,
  `requests==2.32.4`) differ from the looser ranges in `pyproject.toml`. Update
  both intentionally.

---

## 9. Quick reference — current tools

Both halves expose these (Flask endpoint ↔ MCP tool): `nmap` ↔ `nmap_scan`,
`gobuster` ↔ `gobuster_scan`, `dirb` ↔ `dirb_scan`, `nikto` ↔ `nikto_scan`,
`sqlmap` ↔ `sqlmap_scan`, `metasploit` ↔ `metasploit_run`, `hydra` ↔
`hydra_attack`, `john` ↔ `john_crack`, `wpscan` ↔ `wpscan_analyze`, `enum4linux`
↔ `enum4linux_scan`, plus `/health` ↔ `server_health` and `/api/command` ↔
`execute_command`.

**To add a tool:** add the Flask endpoint in `kali_server.py` (validate inputs,
wrap in try/except, return the standard result dict), add the matching
`@mcp.tool()` in `mcp_server.py` (same params/defaults, forward via
`safe_post`), add it to `/health`'s `essential_tools` if appropriate, write a
test in `test_basic.py`, and update `README.md` + `CHANGELOG.md`.
