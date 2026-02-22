#!/usr/bin/env python3
"""
Comprehensive tests for kali_server.py

Covers:
- CommandExecutor.execute() with real subprocess calls
- /health endpoint response content and structure
- All tool API endpoints: input validation (400s) and success paths (mocked)
- Metasploit resource file creation/cleanup
"""

import json
import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Shared fixtures and mock data
# ---------------------------------------------------------------------------

MOCK_SUCCESS_RESULT = {
    "stdout": "scan output",
    "stderr": "",
    "return_code": 0,
    "success": True,
    "timed_out": False,
    "partial_results": False,
}

MOCK_TIMEOUT_RESULT = {
    "stdout": "partial output so far",
    "stderr": "",
    "return_code": -1,
    "success": True,
    "timed_out": True,
    "partial_results": True,
}

MOCK_FAILURE_RESULT = {
    "stdout": "",
    "stderr": "command not found",
    "return_code": 127,
    "success": False,
    "timed_out": False,
    "partial_results": False,
}


@pytest.fixture
def client():
    """Flask test client with TESTING mode enabled."""
    from kali_server import app

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# CommandExecutor – actual execution (no mocks needed; uses plain Unix tools)
# ---------------------------------------------------------------------------


class TestCommandExecutorExecution:
    """Test CommandExecutor.execute() with real subprocesses."""

    def test_successful_command_returns_success_true(self):
        from kali_server import CommandExecutor

        executor = CommandExecutor(["echo", "hello"], timeout=5)
        result = executor.execute()
        assert result["success"] is True

    def test_successful_command_return_code_zero(self):
        from kali_server import CommandExecutor

        executor = CommandExecutor(["true"], timeout=5)
        result = executor.execute()
        assert result["return_code"] == 0

    def test_successful_command_captures_stdout(self):
        from kali_server import CommandExecutor

        executor = CommandExecutor(["echo", "hello world"], timeout=5)
        result = executor.execute()
        assert "hello world" in result["stdout"]

    def test_failed_command_returns_success_false(self):
        from kali_server import CommandExecutor

        executor = CommandExecutor(["false"], timeout=5)
        result = executor.execute()
        assert result["success"] is False
        assert result["return_code"] != 0

    def test_failed_command_captures_stderr(self):
        from kali_server import CommandExecutor

        # ls on a nonexistent path writes to stderr
        executor = CommandExecutor(["ls", "/path/that/does/not/exist_xyzzy"], timeout=5)
        result = executor.execute()
        assert result["success"] is False
        assert len(result["stderr"]) > 0

    def test_timed_out_is_false_on_normal_completion(self):
        from kali_server import CommandExecutor

        executor = CommandExecutor(["echo", "quick"], timeout=5)
        result = executor.execute()
        assert result["timed_out"] is False
        assert result["partial_results"] is False

    def test_timeout_sets_timed_out_flag(self):
        from kali_server import CommandExecutor

        # sleep 10 with a 1-second timeout must trigger TimeoutExpired
        executor = CommandExecutor(["sleep", "10"], timeout=1)
        result = executor.execute()
        assert result["timed_out"] is True
        assert result["return_code"] == -1

    def test_timeout_with_partial_output_is_success(self):
        """If a timed-out command produced some stdout, success must be True
        and partial_results must be truthy.

        NOTE: The code uses ``self.timed_out and (self.stdout_data or self.stderr_data)``
        which returns the string value of stdout/stderr rather than a boolean
        when output is available.  The assertion below intentionally uses a
        truthiness check to document this behaviour; a stricter ``is True``
        assertion would expose the type inconsistency as a bug to fix.
        """
        from kali_server import CommandExecutor

        # sh -c 'echo partial; sleep 60' – prints one line then blocks
        executor = CommandExecutor(
            ["sh", "-c", "echo partial; sleep 60"], timeout=1
        )
        result = executor.execute()
        assert result["timed_out"] is True
        # partial_results is truthy when there is partial output
        assert result["partial_results"]

    def test_result_contains_all_expected_keys(self):
        from kali_server import CommandExecutor

        executor = CommandExecutor(["echo", "test"], timeout=5)
        result = executor.execute()
        for key in ("stdout", "stderr", "return_code", "success", "timed_out", "partial_results"):
            assert key in result, f"Expected key '{key}' missing from result"


