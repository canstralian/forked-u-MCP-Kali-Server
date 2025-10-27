#!/usr/bin/env python3

# This script connect the MCP AI agent to Kali Linux terminal and API Server.

# some of the code here was inspired from https://github.com/whit3rabbit0/project_astro , be sure to check them out

import argparse
import logging
import os
import subprocess
import sys
import tempfile
import threading
import traceback
from typing import Any, Dict

from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuration
API_PORT = int(os.environ.get("API_PORT", 5000))
DEBUG_MODE = os.environ.get("DEBUG_MODE", "0").lower() in ("1", "true", "yes", "y")
COMMAND_TIMEOUT = 180  # 5 minutes default timeout

# Only allow execution of these command names via the /api/command endpoint
# Add to this dictionary as needed for safe operations
COMMAND_ALLOWLIST = {
    "list": ["ls", "-l"],
    "stat": ["stat", "/etc/passwd"],
    "uptime": ["uptime"],
    "whoami": ["whoami"],
    "date": ["date"],
    # Add other safe commands here
}

app = Flask(__name__)


class CommandExecutor:
    """Class to handle command execution with better timeout management"""

    def __init__(self, command: list, timeout: int = COMMAND_TIMEOUT):
        self.command = command
        self.timeout = timeout
        self.process = None
        self.stdout_data = ""
        self.stderr_data = ""
        self.stdout_thread = None
        self.stderr_thread = None
        self.return_code = None
        self.timed_out = False

    def _read_stdout(self):
        """Thread function to continuously read stdout"""
        for line in iter(self.process.stdout.readline, ""):
            self.stdout_data += line

    def _read_stderr(self):
        """Thread function to continuously read stderr"""
        for line in iter(self.process.stderr.readline, ""):
            self.stderr_data += line

    def execute(self) -> Dict[str, Any]:
        """Execute the command and handle timeout gracefully"""
        logger.info("Executing command: %s", self.command)

        try:
            self.process = subprocess.Popen(
                self.command,
                shell=False,  # Run command directly, not via shell
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Start threads to read output continuously
            self.stdout_thread = threading.Thread(target=self._read_stdout)
            self.stderr_thread = threading.Thread(target=self._read_stderr)
            self.stdout_thread.daemon = True
            self.stderr_thread.daemon = True
            self.stdout_thread.start()
            self.stderr_thread.start()

            # Wait for the process to complete or timeout
            try:
                self.return_code = self.process.wait(timeout=self.timeout)
                # Process completed, join the threads
                self.stdout_thread.join()
                self.stderr_thread.join()
            except subprocess.TimeoutExpired:
                # Process timed out but we might have partial results
                self.timed_out = True
                logger.warning("Command timed out after %s seconds. Terminating process.", self.timeout)

                # Try to terminate gracefully first
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)  # Give it 5 seconds to terminate
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    logger.warning("Process not responding to termination. Killing.")
                    self.process.kill()

                # Update final output
                self.return_code = -1

            # Always consider it a success if we have output, even with timeout
            success = True if self.timed_out and (self.stdout_data or self.stderr_data) else (self.return_code == 0)

            return {
                "stdout": self.stdout_data,
                "stderr": self.stderr_data,
                "return_code": self.return_code,
                "success": success,
                "timed_out": self.timed_out,
                "partial_results": self.timed_out and (self.stdout_data or self.stderr_data),
            }

        except Exception as e:
            logger.error("Error executing command: %s", str(e))
            logger.error(traceback.format_exc())
            return {
                "stdout": self.stdout_data,
                "stderr": f"Error executing command: {str(e)}\n{self.stderr_data}",
                "return_code": -1,
                "success": False,
                "timed_out": False,
                "partial_results": bool(self.stdout_data or self.stderr_data),
            }


def execute_command(command: list) -> Dict[str, Any]:
    """
    Execute a command and return the result

    Args:
        command: The command to execute, as a list of strings

    Returns:
        A dictionary containing the stdout, stderr, and return code
    """
    executor = CommandExecutor(command)
    return executor.execute()


