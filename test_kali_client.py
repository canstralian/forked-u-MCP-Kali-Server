#!/usr/bin/env python3
"""
Comprehensive tests for mcp_server.py (KaliToolsClient)

Covers:
- URL normalisation (trailing-slash stripping)
- KaliToolsClient.safe_get(): success, HTTP errors, network errors, unexpected errors
- KaliToolsClient.safe_post(): success, HTTP errors, network errors
- KaliToolsClient.check_health() and execute_command() high-level methods
- setup_mcp_server() returns a FastMCP instance
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(json_data, raise_for_status=None):
    """Build a mock requests.Response-like object."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    if raise_for_status is not None:
        mock_resp.raise_for_status.side_effect = raise_for_status
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------


class TestKaliToolsClientURLHandling:
    """KaliToolsClient should normalise the server URL on construction."""

    def test_trailing_slash_stripped(self):
        from mcp_server import KaliToolsClient

        client = KaliToolsClient("http://localhost:5000/")
        assert client.server_url == "http://localhost:5000"

    def test_no_trailing_slash_unchanged(self):
        from mcp_server import KaliToolsClient

        client = KaliToolsClient("http://localhost:5000")
        assert client.server_url == "http://localhost:5000"

    def test_multiple_trailing_slashes_stripped(self):
        from mcp_server import KaliToolsClient

        client = KaliToolsClient("http://localhost:5000///")
        assert client.server_url == "http://localhost:5000"

    def test_default_timeout_is_300(self):
        from mcp_server import KaliToolsClient

        client = KaliToolsClient("http://localhost:5000")
        assert client.timeout == 300

    def test_custom_timeout_stored(self):
        from mcp_server import KaliToolsClient

        client = KaliToolsClient("http://localhost:5000", timeout=60)
        assert client.timeout == 60

    def test_custom_server_url_stored(self):
        from mcp_server import KaliToolsClient

        client = KaliToolsClient("http://192.168.1.100:9000")
        assert "192.168.1.100" in client.server_url


# ---------------------------------------------------------------------------
# KaliToolsClient.safe_get()
# ---------------------------------------------------------------------------


class TestSafeGet:
    """Tests for KaliToolsClient.safe_get()."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from mcp_server import KaliToolsClient

        self.client = KaliToolsClient("http://localhost:5000")

    def test_success_returns_json_dict(self):
        expected = {"status": "healthy"}
        with patch("requests.get", return_value=_make_mock_response(expected)):
            result = self.client.safe_get("health")
        assert result == expected

    def test_builds_correct_url(self):
        with patch("requests.get", return_value=_make_mock_response({})) as mock_get:
            self.client.safe_get("health")
        url_called = mock_get.call_args[0][0]
        assert url_called == "http://localhost:5000/health"

    def test_passes_timeout_to_requests(self):
        with patch("requests.get", return_value=_make_mock_response({})) as mock_get:
            self.client.safe_get("health")
        assert mock_get.call_args[1]["timeout"] == 300

    def test_passes_query_params(self):
        with patch("requests.get", return_value=_make_mock_response({})) as mock_get:
            self.client.safe_get("health", params={"verbose": "1"})
        assert mock_get.call_args[1]["params"] == {"verbose": "1"}

    def test_empty_params_default(self):
        """Calling without params should still work (default empty dict)."""
        with patch("requests.get", return_value=_make_mock_response({})) as mock_get:
            self.client.safe_get("health")
        assert mock_get.call_args[1]["params"] == {}

    def test_connection_error_returns_error_dict(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
            result = self.client.safe_get("health")
        assert "error" in result
        assert result["success"] is False

    def test_timeout_exception_returns_error_dict(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
            result = self.client.safe_get("health")
        assert "error" in result
        assert result["success"] is False

    def test_http_error_returns_error_dict(self):
        mock_resp = _make_mock_response(
            {}, raise_for_status=requests.exceptions.HTTPError("404")
        )
        with patch("requests.get", return_value=mock_resp):
            result = self.client.safe_get("nonexistent")
        assert "error" in result
        assert result["success"] is False

    def test_unexpected_exception_returns_error_dict(self):
        with patch("requests.get", side_effect=ValueError("boom")):
            result = self.client.safe_get("health")
        assert "error" in result
        assert result["success"] is False

    def test_error_message_contains_exception_text(self):
        with patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("Connection refused"),
        ):
            result = self.client.safe_get("health")
        assert "Connection refused" in result["error"]


# ---------------------------------------------------------------------------
# KaliToolsClient.safe_post()
# ---------------------------------------------------------------------------


class TestSafePost:
    """Tests for KaliToolsClient.safe_post()."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from mcp_server import KaliToolsClient

        self.client = KaliToolsClient("http://localhost:5000")

    def test_success_returns_json_dict(self):
        expected = {"success": True, "stdout": "output"}
        with patch("requests.post", return_value=_make_mock_response(expected)):
            result = self.client.safe_post("api/tools/nmap", {"target": "127.0.0.1"})
        assert result == expected

    def test_builds_correct_url(self):
        with patch("requests.post", return_value=_make_mock_response({})) as mock_post:
            self.client.safe_post("api/tools/nmap", {"target": "127.0.0.1"})
        url_called = mock_post.call_args[0][0]
        assert url_called == "http://localhost:5000/api/tools/nmap"

    def test_sends_json_payload(self):
        payload = {"target": "127.0.0.1", "scan_type": "-sV"}
        with patch("requests.post", return_value=_make_mock_response({})) as mock_post:
            self.client.safe_post("api/tools/nmap", payload)
        assert mock_post.call_args[1]["json"] == payload

    def test_passes_timeout_to_requests(self):
        with patch("requests.post", return_value=_make_mock_response({})) as mock_post:
            self.client.safe_post("api/tools/nmap", {})
        assert mock_post.call_args[1]["timeout"] == 300

    def test_connection_error_returns_error_dict(self):
        with patch(
            "requests.post", side_effect=requests.exceptions.ConnectionError("refused")
        ):
            result = self.client.safe_post("api/tools/nmap", {})
        assert "error" in result
        assert result["success"] is False

    def test_timeout_exception_returns_error_dict(self):
        with patch("requests.post", side_effect=requests.exceptions.Timeout("slow")):
            result = self.client.safe_post("api/tools/nmap", {})
        assert "error" in result
        assert result["success"] is False

    def test_http_error_returns_error_dict(self):
        mock_resp = _make_mock_response(
            {}, raise_for_status=requests.exceptions.HTTPError("500")
        )
        with patch("requests.post", return_value=mock_resp):
            result = self.client.safe_post("api/tools/nmap", {})
        assert "error" in result
        assert result["success"] is False

    def test_unexpected_exception_returns_error_dict(self):
        with patch("requests.post", side_effect=RuntimeError("unexpected")):
            result = self.client.safe_post("api/tools/nmap", {})
        assert "error" in result
        assert result["success"] is False