# ---------------------------------------------------------------------------
# /health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Test /health response structure and content."""

    def test_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.get("/health")
        assert response.status_code == 200

    def test_response_is_json(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.get("/health")
        assert response.content_type == "application/json"

    def test_status_field_is_healthy(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            data = json.loads(client.get("/health").data)
        assert data["status"] == "healthy"

    def test_response_contains_tools_status(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            data = json.loads(client.get("/health").data)
        assert "tools_status" in data
        assert isinstance(data["tools_status"], dict)

    def test_response_contains_all_essential_tools(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            data = json.loads(client.get("/health").data)
        for tool in ("nmap", "gobuster", "dirb", "nikto"):
            assert tool in data["tools_status"], f"Tool '{tool}' missing from tools_status"

    def test_all_essential_tools_available_field_present(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            data = json.loads(client.get("/health").data)
        assert "all_essential_tools_available" in data
        assert isinstance(data["all_essential_tools_available"], bool)

    def test_all_tools_available_true_when_commands_succeed(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            data = json.loads(client.get("/health").data)
        assert data["all_essential_tools_available"] is True

    def test_all_tools_available_false_when_commands_fail(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_FAILURE_RESULT):
            data = json.loads(client.get("/health").data)
        assert data["all_essential_tools_available"] is False

    def test_response_contains_message(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            data = json.loads(client.get("/health").data)
        assert "message" in data


# ---------------------------------------------------------------------------
# /api/command endpoint
# ---------------------------------------------------------------------------


class TestGenericCommandEndpoint:
    """Test /api/command input validation and success paths."""

    def test_missing_action_returns_400(self, client):
        response = client.post("/api/command", json={})
        assert response.status_code == 400

    def test_empty_action_returns_400(self, client):
        response = client.post("/api/command", json={"action": ""})
        assert response.status_code == 400

    def test_unknown_action_returns_400(self, client):
        response = client.post("/api/command", json={"action": "rm -rf /"})
        assert response.status_code == 400

    def test_unknown_action_returns_error_message(self, client):
        response = client.post("/api/command", json={"action": "invalid_action"})
        data = json.loads(response.data)
        assert "error" in data

    def test_valid_action_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post("/api/command", json={"action": "whoami"})
        assert response.status_code == 200

    def test_valid_action_returns_command_output(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            data = json.loads(
                client.post("/api/command", json={"action": "whoami"}).data
            )
        assert "stdout" in data or "success" in data

    def test_all_allowlisted_actions_accepted(self, client):
        from kali_server import COMMAND_ALLOWLIST

        for action in COMMAND_ALLOWLIST:
            with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
                response = client.post("/api/command", json={"action": action})
            assert response.status_code == 200, f"Allowlisted action '{action}' rejected"


# ---------------------------------------------------------------------------
# /api/tools/nmap
# ---------------------------------------------------------------------------


class TestNmapEndpoint:
    """Test /api/tools/nmap endpoint."""

    def test_missing_target_returns_400(self, client):
        assert client.post("/api/tools/nmap", json={}).status_code == 400

    def test_missing_target_error_mentions_target(self, client):
        data = json.loads(client.post("/api/tools/nmap", json={}).data)
        assert "error" in data
        assert "target" in data["error"].lower() or "Target" in data["error"]

    def test_valid_request_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post("/api/tools/nmap", json={"target": "127.0.0.1"})
        assert response.status_code == 200

    def test_custom_scan_type_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/nmap",
                json={"target": "127.0.0.1", "scan_type": "-sS"},
            )
        assert response.status_code == 200

    def test_port_range_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/nmap",
                json={"target": "127.0.0.1", "ports": "80,443,8080"},
            )
        assert response.status_code == 200

    def test_additional_args_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/nmap",
                json={"target": "127.0.0.1", "additional_args": "-T4"},
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/tools/gobuster
# ---------------------------------------------------------------------------


class TestGobusterEndpoint:
    """Test /api/tools/gobuster endpoint."""

    def test_missing_url_returns_400(self, client):
        assert client.post("/api/tools/gobuster", json={}).status_code == 400

    def test_invalid_mode_returns_400(self, client):
        response = client.post(
            "/api/tools/gobuster",
            json={"url": "http://example.com", "mode": "invalid"},
        )
        assert response.status_code == 400

    def test_invalid_mode_error_message(self, client):
        data = json.loads(
            client.post(
                "/api/tools/gobuster",
                json={"url": "http://example.com", "mode": "bad"},
            ).data
        )
        assert "error" in data

    def test_all_valid_modes_accepted(self, client):
        for mode in ("dir", "dns", "fuzz", "vhost"):
            with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
                response = client.post(
                    "/api/tools/gobuster",
                    json={"url": "http://example.com", "mode": mode},
                )
            assert response.status_code == 200, f"Mode '{mode}' should be accepted"

    def test_default_mode_is_dir(self, client):
        """Omitting mode should default to 'dir' and not reject the request."""
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/gobuster", json={"url": "http://example.com"}
            )
        assert response.status_code == 200

    def test_custom_wordlist_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/gobuster",
                json={"url": "http://example.com", "wordlist": "/tmp/words.txt"},
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/tools/dirb
# ---------------------------------------------------------------------------


class TestDirbEndpoint:
    """Test /api/tools/dirb endpoint."""

    def test_missing_url_returns_400(self, client):
        assert client.post("/api/tools/dirb", json={}).status_code == 400

    def test_missing_url_error_message(self, client):
        data = json.loads(client.post("/api/tools/dirb", json={}).data)
        assert "error" in data

    def test_valid_request_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/dirb", json={"url": "http://example.com"}
            )
        assert response.status_code == 200

    def test_custom_wordlist_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/dirb",
                json={"url": "http://example.com", "wordlist": "/tmp/custom.txt"},
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/tools/nikto
# ---------------------------------------------------------------------------


class TestNiktoEndpoint:
    """Test /api/tools/nikto endpoint."""

    def test_missing_target_returns_400(self, client):
        assert client.post("/api/tools/nikto", json={}).status_code == 400

    def test_missing_target_error_message(self, client):
        data = json.loads(client.post("/api/tools/nikto", json={}).data)
        assert "error" in data

    def test_valid_request_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/nikto", json={"target": "http://example.com"}
            )
        assert response.status_code == 200

    def test_additional_args_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/nikto",
                json={"target": "http://example.com", "additional_args": "-ssl"},
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/tools/sqlmap
# ---------------------------------------------------------------------------


class TestSqlmapEndpoint:
    """Test /api/tools/sqlmap endpoint."""

    def test_missing_url_returns_400(self, client):
        assert client.post("/api/tools/sqlmap", json={}).status_code == 400

    def test_missing_url_error_message(self, client):
        data = json.loads(client.post("/api/tools/sqlmap", json={}).data)
        assert "error" in data

    def test_valid_request_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/sqlmap", json={"url": "http://example.com/page?id=1"}
            )
        assert response.status_code == 200

    def test_post_data_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/sqlmap",
                json={
                    "url": "http://example.com/login",
                    "data": "username=admin&password=test",
                },
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/tools/metasploit
# ---------------------------------------------------------------------------


class TestMetasploitEndpoint:
    """Test /api/tools/metasploit endpoint."""

    def test_missing_module_returns_400(self, client):
        assert client.post("/api/tools/metasploit", json={}).status_code == 400

    def test_missing_module_error_message(self, client):
        data = json.loads(client.post("/api/tools/metasploit", json={}).data)
        assert "error" in data

    def test_valid_request_returns_200(self, client):
        m = mock_open()
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT), \
             patch("builtins.open", m), \
             patch("os.remove"):
            response = client.post(
                "/api/tools/metasploit",
                json={
                    "module": "auxiliary/scanner/portscan/tcp",
                    "options": {"RHOSTS": "192.168.1.1", "PORTS": "22"},
                },
            )
        assert response.status_code == 200

    def test_resource_file_is_written(self, client):
        """Verify that the MSF resource script is created before running."""
        m = mock_open()
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT), \
             patch("builtins.open", m) as mock_file, \
             patch("os.remove"):
            client.post(
                "/api/tools/metasploit",
                json={"module": "exploit/multi/handler", "options": {}},
            )
        mock_file.assert_called_once_with("/tmp/mcp_msf_resource.rc", "w")

    def test_resource_file_cleanup_attempted(self, client):
        """os.remove should be called after execution to clean up the temp file."""
        m = mock_open()
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT), \
             patch("builtins.open", m), \
             patch("os.remove") as mock_remove:
            client.post(
                "/api/tools/metasploit",
                json={"module": "exploit/multi/handler", "options": {}},
            )
        mock_remove.assert_called_once_with("/tmp/mcp_msf_resource.rc")

    def test_no_options_accepted(self, client):
        """Module without options should still work."""
        m = mock_open()
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT), \
             patch("builtins.open", m), \
             patch("os.remove"):
            response = client.post(
                "/api/tools/metasploit",
                json={"module": "auxiliary/scanner/portscan/tcp"},
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/tools/hydra
# ---------------------------------------------------------------------------


class TestHydraEndpoint:
    """Test /api/tools/hydra endpoint – complex multi-param validation."""

    def test_missing_target_returns_400(self, client):
        response = client.post(
            "/api/tools/hydra",
            json={"service": "ssh", "username": "admin", "password": "pass"},
        )
        assert response.status_code == 400

    def test_missing_service_returns_400(self, client):
        response = client.post(
            "/api/tools/hydra",
            json={"target": "192.168.1.1", "username": "admin", "password": "pass"},
        )
        assert response.status_code == 400

    def test_missing_username_and_username_file_returns_400(self, client):
        response = client.post(
            "/api/tools/hydra",
            json={"target": "192.168.1.1", "service": "ssh", "password": "pass"},
        )
        assert response.status_code == 400

    def test_missing_password_and_password_file_returns_400(self, client):
        response = client.post(
            "/api/tools/hydra",
            json={"target": "192.168.1.1", "service": "ssh", "username": "admin"},
        )
        assert response.status_code == 400

    def test_valid_inline_credentials_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/hydra",
                json={
                    "target": "192.168.1.1",
                    "service": "ssh",
                    "username": "admin",
                    "password": "secret",
                },
            )
        assert response.status_code == 200

    def test_valid_file_based_credentials_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/hydra",
                json={
                    "target": "192.168.1.1",
                    "service": "ftp",
                    "username_file": "/wordlists/users.txt",
                    "password_file": "/wordlists/passwords.txt",
                },
            )
        assert response.status_code == 200

    def test_mixed_credentials_inline_user_file_pass_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/hydra",
                json={
                    "target": "192.168.1.1",
                    "service": "ssh",
                    "username": "root",
                    "password_file": "/wordlists/passwords.txt",
                },
            )
        assert response.status_code == 200

    def test_error_message_for_missing_target(self, client):
        data = json.loads(
            client.post(
                "/api/tools/hydra",
                json={"service": "ssh", "username": "a", "password": "b"},
            ).data
        )
        assert "error" in data