@app.route("/api/command", methods=["POST"])
def generic_command():
    """Execute a safe command from the allowlist provided in the request."""
    try:
        params = request.json
        action = params.get("action", "")

        if not action or action not in COMMAND_ALLOWLIST:
            logger.warning("Command endpoint called with unknown or missing action parameter: %s", action)
            return (
                jsonify(
                    {"error": "Action parameter is required and must be one of: " + ", ".join(COMMAND_ALLOWLIST.keys())}
                ),
                400,
            )

        command_to_run = COMMAND_ALLOWLIST[action]
        result = execute_command(command_to_run)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in command endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/nmap", methods=["POST"])
def nmap():
    """Execute nmap scan with the provided parameters."""
    try:
        params = request.json
        target = params.get("target", "")
        scan_type = params.get("scan_type", "-sCV")
        ports = params.get("ports", "")
        additional_args = params.get("additional_args", "-T4 -Pn")

        if not target:
            logger.warning("Nmap called without target parameter")
            return jsonify({"error": "Target parameter is required"}), 400

        # Build command as a list to prevent command injection
        command = ["nmap"]
        command.extend(scan_type.split())

        if ports:
            command.extend(["-p", ports])

        if additional_args:
            command.extend(additional_args.split())

        command.append(target)

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in nmap endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/gobuster", methods=["POST"])
def gobuster():
    """Execute gobuster with the provided parameters."""
    try:
        params = request.json
        url = params.get("url", "")
        mode = params.get("mode", "dir")
        wordlist = params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("Gobuster called without URL parameter")
            return jsonify({"error": "URL parameter is required"}), 400

        # Validate mode
        if mode not in ["dir", "dns", "fuzz", "vhost"]:
            logger.warning("Invalid gobuster mode: %s", mode)
            return jsonify({"error": f"Invalid mode: {mode}. Must be one of: dir, dns, fuzz, vhost"}), 400

        # Build command as a list to prevent command injection
        command = ["gobuster", mode, "-u", url, "-w", wordlist]

        if additional_args:
            command.extend(additional_args.split())

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in gobuster endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/dirb", methods=["POST"])
def dirb():
    """Execute dirb with the provided parameters."""
    try:
        params = request.json
        url = params.get("url", "")
        wordlist = params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("Dirb called without URL parameter")
            return jsonify({"error": "URL parameter is required"}), 400

        # Build command as a list to prevent command injection
        command = ["dirb", url, wordlist]

        if additional_args:
            command.extend(additional_args.split())

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in dirb endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/nikto", methods=["POST"])
def nikto():
    """Execute nikto with the provided parameters."""
    try:
        params = request.json
        target = params.get("target", "")
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("Nikto called without target parameter")
            return jsonify({"error": "Target parameter is required"}), 400

        # Build command as a list to prevent command injection
        command = ["nikto", "-h", target]

        if additional_args:
            command.extend(additional_args.split())

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in nikto endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/sqlmap", methods=["POST"])
def sqlmap():
    """Execute sqlmap with the provided parameters."""
    try:
        params = request.json
        url = params.get("url", "")
        data = params.get("data", "")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("SQLMap called without URL parameter")
            return jsonify({"error": "URL parameter is required"}), 400

        # Build command as a list to prevent command injection
        command = ["sqlmap", "-u", url, "--batch"]

        if data:
            command.extend(["--data", data])

        if additional_args:
            command.extend(additional_args.split())

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in sqlmap endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/metasploit", methods=["POST"])
def metasploit():
    """Execute metasploit module with the provided parameters."""
    try:
        params = request.json
        module = params.get("module", "")
        options = params.get("options", {})

        if not module:
            logger.warning("Metasploit called without module parameter")
            return jsonify({"error": "Module parameter is required"}), 400

        # Create an MSF resource script
        resource_content = f"use {module}\n"
        for key, value in options.items():
            resource_content += f"set {key} {value}\n"
        resource_content += "exploit\n"

        # Save resource script to a secure temporary file
        fd, resource_file = tempfile.mkstemp(suffix=".rc", prefix="mcp_msf_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(resource_content)

            # Build command as a list to prevent command injection
            command = ["msfconsole", "-q", "-r", resource_file]
            result = execute_command(command)
        finally:
            # Clean up the temporary file
            try:
                os.remove(resource_file)
            except Exception as e:
                logger.warning("Error removing temporary resource file: %s", str(e))

        return jsonify(result)
    except Exception as e:
        logger.error("Error in metasploit endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/hydra", methods=["POST"])
def hydra():
    """Execute hydra with the provided parameters."""
    try:
        params = request.json
        target = params.get("target", "")
        service = params.get("service", "")
        username = params.get("username", "")
        username_file = params.get("username_file", "")
        password = params.get("password", "")
        password_file = params.get("password_file", "")
        additional_args = params.get("additional_args", "")

        if not target or not service:
            logger.warning("Hydra called without target or service parameter")
            return jsonify({"error": "Target and service parameters are required"}), 400

        if not (username or username_file) or not (password or password_file):
            logger.warning("Hydra called without username/password parameters")
            return jsonify({"error": "Username/username_file and password/password_file are required"}), 400

        # Build command as a list to prevent command injection
        command = ["hydra", "-t", "4"]

        if username:
            command.extend(["-l", username])
        elif username_file:
            command.extend(["-L", username_file])

        if password:
            command.extend(["-p", password])
        elif password_file:
            command.extend(["-P", password_file])

        if additional_args:
            command.extend(additional_args.split())

        command.extend([target, service])

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in hydra endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/john", methods=["POST"])
def john():
    """Execute john with the provided parameters."""
    try:
        params = request.json
        hash_file = params.get("hash_file", "")
        wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        format_type = params.get("format", "")
        additional_args = params.get("additional_args", "")

        if not hash_file:
            logger.warning("John called without hash_file parameter")
            return jsonify({"error": "Hash file parameter is required"}), 400

        # Build command as a list to prevent command injection
        command = ["john"]

        if format_type:
            command.append(f"--format={format_type}")

        if wordlist:
            command.append(f"--wordlist={wordlist}")

        if additional_args:
            command.extend(additional_args.split())

        command.append(hash_file)

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in john endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/wpscan", methods=["POST"])
def wpscan():
    """Execute wpscan with the provided parameters."""
    try:
        params = request.json
        url = params.get("url", "")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("WPScan called without URL parameter")
            return jsonify({"error": "URL parameter is required"}), 400

        # Build command as a list to prevent command injection
        command = ["wpscan", "--url", url]

        if additional_args:
            command.extend(additional_args.split())

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in wpscan endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/tools/enum4linux", methods=["POST"])
def enum4linux():
    """Execute enum4linux with the provided parameters."""
    try:
        params = request.json
        target = params.get("target", "")
        additional_args = params.get("additional_args", "-a")

        if not target:
            logger.warning("Enum4linux called without target parameter")
            return jsonify({"error": "Target parameter is required"}), 400

        # Build command as a list to prevent command injection
        command = ["enum4linux"]
        command.extend(additional_args.split())
        command.append(target)

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error("Error in enum4linux endpoint: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    # Check if essential tools are installed
    essential_tools = ["nmap", "gobuster", "dirb", "nikto"]
    tools_status = {}

    for tool in essential_tools:
        try:
            result = execute_command(["which", tool])
            tools_status[tool] = result["success"]
        except Exception as e:
            logger.debug("Error checking tool %s: %s", tool, str(e))
            tools_status[tool] = False

    all_essential_tools_available = all(tools_status.values())

    return jsonify(
        {
            "status": "healthy",
            "message": "Kali Linux Tools API Server is running",
            "tools_status": tools_status,
            "all_essential_tools_available": all_essential_tools_available,
        }
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the Kali Linux API Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--port", type=int, default=API_PORT, help=f"Port for the API server (default: {API_PORT})")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Set configuration from command line arguments
    if args.debug:
        DEBUG_MODE = True
        os.environ["DEBUG_MODE"] = "1"
        logger.setLevel(logging.DEBUG)

    if args.port != API_PORT:
        API_PORT = args.port

    logger.info("Starting Kali Linux Tools API Server on port %s", API_PORT)
    app.run(host="0.0.0.0", port=API_PORT, debug=DEBUG_MODE)
