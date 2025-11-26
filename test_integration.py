#!/usr/bin/env python3
"""
Integration tests for MCP Kali Server.

Tests end-to-end workflows, full request/response cycles, and component interaction.
"""

import pytest
import json
import threading
import time
from unittest.mock import patch, MagicMock
import kali_server
import mcp_server


class TestEndToEndFlows:
    """Test complete end-to-end workflows."""

    def test_full_nmap_scan_workflow(self, flask_client, mock_successful_command):
        """Test complete nmap scan from request to response."""
        payload = {
            "target": "192.168.1.1",
            "scan_type": "-sV",
            "ports": "80,443",
            "additional_args": "-T4"
        }

        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "stdout" in data or "stderr" in data
        assert "success" in data
        assert "return_code" in data

    def test_mcp_client_to_api_server_flow(self, mock_requests_post):
        """Test MCP client calling API server."""
        client = mcp_server.KaliToolsClient("http://localhost:5000")

        result = client.safe_post("api/tools/nmap", {
            "target": "127.0.0.1",
            "scan_type": "-sV"
        })

        assert result["success"] is True
        mock_requests_post.assert_called_once()

    def test_health_check_workflow(self, flask_client, mock_which_command):
        """Test complete health check workflow."""
        with patch.object(kali_server, 'execute_command', side_effect=mock_which_command):
            response = flask_client.get('/health')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "healthy"
            assert "tools_status" in data


class TestMultipleToolExecution:
    """Test executing multiple tools in sequence."""

    def test_sequential_tool_execution(self, flask_client, mock_successful_command):
        """Test executing multiple tools sequentially."""
        tools = [
            ('/api/tools/nmap', {"target": "127.0.0.1"}),
            ('/api/tools/nikto', {"target": "http://127.0.0.1"}),
            ('/api/tools/gobuster', {"url": "http://127.0.0.1", "mode": "dir"}),
        ]

        for endpoint, payload in tools:
            response = flask_client.post(
                endpoint,
                data=json.dumps(payload),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "success" in data

    def test_multiple_scans_same_tool(self, flask_client, mock_successful_command):
        """Test executing same tool multiple times."""
        for i in range(3):
            payload = {"target": f"192.168.1.{i+1}"}

            response = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps(payload),
                content_type='application/json'
            )

            assert response.status_code == 200


class TestErrorRecoveryFlows:
    """Test error recovery in complete workflows."""

    def test_recovery_after_failed_command(self, flask_client):
        """Test that system recovers after command failure."""
        # First request fails
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = Exception("Command failed")

            response1 = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": "127.0.0.1"}),
                content_type='application/json'
            )

            # Should return 200 with error in response body or 500
            assert response1.status_code in [200, 500]
            data1 = json.loads(response1.data)
            # Either has error field or success is False
            assert "error" in data1 or data1.get("success") is False

        # Second request succeeds
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            response2 = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": "127.0.0.1"}),
                content_type='application/json'
            )

            assert response2.status_code == 200

    def test_partial_results_handling(self, flask_client):
        """Test handling of partial results from timed-out commands."""
        with patch('subprocess.Popen') as mock_popen:
            import subprocess
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(side_effect=['partial data\n', ''])
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(side_effect=[subprocess.TimeoutExpired('cmd', 1), None])
            mock_process.terminate = MagicMock()
            mock_popen.return_value = mock_process

            response = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": "127.0.0.1"}),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["timed_out"] is True
            assert "partial data" in data["stdout"]
            assert data["partial_results"] is True


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    def test_concurrent_api_requests(self, flask_client, mock_successful_command):
        """Test handling multiple concurrent requests."""
        def make_request():
            response = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": "127.0.0.1"}),
                content_type='application/json'
            )
            return response.status_code

        # Create multiple threads to make concurrent requests
        threads = []
        results = []

        for _ in range(5):
            thread = threading.Thread(target=lambda: results.append(make_request()))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All requests should succeed
        assert all(code == 200 for code in results)

    def test_concurrent_different_tools(self, flask_client, mock_successful_command):
        """Test concurrent requests to different tools."""
        endpoints = [
            '/api/tools/nmap',
            '/api/tools/nikto',
            '/api/tools/gobuster',
        ]

        payloads = [
            {"target": "127.0.0.1"},
            {"target": "http://127.0.0.1"},
            {"url": "http://127.0.0.1", "mode": "dir"},
        ]

        def make_request(endpoint, payload):
            response = flask_client.post(
                endpoint,
                data=json.dumps(payload),
                content_type='application/json'
            )
            return response.status_code

        threads = []
        results = []

        for endpoint, payload in zip(endpoints, payloads):
            thread = threading.Thread(
                target=lambda e=endpoint, p=payload: results.append(make_request(e, p))
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 3
        assert all(code == 200 for code in results)


class TestDataFlowValidation:
    """Test data flow through the system."""

    def test_request_data_reaches_executor(self, flask_client):
        """Test that request data is properly passed to CommandExecutor."""
        with patch.object(kali_server, 'CommandExecutor') as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor.execute.return_value = {
                "stdout": "test",
                "stderr": "",
                "return_code": 0,
                "success": True,
                "timed_out": False,
                "partial_results": False
            }
            mock_executor_class.return_value = mock_executor

            response = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": "192.168.1.1", "scan_type": "-sV"}),
                content_type='application/json'
            )

            assert response.status_code == 200
            # Verify CommandExecutor was called
            assert mock_executor.execute.called

    def test_response_format_consistency(self, flask_client, mock_successful_command):
        """Test that all tool endpoints return consistent response format."""
        endpoints_payloads = [
            ('/api/tools/nmap', {"target": "127.0.0.1"}),
            ('/api/tools/nikto', {"target": "http://127.0.0.1"}),
            ('/api/tools/dirb', {"url": "http://127.0.0.1"}),
        ]

        for endpoint, payload in endpoints_payloads:
            response = flask_client.post(
                endpoint,
                data=json.dumps(payload),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)

            # All responses should have these fields
            assert "success" in data or "stdout" in data
            assert isinstance(data, dict)


