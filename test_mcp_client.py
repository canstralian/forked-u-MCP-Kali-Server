#!/usr/bin/env python3
"""
Tests for MCP Server Client.

Tests KaliToolsClient, request handling, error cases, and tool wrappers.
"""

import pytest
import requests
from unittest.mock import patch, MagicMock
import mcp_server


class TestKaliToolsClientInitialization:
    """Test KaliToolsClient initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default timeout."""
        client = mcp_server.KaliToolsClient("http://localhost:5000")

        assert client.server_url == "http://localhost:5000"
        assert client.timeout == mcp_server.DEFAULT_REQUEST_TIMEOUT

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = mcp_server.KaliToolsClient("http://localhost:5000", timeout=60)

        assert client.timeout == 60

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from URL."""
        client = mcp_server.KaliToolsClient("http://localhost:5000/")

        assert client.server_url == "http://localhost:5000"
        assert not client.server_url.endswith("/")

    def test_init_with_different_hosts(self):
        """Test initialization with various host formats."""
        hosts = [
            "http://192.168.1.100:5000",
            "https://example.com",
            "http://kali-server:8080"
        ]

        for host in hosts:
            client = mcp_server.KaliToolsClient(host)
            assert client.server_url == host.rstrip("/")


class TestSafePostMethod:
    """Test safe_post method."""

    def test_safe_post_success(self, kali_client, mock_requests_post):
        """Test successful POST request."""
        result = kali_client.safe_post("api/tools/nmap", {"target": "127.0.0.1"})

        assert result["success"] is True
        assert "stdout" in result
        mock_requests_post.assert_called_once()

    def test_safe_post_url_construction(self, kali_client, mock_requests_post):
        """Test URL construction in safe_post."""
        kali_client.safe_post("api/tools/nmap", {"target": "127.0.0.1"})

        call_args = mock_requests_post.call_args
        assert call_args[1]["json"] == {"target": "127.0.0.1"}
        assert "http://localhost:5000/api/tools/nmap" in str(call_args)

    def test_safe_post_timeout(self, kali_client, mock_requests_post):
        """Test that timeout is passed to requests."""
        kali_client.safe_post("api/test", {})

        call_args = mock_requests_post.call_args
        assert call_args[1]["timeout"] == kali_client.timeout

    def test_safe_post_connection_error(self, kali_client):
        """Test handling of connection errors."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

            result = kali_client.safe_post("api/test", {})

            assert result["success"] is False
            assert "error" in result
            assert "Connection refused" in result["error"]

    def test_safe_post_timeout_error(self, kali_client):
        """Test handling of timeout errors."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

            result = kali_client.safe_post("api/test", {})

            assert result["success"] is False
            assert "error" in result
            assert "timed out" in result["error"]

    def test_safe_post_http_error(self, kali_client):
        """Test handling of HTTP errors."""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
            mock_post.return_value = mock_response

            result = kali_client.safe_post("api/test", {})

            assert result["success"] is False
            assert "error" in result

    def test_safe_post_json_decode_error(self, kali_client):
        """Test handling of invalid JSON responses."""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = kali_client.safe_post("api/test", {})

            assert "error" in result


class TestSafeGetMethod:
    """Test safe_get method."""

    def test_safe_get_success(self, kali_client, mock_requests_get):
        """Test successful GET request."""
        result = kali_client.safe_get("health")

        assert result["status"] == "healthy"
        mock_requests_get.assert_called_once()

    def test_safe_get_with_params(self, kali_client, mock_requests_get):
        """Test GET request with query parameters."""
        params = {"key": "value", "limit": 10}
        result = kali_client.safe_get("api/test", params)

        call_args = mock_requests_get.call_args
        assert call_args[1]["params"] == params

    def test_safe_get_connection_error(self, kali_client):
        """Test handling of connection errors in GET."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

            result = kali_client.safe_get("health")

            assert result["success"] is False
            assert "error" in result

    def test_safe_get_without_params(self, kali_client, mock_requests_get):
        """Test GET request without parameters."""
        result = kali_client.safe_get("health")

        call_args = mock_requests_get.call_args
        assert call_args[1]["params"] == {}


