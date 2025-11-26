#!/usr/bin/env python3

# This script connect the MCP AI agent to Kali Linux terminal and API Server.

# some of the code here was inspired from https://github.com/whit3rabbit0/project_astro , be sure to check them out

import argparse
import logging
import os
import subprocess
import sys
import traceback
import threading
from typing import Dict, Any
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
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
        for line in iter(self.process.stdout.readline, ''):
            self.stdout_data += line

    def _read_stderr(self):
        """Thread function to continuously read stderr"""
        for line in iter(self.process.stderr.readline, ''):
            self.stderr_data += line

    def execute(self) -> Dict[str, Any]:
        """Execute the command and handle timeout gracefully"""
        logger.info(f"Executing command: {self.command}")

        try:
            self.process = subprocess.Popen(
                self.command,
                shell=False,  # Run command directly, not via shell
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
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
                logger.warning(f"Command timed out after {self.timeout} seconds. Terminating process.")

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
                "partial_results": self.timed_out and (self.stdout_data or self.stderr_data)
            }

        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "stdout": self.stdout_data,
                "stderr": f"Error executing command: {str(e)}\n{self.stderr_data}",
                "return_code": -1,
                "success": False,
                "timed_out": False,
                "partial_results": bool(self.stdout_data or self.stderr_data)
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
            logger.warning(f"Command endpoint called with unknown or missing action parameter: {action}")
            return jsonify({
                "error": "Action parameter is required and must be one of: " + ", ".join(COMMAND_ALLOWLIST.keys())
            }), 400

        command_to_run = COMMAND_ALLOWLIST[action]
        result = execute_command(command_to_run)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in command endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


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
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"nmap {scan_type}"

        if ports:
            command += f" -p {ports}"

        if additional_args:
            # Basic validation for additional args - more sophisticated validation would be better
            command += f" {additional_args}"

        command += f" {target}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in nmap endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


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
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        # Validate mode
        if mode not in ["dir", "dns", "fuzz", "vhost"]:
            logger.warning(f"Invalid gobuster mode: {mode}")
            return jsonify({
                "error": f"Invalid mode: {mode}. Must be one of: dir, dns, fuzz, vhost"
            }), 400

        command = f"gobuster {mode} -u {url} -w {wordlist}"

        if additional_args:
            command += f" {additional_args}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in gobuster endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


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
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        command = f"dirb {url} {wordlist}"

        if additional_args:
            command += f" {additional_args}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in dirb endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@app.route("/api/tools/nikto", methods=["POST"])