# ---------------------------------------------------------------------------
# High-level KaliToolsClient methods
# ---------------------------------------------------------------------------


class TestCheckHealth:
    """Tests for KaliToolsClient.check_health()."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from mcp_server import KaliToolsClient

        self.client = KaliToolsClient("http://localhost:5000")

    def test_calls_health_endpoint(self):
        with patch("requests.get", return_value=_make_mock_response({"status": "healthy"})) as mock_get:
            self.client.check_health()
        assert "health" in mock_get.call_args[0][0]

    def test_returns_server_response(self):
        health_data = {
            "status": "healthy",
            "tools_status": {"nmap": True},
            "all_essential_tools_available": True,
        }
        with patch("requests.get", return_value=_make_mock_response(health_data)):
            result = self.client.check_health()
        assert result == health_data

    def test_propagates_connection_error(self):
        with patch(
            "requests.get", side_effect=requests.exceptions.ConnectionError("refused")
        ):
            result = self.client.check_health()
        assert "error" in result
        assert result["success"] is False


class TestExecuteCommandMethod:
    """Tests for KaliToolsClient.execute_command()."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from mcp_server import KaliToolsClient

        self.client = KaliToolsClient("http://localhost:5000")

    def test_posts_to_api_command_endpoint(self):
        with patch("requests.post", return_value=_make_mock_response({"success": True})) as mock_post:
            self.client.execute_command("whoami")
        url_called = mock_post.call_args[0][0]
        assert "api/command" in url_called

    def test_sends_command_in_payload(self):
        with patch("requests.post", return_value=_make_mock_response({"success": True})) as mock_post:
            self.client.execute_command("whoami")
        payload = mock_post.call_args[1]["json"]
        assert payload.get("command") == "whoami"

    def test_returns_server_response(self):
        expected = {"success": True, "stdout": "root\n"}
        with patch("requests.post", return_value=_make_mock_response(expected)):
            result = self.client.execute_command("whoami")
        assert result == expected

    def test_propagates_error_on_failure(self):
        with patch(
            "requests.post", side_effect=requests.exceptions.ConnectionError("refused")
        ):
            result = self.client.execute_command("whoami")
        assert "error" in result
        assert result["success"] is False


# ---------------------------------------------------------------------------
# setup_mcp_server()
# ---------------------------------------------------------------------------


class TestSetupMcpServer:
    """Tests for the setup_mcp_server() factory function."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from mcp_server import KaliToolsClient

        self.kali_client = KaliToolsClient("http://localhost:5000")

    def test_returns_fastmcp_instance(self):
        from mcp.server.fastmcp import FastMCP
        from mcp_server import setup_mcp_server

        mcp = setup_mcp_server(self.kali_client)
        assert isinstance(mcp, FastMCP)

    def test_mcp_instance_is_not_none(self):
        from mcp_server import setup_mcp_server

        mcp = setup_mcp_server(self.kali_client)
        assert mcp is not None

    def test_can_call_setup_mcp_server_multiple_times(self):
        """setup_mcp_server must be idempotent (no global side-effects that crash)."""
        from mcp_server import setup_mcp_server

        mcp1 = setup_mcp_server(self.kali_client)
        mcp2 = setup_mcp_server(self.kali_client)
        assert mcp1 is not None
        assert mcp2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