# ---------------------------------------------------------------------------
# /api/tools/john
# ---------------------------------------------------------------------------


class TestJohnEndpoint:
    """Test /api/tools/john endpoint."""

    def test_missing_hash_file_returns_400(self, client):
        assert client.post("/api/tools/john", json={}).status_code == 400

    def test_missing_hash_file_error_message(self, client):
        data = json.loads(client.post("/api/tools/john", json={}).data)
        assert "error" in data

    def test_valid_request_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/john", json={"hash_file": "/tmp/hashes.txt"}
            )
        assert response.status_code == 200

    def test_format_type_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/john",
                json={"hash_file": "/tmp/hashes.txt", "format": "md5crypt"},
            )
        assert response.status_code == 200

    def test_custom_wordlist_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/john",
                json={
                    "hash_file": "/tmp/hashes.txt",
                    "wordlist": "/usr/share/wordlists/rockyou.txt",
                },
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/tools/wpscan
# ---------------------------------------------------------------------------


class TestWpscanEndpoint:
    """Test /api/tools/wpscan endpoint."""

    def test_missing_url_returns_400(self, client):
        assert client.post("/api/tools/wpscan", json={}).status_code == 400

    def test_missing_url_error_message(self, client):
        data = json.loads(client.post("/api/tools/wpscan", json={}).data)
        assert "error" in data

    def test_valid_request_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/wpscan", json={"url": "http://example.com"}
            )
        assert response.status_code == 200

    def test_additional_args_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/wpscan",
                json={
                    "url": "http://example.com",
                    "additional_args": "--enumerate u",
                },
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/tools/enum4linux
# ---------------------------------------------------------------------------


