#!/usr/bin/env python3
"""
Kali Tools API Server (Hardened)

Security Improvements:
- No shell=True usage
- Argument vectors passed directly to subprocess
- Input validation & sanitization
- Optional restrictive mode for generic command execution
- Timeouts and output size limiting
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_PORT = int(os.environ.get("API_PORT", "5000"))
DEBUG_MODE = os.environ.get("DEBUG_MODE", "0").lower() in {"1", "true", "yes", "y"}
COMMAND_TIMEOUT = int(os.environ.get("COMMAND_TIMEOUT", "180"))
MAX_OUTPUT_BYTES = int(os.environ.get("MAX_OUTPUT_BYTES", str(2 * 1024 * 1024)))  # 2MB
ALLOW_GENERIC_COMMANDS = os.environ.get("ALLOW_GENERIC_COMMANDS", "0").lower() in {"1", "true", "yes"}
ALLOWED_COMMANDS = set(
    filter(
        None,
        [c.strip() for c in os.environ.get("ALLOWED_COMMANDS", "id,uname,whoami").split(",")],
    )
)
# Pattern to restrict additional arguments (flags and simple key=value only)
SAFE_ADDITIONAL_ARG_PATTERN = re.compile(r"^[-]{1,2}[\w][\w\-]*(=[\w./:@%+,[\]-]+)?$")
# Logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
app = Flask(__name__)
# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------
HOSTNAME_REGEX = re.compile(r"^[a-zA-Z0-9._-]{1,253}$")
URL_REGEX = re.compile(r"^https?://[a-zA-Z0-9._:%/\-?=&+#~]+$")

def validate_hostname_or_ip(value: str, field: str = "target") -> str:
    if not value:
        raise ValueError(f"{field} is required")
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if not HOSTNAME_REGEX.match(value):
        raise ValueError(f"Invalid {field}: {value}")
    return value

def validate_url(value: str, field: str = "url") -> str:
    if not value:
        raise ValueError(f"{field} is required")
    if not URL_REGEX.match(value):
        raise ValueError(f"Invalid {field}: {value}")
    return value

def validate_ports(value: str) -> str:
    if not value:
        return value
    if not re.fullmatch(r"[0-9,\-]+", value):
        raise ValueError(f"Invalid ports specification: {value}")
    return value

def sanitize_wordlist_path(path: str) -> str:
    p = Path(path)
    allowed_prefixes = [Path("/usr/share/wordlists"), Path("/tmp")]
    if not p.is_absolute() or not any(str(p).startswith(str(prefix)) for prefix in allowed_prefixes):
        raise ValueError(f"Wordlist path not permitted: {path}")
    return str(p)

def parse_additional_args(raw: str) -> List[str]:
    if not raw:
        return []
    try:
        parts = shlex.split(raw, posix=True)
    except ValueError as exc:
        raise ValueError(f"Unable to parse additional_args: {exc}") from exc
    safe: List[str] = []
    for part in parts:
        if part.startswith("-"):
            if not SAFE_ADDITIONAL_ARG_PATTERN.match(part):
                raise ValueError(f"Unsafe flag detected: {part}")
            safe.append(part)
        else:
            if re.search(r"[;&|`$><(){}]", part):
                raise ValueError(f"Unsafe argument token: {part}")
            safe.append(part)
    return safe

def secure_module_name(module: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_/]+", module):
        raise ValueError(f"Invalid module name: {module}")
    return module

def validate_msf_option_key(k: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", k):
        raise ValueError(f"Invalid Metasploit option key: {k}")
    return k

def validate_msf_option_value(v: Any) -> str:
    if isinstance(v, (int, float)):
        return str(v)
    if not isinstance(v, str):
        raise ValueError("Option values must be string or numeric")
    if re.search(r"[\n\r;`|&<>$]", v):
        raise ValueError("Invalid characters in option value")
    return v

def enforce_allowed_command(cmd: str) -> None:
    if cmd not in ALLOWED_COMMANDS:
        raise ValueError(f"Command '{cmd}' not permitted")
# ---------------------------------------------------------------------------
# Command Execution
# ---------------------------------------------------------------------------
class CommandExecutor:
    """Execute a command vector securely (no shell)."""
    def __init__(self, argv: Sequence[str], timeout: int = COMMAND_TIMEOUT):
        self.argv = list(argv)
        self.timeout = timeout
    def execute(self) -> Dict[str, Any]:
        logger.info("Executing: %s", " ".join(shlex.quote(a) for a in self.argv))
        try:
            proc = subprocess.Popen(
                self.argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(timeout=self.timeout)
            if len(stdout.encode()) > MAX_OUTPUT_BYTES:
                stdout = stdout.encode()[:MAX_OUTPUT_BYTES].decode(errors="ignore") + "\n[TRUNCATED]"
            if len(stderr.encode()) > MAX_OUTPUT_BYTES:
                stderr = stderr.encode()[:MAX_OUTPUT_BYTES].decode(errors="ignore") + "\n[TRUNCATED]"
            return {
                "argv": self.argv,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": proc.returncode,
                "success": proc.returncode == 0,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            return {
                "argv": self.argv,
                "stdout": "",
                "stderr": f"Process timed out after {self.timeout}s",
                "return_code": -1,
                "success": False,
                "timed_out": True,
            }
        except FileNotFoundError:
            return {
                "argv": self.argv,
                "stdout": "",
                "stderr": "Executable not found",
                "return_code": 127,
                "success": False,
                "timed_out": False,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Execution error")
            return {
                "argv": self.argv,
                "stdout": "",
                "stderr": f"Execution error: {exc}",
                "return_code": -1,
                "success": False,
                "timed_out": False,
            }

def run(argv: Sequence[str]) -> Dict[str, Any]:
    return CommandExecutor(argv).execute()

def json_error(msg: str, status: int = 400):
    return jsonify({"error": msg}), status
# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.route("/api/command", methods=["POST"])
def generic_command():
    if not ALLOW_GENERIC_COMMANDS:
        return json_error("Generic command execution disabled by server policy", 403)
    data = request.get_json(silent=True) or {}
    raw = data.get("command", "")
    if not raw:
        return json_error("command is required")
    try:
        parts = shlex.split(raw, posix=True)
    except ValueError as exc:
        return json_error(f"Unable to parse command: {exc}")
    if not parts:
        return json_error("Empty command")
    try:
        enforce_allowed_command(parts[0])
    except ValueError as exc:
        return json_error(str(exc), 403)
    for token in parts[1:]:
        if re.search(r"[;&|`$><]", token):
            return json_error(f"Disallowed token: {token}")
    result = run(parts)
    return jsonify(result)
@app.route("/api/tools/nmap", methods=["POST"])
def nmap():
    data = request.get_json(silent=True) or {}
    try:
        target = validate_hostname_or_ip(data.get("target", ""))
        scan_type = data.get("scan_type", "-sCV")
        ports = validate_ports(data.get("ports", "")) if data.get("ports") else ""
        additional_args = parse_additional_args(data.get("additional_args", "-T4 -Pn"))
        argv: List[str] = ["nmap"]
        if scan_type:
            argv.extend(shlex.split(scan_type))
        if ports:
            argv.extend(["-p", ports])
        argv.extend(additional_args)
        argv.append(target)
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
@app.route("/api/tools/gobuster", methods=["POST"])
def gobuster():
    data = request.get_json(silent=True) or {}
    try:
        url = validate_url(data.get("url", ""))
        mode = data.get("mode", "dir")
        if mode not in {"dir", "dns", "fuzz", "vhost"}:
            raise ValueError(f"Invalid mode: {mode}")
        wordlist = sanitize_wordlist_path(data.get("wordlist", "/usr/share/wordlists/dirb/common.txt"))
        additional_args = parse_additional_args(data.get("additional_args", ""))
        argv = ["gobuster", mode, "-u", url, "-w", wordlist]
        argv.extend(additional_args)
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
@app.route("/api/tools/dirb", methods=["POST"])
def dirb():
    data = request.get_json(silent=True) or {}
    try:
        url = validate_url(data.get("url", ""))
        wordlist = sanitize_wordlist_path(data.get("wordlist", "/usr/share/wordlists/dirb/common.txt"))
        additional_args = parse_additional_args(data.get("additional_args", ""))
        argv = ["dirb", url, wordlist]
        argv.extend(additional_args)
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
@app.route("/api/tools/nikto", methods=["POST"])
def nikto():
    data = request.get_json(silent=True) or {}
    try:
        target = validate_hostname_or_ip(data.get("target", ""))
        additional_args = parse_additional_args(data.get("additional_args", ""))
        argv = ["nikto", "-h", target]
        argv.extend(additional_args)
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
@app.route("/api/tools/sqlmap", methods=["POST"])
def sqlmap():
    data = request.get_json(silent=True) or {}
    try:
        url = validate_url(data.get("url", ""))
        post_data = data.get("data", "")
        if post_data and re.search(r"[;&|`$<>]", post_data):
            raise ValueError("Unsafe characters in data payload")
        additional_args = parse_additional_args(data.get("additional_args", ""))
        argv = ["sqlmap", "-u", url, "--batch"]
        if post_data:
            argv.append(f"--data={post_data}")
        argv.extend(additional_args)
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
@app.route("/api/tools/metasploit", methods=["POST"])
def metasploit():
    data = request.get_json(silent=True) or {}
    try:
        module = secure_module_name(data.get("module", ""))
        if not module:
            raise ValueError("module is required")
        options = data.get("options", {})
        if not isinstance(options, dict):
            raise ValueError("options must be an object")
        lines = [f"use {module}"]
        for k, v in options.items():
            k_s = validate_msf_option_key(k)
            v_s = validate_msf_option_value(v)
            lines.append(f"set {k_s} {v_s}")
        lines.append("exploit")
        with tempfile.NamedTemporaryFile("w", delete=False, prefix="msf_", suffix=".rc") as tf:
            tf.write("\n".join(lines) + "\n")
            rc_path = tf.name
        argv = ["msfconsole", "-q", "-r", rc_path]
    except ValueError as exc:
        return json_error(str(exc))
    result = run(argv)
    try:
        os.remove(rc_path)
    except OSError:
        pass
    return jsonify(result)
@app.route("/api/tools/hydra", methods=["POST"])
def hydra():
    data = request.get_json(silent=True) or {}
    try:
        target = validate_hostname_or_ip(data.get("target", ""))
        service = data.get("service", "")
        if not service or not re.fullmatch(r"[a-zA-Z0-9_]+", service):
            raise ValueError("Invalid service")
        username = data.get("username", "")
        username_file = data.get("username_file", "")
        password = data.get("password", "")
        password_file = data.get("password_file", "")
        if not (username or username_file) or not (password or password_file):
            raise ValueError("Provide username/username_file and password/password_file")
        additional_args = parse_additional_args(data.get("additional_args", ""))
        argv = ["hydra", "-t", "4"]
        if username:
            argv.extend(["-l", username])
        elif username_file:
            argv.extend(["-L", username_file])
        if password:
            argv.extend(["-p", password])
        elif password_file:
            argv.extend(["-P", password_file])
        argv.extend(additional_args)
        argv.extend([target, service])
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
@app.route("/api/tools/john", methods=["POST"])
def john():
    data = request.get_json(silent=True) or {}
    try:
        hash_file = data.get("hash_file", "")
        if not hash_file or not Path(hash_file).is_file():
            raise ValueError("Valid hash_file required")
        wordlist = sanitize_wordlist_path(data.get("wordlist", "/usr/share/wordlists/rockyou.txt"))
        fmt = data.get("format", "")
        if fmt and not re.fullmatch(r"[A-Za-z0-9_]+", fmt):
            raise ValueError("Invalid format")
        additional_args = parse_additional_args(data.get("additional_args", ""))
        argv = ["john"]
        if fmt:
            argv.append(f"--format={fmt}")
        if wordlist:
            argv.append(f"--wordlist={wordlist}")
        argv.extend(additional_args)
        argv.append(hash_file)
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
@app.route("/api/tools/wpscan", methods=["POST"])
def wpscan():
    data = request.get_json(silent=True) or {}
    try:
        url = validate_url(data.get("url", ""))
        additional_args = parse_additional_args(data.get("additional_args", ""))
        argv = ["wpscan", "--url", url]
        argv.extend(additional_args)
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
@app.route("/api/tools/enum4linux", methods=["POST"])
def enum4linux():
    data = request.get_json(silent=True) or {}
    try:
        target = validate_hostname_or_ip(data.get("target", ""))
        additional_args = parse_additional_args(data.get("additional_args", "-a"))
        argv = ["enum4linux"]
        argv.extend(additional_args)
        argv.append(target)
    except ValueError as exc:
        return json_error(str(exc))
    return jsonify(run(argv))
# ---------------------------------------------------------------------------
# Health & Capabilities
# ---------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    essential = ["nmap", "gobuster", "dirb", "nikto"]
    tools_status = {tool: bool(shutil.which(tool)) for tool in essential}
    return jsonify(
        {
            "status": "healthy",
            "tools_status": tools_status,
            "all_essential_tools_available": all(tools_status.values()),
            "generic_commands_enabled": ALLOW_GENERIC_COMMANDS,
        }
    )
@app.route("/mcp/capabilities", methods=["GET"])
def capabilities():
    return jsonify(
        {
            "tools": [
                "nmap",
                "gobuster",
                "dirb",
                "nikto",
                "sqlmap",
                "metasploit",
                "hydra",
                "john",
                "wpscan",
                "enum4linux",
            ],
            "generic_command": ALLOW_GENERIC_COMMANDS,
            "security": {
                "shell": False,
                "validation": True,
                "timeout_seconds": COMMAND_TIMEOUT,
                "max_output_bytes": MAX_OUTPUT_BYTES,
            },
        }
    )
@app.route("/mcp/tools/kali_tools/<tool_name>", methods=["POST"])
def execute_tool(tool_name: str):  # placeholder for MCP integration
    return json_error("Direct tool execution wrapper not yet implemented", 501)
# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Hardened Kali Linux Tools API Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--port", type=int, default=API_PORT, help=f"Port (default {API_PORT})")
    return parser.parse_args()
if __name__ == "__main__":
    args = parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    if args.port != API_PORT:
        API_PORT = args.port  # type: ignore
    logger.info("Starting Hardened Kali Linux Tools API Server on port %d", API_PORT)
    app.run(host="0.0.0.0", port=API_PORT, debug=DEBUG_MODE)