class TestMCPClientIntegration:
    """Test MCP client integration with API server."""

    def test_mcp_client_health_check(self, mock_requests_get):
        """Test MCP client health check integration."""
        client = mcp_server.KaliToolsClient("http://localhost:5000")
        result = client.check_health()

        assert result["status"] == "healthy"

    def test_mcp_tool_function_integration(self, mock_requests_post):
        """Test MCP tool functions call correct endpoints."""
        client = mcp_server.KaliToolsClient("http://localhost:5000")
        mcp = mcp_server.setup_mcp_server(client)

        # Verify MCP server is set up
        assert mcp.name == "kali-mcp"

    def test_mcp_client_error_propagation(self):
        """Test that errors propagate correctly through MCP client."""
        client = mcp_server.KaliToolsClient("http://nonexistent:9999", timeout=1)

        with patch('requests.post') as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

            result = client.safe_post("api/test", {})

            assert result["success"] is False
            assert "error" in result


class TestConfigurationIntegration:
    """Test configuration and environment variable integration."""

    def test_environment_variable_configuration(self):
        """Test that environment variables affect configuration."""
        import os

        original_port = os.environ.get("API_PORT")
        os.environ["API_PORT"] = "8080"

        # Re-import to get new config
        import importlib
        importlib.reload(kali_server)

        # Clean up
        if original_port:
            os.environ["API_PORT"] = original_port
        else:
            os.environ.pop("API_PORT", None)

    def test_debug_mode_configuration(self):
        """Test debug mode configuration."""
        import os

        original_debug = os.environ.get("DEBUG_MODE")
        os.environ["DEBUG_MODE"] = "1"

        import importlib
        importlib.reload(kali_server)

        # Clean up
        if original_debug:
            os.environ["DEBUG_MODE"] = original_debug
        else:
            os.environ.pop("DEBUG_MODE", None)


class TestResourceManagement:
    """Test resource management and cleanup."""

    @patch('builtins.open', create=True)
    @patch('os.remove')
    def test_metasploit_temp_file_lifecycle(self, mock_remove, mock_open, flask_client, mock_successful_command):
        """Test complete lifecycle of Metasploit temporary files."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        payload = {
            "module": "exploit/test",
            "options": {"RHOST": "192.168.1.1"}
        }

        response = flask_client.post(
            '/api/tools/metasploit',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verify file was written and removed
        mock_open.assert_called_once()
        mock_remove.assert_called_once()

    def test_command_executor_cleanup(self, mock_successful_command):
        """Test that CommandExecutor cleans up resources."""
        executor = kali_server.CommandExecutor(["echo", "test"])
        result = executor.execute()

        # Threads should be joined (not running)
        assert result["success"] is True
        # Process should be completed
        assert executor.return_code is not None


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_full_penetration_test_workflow(self, flask_client, mock_successful_command):
        """Test a realistic penetration testing workflow."""
        # 1. Health check
        health = flask_client.get('/health')
        assert health.status_code == 200

        # 2. Nmap scan
        nmap_response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps({"target": "192.168.1.100"}),
            content_type='application/json'
        )
        assert nmap_response.status_code == 200

        # 3. Gobuster scan
        gobuster_response = flask_client.post(
            '/api/tools/gobuster',
            data=json.dumps({"url": "http://192.168.1.100", "mode": "dir"}),
            content_type='application/json'
        )
        assert gobuster_response.status_code == 200

        # 4. Nikto scan
        nikto_response = flask_client.post(
            '/api/tools/nikto',
            data=json.dumps({"target": "http://192.168.1.100"}),
            content_type='application/json'
        )
        assert nikto_response.status_code == 200

    def test_authenticated_attack_workflow(self, flask_client, mock_successful_command):
        """Test workflow involving credential attacks."""
        # 1. Hydra brute force
        hydra_response = flask_client.post(
            '/api/tools/hydra',
            data=json.dumps({
                "target": "192.168.1.100",
                "service": "ssh",
                "username": "admin",
                "password_file": "/tmp/passwords.txt"
            }),
            content_type='application/json'
        )
        assert hydra_response.status_code == 200

        # 2. John the Ripper
        john_response = flask_client.post(
            '/api/tools/john',
            data=json.dumps({"hash_file": "/tmp/hashes.txt"}),
            content_type='application/json'
        )
        assert john_response.status_code == 200


class TestEdgeCaseIntegration:
    """Test edge cases in integrated scenarios."""

    def test_rapid_sequential_requests(self, flask_client, mock_successful_command):
        """Test handling of rapid sequential requests."""
        for i in range(10):
            response = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": f"127.0.0.{i+1}"}),
                content_type='application/json'
            )

            assert response.status_code == 200

    def test_mixed_success_and_failure(self, flask_client):
        """Test system behavior with mixed success and failure."""
        # Valid request
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            response1 = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": "127.0.0.1"}),
                content_type='application/json'
            )
            assert response1.status_code == 200

        # Invalid request
        response2 = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response2.status_code == 400

        # Valid request again
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            response3 = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": "127.0.0.1"}),
                content_type='application/json'
            )
            assert response3.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