def nikto():
    """Execute nikto with the provided parameters."""
    try:
        params = request.json
        target = params.get("target", "")
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("Nikto called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"nikto -h {target}"

        if additional_args:
            command += f" {additional_args}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in nikto endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


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
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        command = f"sqlmap -u {url} --batch"

        if data:
            command += f" --data=\"{data}\""

        if additional_args:
            command += f" {additional_args}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in sqlmap endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@app.route("/api/tools/metasploit", methods=["POST"])
def metasploit():
    """Execute metasploit module with the provided parameters."""
    try:
        params = request.json
        module = params.get("module", "")
        options = params.get("options", {})

        if not module:
            logger.warning("Metasploit called without module parameter")
            return jsonify({
                "error": "Module parameter is required"
            }), 400

        # Format options for Metasploit
        options_str = ""
        for key, value in options.items():
            options_str += f" {key}={value}"

        # Create an MSF resource script
        resource_content = f"use {module}\n"
        for key, value in options.items():
            resource_content += f"set {key} {value}\n"
        resource_content += "exploit\n"

        # Save resource script to a temporary file
        resource_file = "/tmp/mcp_msf_resource.rc"
        with open(resource_file, "w") as f:
            f.write(resource_content)

        command = f"msfconsole -q -r {resource_file}"
        result = execute_command(command)

        # Clean up the temporary file
        try:
            os.remove(resource_file)
        except Exception as e:
            logger.warning(f"Error removing temporary resource file: {str(e)}")

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in metasploit endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


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
            return jsonify({
                "error": "Target and service parameters are required"
            }), 400

        if not (username or username_file) or not (password or password_file):
            logger.warning("Hydra called without username/password parameters")
            return jsonify({
                "error": "Username/username_file and password/password_file are required"
            }), 400

        command = f"hydra -t 4"

        if username:
            command += f" -l {username}"
        elif username_file:
            command += f" -L {username_file}"

        if password:
            command += f" -p {password}"
        elif password_file:
            command += f" -P {password_file}"

        if additional_args:
            command += f" {additional_args}"

        command += f" {target} {service}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in hydra endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


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
            return jsonify({
                "error": "Hash file parameter is required"
            }), 400

        command = f"john"

        if format_type:
            command += f" --format={format_type}"

        if wordlist:
            command += f" --wordlist={wordlist}"

        if additional_args:
            command += f" {additional_args}"

        command += f" {hash_file}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in john endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@app.route("/api/tools/wpscan", methods=["POST"])
def wpscan():
    """Execute wpscan with the provided parameters."""
    try:
        params = request.json
        url = params.get("url", "")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("WPScan called without URL parameter")
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        command = f"wpscan --url {url}"

        if additional_args:
            command += f" {additional_args}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in wpscan endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@app.route("/api/tools/enum4linux", methods=["POST"])
def enum4linux():
    """Execute enum4linux with the provided parameters."""
    try:
        params = request.json
        target = params.get("target", "")
        additional_args = params.get("additional_args", "-a")

        if not target:
            logger.warning("Enum4linux called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"enum4linux {additional_args} {target}"

        result = execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in enum4linux endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    # Check if essential tools are installed
    essential_tools = ["nmap", "gobuster", "dirb", "nikto"]
    tools_status = {}

    for tool in essential_tools:
        try:
            result = execute_command(f"which {tool}")
            tools_status[tool] = result["success"]
        except:
            tools_status[tool] = False

    all_essential_tools_available = all(tools_status.values())

    return jsonify({
        "status": "healthy",
        "message": "Kali Linux Tools API Server is running",
        "tools_status": tools_status,
        "all_essential_tools_available": all_essential_tools_available
    })


@app.route("/mcp/capabilities", methods=["GET"])
def get_capabilities():
    """Return available tools and their capabilities."""
    capabilities = {
        "tools": {
            "nmap": {
                "name": "nmap",
                "description": "Execute Nmap network scanning",
                "parameters": {
                    "target": {"type": "string", "required": True, "description": "IP address or hostname to scan"},
                    "scan_type": {"type": "string", "required": False, "default": "-sCV", "description": "Scan type (e.g., -sV, -sS, -sCV)"},
                    "ports": {"type": "string", "required": False, "description": "Comma-separated list of ports or port ranges"},
                    "additional_args": {"type": "string", "required": False, "default": "-T4 -Pn", "description": "Additional Nmap arguments"}
                }
            },
            "gobuster": {
                "name": "gobuster",
                "description": "Execute Gobuster directory/DNS enumeration",
                "parameters": {
                    "url": {"type": "string", "required": True, "description": "Target URL"},
                    "mode": {"type": "string", "required": False, "default": "dir", "description": "Mode: dir, dns, fuzz, vhost"},
                    "wordlist": {"type": "string", "required": False, "default": "/usr/share/wordlists/dirb/common.txt", "description": "Path to wordlist"},
                    "additional_args": {"type": "string", "required": False, "description": "Additional Gobuster arguments"}
                }
            },
            "dirb": {
                "name": "dirb",
                "description": "Execute Dirb web content scanner",
                "parameters": {
                    "url": {"type": "string", "required": True, "description": "Target URL"},
                    "wordlist": {"type": "string", "required": False, "default": "/usr/share/wordlists/dirb/common.txt", "description": "Path to wordlist"},
                    "additional_args": {"type": "string", "required": False, "description": "Additional Dirb arguments"}
                }
            },
            "nikto": {
                "name": "nikto",
                "description": "Execute Nikto web server scanner",
                "parameters": {
                    "target": {"type": "string", "required": True, "description": "Target URL or IP"},
                    "additional_args": {"type": "string", "required": False, "description": "Additional Nikto arguments"}
                }
            },
            "sqlmap": {
                "name": "sqlmap",
                "description": "Execute SQLmap SQL injection scanner",
                "parameters": {
                    "url": {"type": "string", "required": True, "description": "Target URL"},
                    "data": {"type": "string", "required": False, "description": "POST data string"},
                    "additional_args": {"type": "string", "required": False, "description": "Additional SQLmap arguments"}
                }
            },
            "metasploit": {
                "name": "metasploit",
                "description": "Execute Metasploit module",
                "parameters": {
                    "module": {"type": "string", "required": True, "description": "Metasploit module path"},
                    "options": {"type": "object", "required": False, "default": {}, "description": "Module options as key-value pairs"}
                }
            },
            "hydra": {
                "name": "hydra",
                "description": "Execute Hydra password cracking",
                "parameters": {
                    "target": {"type": "string", "required": True, "description": "Target IP or hostname"},
                    "service": {"type": "string", "required": True, "description": "Service to attack (ssh, ftp, etc.)"},
                    "username": {"type": "string", "required": False, "description": "Single username to try"},
                    "username_file": {"type": "string", "required": False, "description": "Path to username file"},
                    "password": {"type": "string", "required": False, "description": "Single password to try"},
                    "password_file": {"type": "string", "required": False, "description": "Path to password file"},
                    "additional_args": {"type": "string", "required": False, "description": "Additional Hydra arguments"}
                }
            },
            "john": {
                "name": "john",
                "description": "Execute John the Ripper password cracker",
                "parameters": {
                    "hash_file": {"type": "string", "required": True, "description": "Path to file containing hashes"},
                    "wordlist": {"type": "string", "required": False, "default": "/usr/share/wordlists/rockyou.txt", "description": "Path to wordlist"},
                    "format": {"type": "string", "required": False, "description": "Hash format type"},
                    "additional_args": {"type": "string", "required": False, "description": "Additional John arguments"}
                }
            },
            "wpscan": {
                "name": "wpscan",
                "description": "Execute WPScan WordPress vulnerability scanner",
                "parameters": {
                    "url": {"type": "string", "required": True, "description": "Target WordPress URL"},
                    "additional_args": {"type": "string", "required": False, "description": "Additional WPScan arguments"}
                }
            },
            "enum4linux": {
                "name": "enum4linux",
                "description": "Execute Enum4linux Windows/Samba enumeration",
                "parameters": {
                    "target": {"type": "string", "required": True, "description": "Target IP or hostname"},
                    "additional_args": {"type": "string", "required": False, "default": "-a", "description": "Additional enum4linux arguments"}
                }
            }
        },
        "command_allowlist": list(COMMAND_ALLOWLIST.keys()),
        "version": "1.0.0",
        "server": "Kali Linux Tools API Server"
    }
    return jsonify(capabilities)


@app.route("/mcp/tools/kali_tools/<tool_name>", methods=["POST"])
def execute_tool(tool_name):
    """Execute a tool directly by name with provided parameters."""
    try:
        params = request.json or {}

        # Map tool names to their corresponding endpoint handlers
        tool_handlers = {
            "nmap": ("api/tools/nmap", ["target"]),
            "gobuster": ("api/tools/gobuster", ["url"]),
            "dirb": ("api/tools/dirb", ["url"]),
            "nikto": ("api/tools/nikto", ["target"]),
            "sqlmap": ("api/tools/sqlmap", ["url"]),
            "metasploit": ("api/tools/metasploit", ["module"]),
            "hydra": ("api/tools/hydra", ["target", "service"]),
            "john": ("api/tools/john", ["hash_file"]),
            "wpscan": ("api/tools/wpscan", ["url"]),
            "enum4linux": ("api/tools/enum4linux", ["target"])
        }

        if tool_name not in tool_handlers:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return jsonify({
                "error": f"Unknown tool: {tool_name}. Available tools: {', '.join(tool_handlers.keys())}"
            }), 400

        endpoint, required_params = tool_handlers[tool_name]

        # Validate required parameters
        missing_params = [param for param in required_params if param not in params or not params[param]]
        if missing_params:
            logger.warning(f"Missing required parameters for {tool_name}: {missing_params}")
            return jsonify({
                "error": f"Missing required parameters: {', '.join(missing_params)}"
            }), 400

        # Route to the appropriate tool handler
        if tool_name == "nmap":
            return nmap()
        elif tool_name == "gobuster":
            return gobuster()
        elif tool_name == "dirb":
            return dirb()
        elif tool_name == "nikto":
            return nikto()
        elif tool_name == "sqlmap":
            return sqlmap()
        elif tool_name == "metasploit":
            return metasploit()
        elif tool_name == "hydra":
            return hydra()
        elif tool_name == "john":
            return john()
        elif tool_name == "wpscan":
            return wpscan()
        elif tool_name == "enum4linux":
            return enum4linux()

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


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

    logger.info(f"Starting Kali Linux Tools API Server on port {API_PORT}")
    app.run(host="0.0.0.0", port=API_PORT, debug=DEBUG_MODE)