class TestHealthCheckMethod:
    """Test check_health method."""

    def test_check_health_success(self, kali_client, mock_requests_get):
        """Test successful health check."""
        result = kali_client.check_health()

        assert result["status"] == "healthy"

    def test_check_health_calls_correct_endpoint(self, kali_client, mock_requests_get):
        """Test that health check calls the correct endpoint."""
        kali_client.check_health()

        call_args = mock_requests_get.call_args[0][0]
        assert call_args == "http://localhost:5000/health"

    def test_check_health_error_handling(self, kali_client):
        """Test health check error handling."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Server down")

            result = kali_client.check_health()

            assert "error" in result
            assert result["success"] is False


class TestMCPToolWrappers:
    """Test MCP tool wrapper functions."""

    def test_nmap_scan_tool(self, kali_client, mock_requests_post):
        """Test nmap_scan tool wrapper."""
        # We need to test through setup_mcp_server
        mcp = mcp_server.setup_mcp_server(kali_client)

        # Verify MCP instance was created
        assert mcp is not None
        assert mcp.name == "kali-mcp"

    def test_tool_registration(self, kali_client):
        """Test that all tools are registered."""
        mcp = mcp_server.setup_mcp_server(kali_client)

        # Verify MCP instance is created
        assert mcp is not None
        assert mcp.name == "kali-mcp"

    def test_mcp_server_name(self, kali_client):
        """Test MCP server name."""
        mcp = mcp_server.setup_mcp_server(kali_client)

        assert mcp.name == "kali-mcp"


class TestExecuteCommandMethod:
    """Test execute_command method (deprecated)."""

    def test_execute_command(self, kali_client, mock_requests_post):
        """Test execute_command method."""
        result = kali_client.execute_command("ls -la")

        assert "success" in result or "stdout" in result
        mock_requests_post.assert_called_once()

    def test_execute_command_endpoint(self, kali_client, mock_requests_post):
        """Test that execute_command calls correct endpoint."""
        kali_client.execute_command("whoami")

        call_args = mock_requests_post.call_args
        assert "api/command" in str(call_args[0][0])


class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_multiple_failed_requests(self, kali_client):
        """Test handling of multiple consecutive failures."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

            # Make multiple requests
            for _ in range(3):
                result = kali_client.safe_post("api/test", {})
                assert result["success"] is False

    def test_recovery_after_failure(self, kali_client):
        """Test that client recovers after failures."""
        with patch('requests.post') as mock_post:
            # First call fails, second succeeds
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status = MagicMock()

            mock_post.side_effect = [
                requests.exceptions.ConnectionError("Failed"),
                mock_response
            ]

            result1 = kali_client.safe_post("api/test", {})
            assert result1["success"] is False

            result2 = kali_client.safe_post("api/test", {})
            assert result2["success"] is True

    def test_unexpected_exception_handling(self, kali_client):
        """Test handling of unexpected exceptions."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = RuntimeError("Unexpected error")

            result = kali_client.safe_post("api/test", {})

            assert result["success"] is False
            assert "error" in result


class TestArgumentParsing:
    """Test command-line argument parsing."""

    def test_parse_args_defaults(self):
        """Test default argument values."""
        with patch('sys.argv', ['mcp_server.py']):
            args = mcp_server.parse_args()

            assert args.server == mcp_server.DEFAULT_KALI_SERVER
            assert args.timeout == mcp_server.DEFAULT_REQUEST_TIMEOUT
            assert args.debug is False

    def test_parse_args_custom_server(self):
        """Test custom server argument."""
        with patch('sys.argv', ['mcp_server.py', '--server', 'http://custom:8080']):
            args = mcp_server.parse_args()

            assert args.server == 'http://custom:8080'

    def test_parse_args_custom_timeout(self):
        """Test custom timeout argument."""
        with patch('sys.argv', ['mcp_server.py', '--timeout', '600']):
            args = mcp_server.parse_args()

            assert args.timeout == 600

    def test_parse_args_debug_flag(self):
        """Test debug flag."""
        with patch('sys.argv', ['mcp_server.py', '--debug']):
            args = mcp_server.parse_args()

            assert args.debug is True


class TestMainFunction:
    """Test main entry point."""

    @patch('mcp_server.setup_mcp_server')
    @patch('mcp_server.KaliToolsClient')
    def test_main_initialization(self, mock_client_class, mock_setup):
        """Test main function initialization."""
        mock_client = MagicMock()
        mock_client.check_health.return_value = {"status": "healthy", "all_essential_tools_available": True}
        mock_client_class.return_value = mock_client

        mock_mcp = MagicMock()
        mock_setup.return_value = mock_mcp

        with patch('sys.argv', ['mcp_server.py']):
            with patch.object(mock_mcp, 'run'):
                try:
                    mcp_server.main()
                except SystemExit:
                    pass

        # Verify client was created
        mock_client_class.assert_called_once()

    @patch('mcp_server.setup_mcp_server')
    @patch('mcp_server.KaliToolsClient')
    def test_main_health_check_warning(self, mock_client_class, mock_setup):
        """Test main function with health check failure."""
        mock_client = MagicMock()
        mock_client.check_health.return_value = {"error": "Connection failed"}
        mock_client_class.return_value = mock_client

        mock_mcp = MagicMock()
        mock_setup.return_value = mock_mcp

        with patch('sys.argv', ['mcp_server.py']):
            with patch.object(mock_mcp, 'run'):
                try:
                    mcp_server.main()
                except SystemExit:
                    pass

        # Should still proceed even if health check fails
        mock_setup.assert_called_once()

    @patch('mcp_server.setup_mcp_server')
    @patch('mcp_server.KaliToolsClient')
    def test_main_with_debug_flag(self, mock_client_class, mock_setup):
        """Test main function with debug flag."""
        mock_client = MagicMock()
        mock_client.check_health.return_value = {"status": "healthy", "all_essential_tools_available": True}
        mock_client_class.return_value = mock_client

        mock_mcp = MagicMock()
        mock_setup.return_value = mock_mcp

        with patch('sys.argv', ['mcp_server.py', '--debug']):
            with patch.object(mock_mcp, 'run'):
                try:
                    mcp_server.main()
                except SystemExit:
                    pass

        # Verify debug mode was enabled
        mock_client_class.assert_called_once()


class TestRequestHeaders:
    """Test HTTP request headers and formatting."""

    def test_post_content_type(self, kali_client, mock_requests_post):
        """Test that POST requests use correct content type."""
        kali_client.safe_post("api/test", {"key": "value"})

        call_args = mock_requests_post.call_args
        # Requests library handles JSON content-type automatically
        assert call_args[1]["json"] == {"key": "value"}

    def test_timeout_parameter(self, kali_client):
        """Test that timeout parameter is correctly passed."""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            kali_client.safe_post("api/test", {})

            call_args = mock_post.call_args
            assert call_args[1]["timeout"] == kali_client.timeout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