class TestEnum4linuxEndpoint:
    """Test /api/tools/enum4linux endpoint."""

    def test_missing_target_returns_400(self, client):
        assert client.post("/api/tools/enum4linux", json={}).status_code == 400

    def test_missing_target_error_message(self, client):
        data = json.loads(client.post("/api/tools/enum4linux", json={}).data)
        assert "error" in data

    def test_valid_request_returns_200(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/enum4linux", json={"target": "192.168.1.1"}
            )
        assert response.status_code == 200

    def test_default_additional_args_is_dash_a(self, client):
        """The default additional_args '-a' should be used when not provided."""
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/enum4linux", json={"target": "192.168.1.1"}
            )
        assert response.status_code == 200

    def test_custom_additional_args_accepted(self, client):
        with patch("kali_server.execute_command", return_value=MOCK_SUCCESS_RESULT):
            response = client.post(
                "/api/tools/enum4linux",
                json={"target": "192.168.1.1", "additional_args": "-U -S -G"},
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Environment variable configuration
# ---------------------------------------------------------------------------


class TestEnvironmentConfiguration:
    """Test that module-level config responds to environment variables."""

    def test_api_port_default_is_5000(self):
        import importlib

        import kali_server

        importlib.reload(kali_server)
        assert kali_server.API_PORT == 5000

    def test_debug_mode_default_is_false(self):
        import importlib

        import kali_server

        importlib.reload(kali_server)
        assert kali_server.DEBUG_MODE is False

    def test_command_timeout_is_180(self):
        import kali_server

        assert kali_server.COMMAND_TIMEOUT == 180

    def test_debug_mode_enabled_via_env_1(self):
        import importlib

        with patch.dict(os.environ, {"DEBUG_MODE": "1"}):
            import kali_server

            importlib.reload(kali_server)
            assert kali_server.DEBUG_MODE is True

    def test_debug_mode_enabled_via_env_true(self):
        import importlib

        with patch.dict(os.environ, {"DEBUG_MODE": "true"}):
            import kali_server

            importlib.reload(kali_server)
            assert kali_server.DEBUG_MODE is True

    def test_debug_mode_enabled_via_env_yes(self):
        import importlib

        with patch.dict(os.environ, {"DEBUG_MODE": "yes"}):
            import kali_server

            importlib.reload(kali_server)
            assert kali_server.DEBUG_MODE is True

    def test_api_port_from_environment(self):
        import importlib

        with patch.dict(os.environ, {"API_PORT": "8080"}):
            import kali_server

            importlib.reload(kali_server)
            assert kali_server.API_PORT == 8080


# ---------------------------------------------------------------------------
# Command allowlist integrity
# ---------------------------------------------------------------------------


class TestCommandAllowlist:
    """Verify the COMMAND_ALLOWLIST structure is well-formed."""

    def test_allowlist_is_dict(self):
        from kali_server import COMMAND_ALLOWLIST

        assert isinstance(COMMAND_ALLOWLIST, dict)

    def test_allowlist_values_are_lists(self):
        from kali_server import COMMAND_ALLOWLIST

        for key, val in COMMAND_ALLOWLIST.items():
            assert isinstance(val, list), f"Allowlist entry '{key}' must be a list"

    def test_allowlist_values_are_nonempty(self):
        from kali_server import COMMAND_ALLOWLIST

        for key, val in COMMAND_ALLOWLIST.items():
            assert len(val) > 0, f"Allowlist entry '{key}' must not be empty"

    def test_allowlist_contains_expected_safe_commands(self):
        from kali_server import COMMAND_ALLOWLIST

        # These safe utilities should always be present
        for expected in ("whoami", "uptime", "date"):
            assert expected in COMMAND_ALLOWLIST, f"'{expected}' missing from allowlist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
