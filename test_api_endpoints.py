#!/usr/bin/env python3
"""
Tests for Flask API endpoints.

Tests all tool endpoints, parameter validation, and response formats.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
import kali_server


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_endpoint_exists(self, flask_client):
        """Test that health endpoint responds."""
        response = flask_client.get('/health')
        assert response.status_code == 200

    def test_health_endpoint_response_format(self, flask_client, mock_which_command):
        """Test health endpoint returns proper JSON format."""
        with patch.object(kali_server, 'execute_command', side_effect=mock_which_command):
            response = flask_client.get('/health')
            data = json.loads(response.data)

            assert "status" in data
            assert "message" in data
            assert "tools_status" in data
            assert "all_essential_tools_available" in data

    def test_health_check_tools_available(self, flask_client, mock_which_command):
        """Test health check when all tools are available."""
        with patch.object(kali_server, 'execute_command', side_effect=mock_which_command):
            response = flask_client.get('/health')
            data = json.loads(response.data)

            assert data["status"] == "healthy"
            assert data["all_essential_tools_available"] is True
            assert all(data["tools_status"].values())

    def test_health_check_tools_missing(self, flask_client):
        """Test health check when tools are missing."""
        def mock_missing_tools(command):
            return {"stdout": "", "stderr": "", "return_code": 1, "success": False}

        with patch.object(kali_server, 'execute_command', side_effect=mock_missing_tools):
            response = flask_client.get('/health')
            data = json.loads(response.data)

            assert data["all_essential_tools_available"] is False


class TestNmapEndpoint:
    """Test /api/tools/nmap endpoint."""

    def test_nmap_basic_scan(self, flask_client, sample_nmap_payload, mock_successful_command):
        """Test basic nmap scan."""
        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps(sample_nmap_payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "stdout" in data or "stderr" in data

    def test_nmap_with_ports(self, flask_client, mock_successful_command):
        """Test nmap scan with port specification."""
        payload = {
            "target": "192.168.1.1",
            "scan_type": "-sV",
            "ports": "80,443,8080"
        }

        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_nmap_without_optional_params(self, flask_client, mock_successful_command):
        """Test nmap with only required target parameter."""
        payload = {"target": "192.168.1.1"}

        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_nmap_missing_target(self, flask_client):
        """Test nmap without target returns 400."""
        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


class TestGobusterEndpoint:
    """Test /api/tools/gobuster endpoint."""

    def test_gobuster_dir_scan(self, flask_client, sample_gobuster_payload, mock_successful_command):
        """Test gobuster directory scan."""
        response = flask_client.post(
            '/api/tools/gobuster',
            data=json.dumps(sample_gobuster_payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_gobuster_dns_mode(self, flask_client, mock_successful_command):
        """Test gobuster in DNS mode."""
        payload = {
            "url": "example.com",
            "mode": "dns",
            "wordlist": "/usr/share/wordlists/dirb/common.txt"
        }

        response = flask_client.post(
            '/api/tools/gobuster',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_gobuster_vhost_mode(self, flask_client, mock_successful_command):
        """Test gobuster in vhost mode."""
        payload = {
            "url": "http://example.com",
            "mode": "vhost"
        }

        response = flask_client.post(
            '/api/tools/gobuster',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_gobuster_missing_url(self, flask_client):
        """Test gobuster without URL returns 400."""
        response = flask_client.post(
            '/api/tools/gobuster',
            data=json.dumps({"mode": "dir"}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestDirbEndpoint:
    """Test /api/tools/dirb endpoint."""

    def test_dirb_basic_scan(self, flask_client, mock_successful_command):
        """Test basic dirb scan."""
        payload = {"url": "http://example.com"}

        response = flask_client.post(
            '/api/tools/dirb',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_dirb_with_custom_wordlist(self, flask_client, mock_successful_command):
        """Test dirb with custom wordlist."""
        payload = {
            "url": "http://example.com",
            "wordlist": "/usr/share/wordlists/dirb/big.txt"
        }

        response = flask_client.post(
            '/api/tools/dirb',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_dirb_missing_url(self, flask_client):
        """Test dirb without URL returns 400."""
        response = flask_client.post(
            '/api/tools/dirb',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestNiktoEndpoint:
    """Test /api/tools/nikto endpoint."""

    def test_nikto_basic_scan(self, flask_client, mock_successful_command):
        """Test basic nikto scan."""
        payload = {"target": "http://example.com"}

        response = flask_client.post(
            '/api/tools/nikto',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_nikto_with_additional_args(self, flask_client, mock_successful_command):
        """Test nikto with additional arguments."""
        payload = {
            "target": "http://example.com",
            "additional_args": "-ssl -port 443"
        }

        response = flask_client.post(
            '/api/tools/nikto',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_nikto_missing_target(self, flask_client):
        """Test nikto without target returns 400."""
        response = flask_client.post(
            '/api/tools/nikto',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestSqlmapEndpoint:
    """Test /api/tools/sqlmap endpoint."""

    def test_sqlmap_basic_scan(self, flask_client, mock_successful_command):
        """Test basic sqlmap scan."""
        payload = {"url": "http://example.com/page?id=1"}

        response = flask_client.post(
            '/api/tools/sqlmap',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_sqlmap_with_post_data(self, flask_client, sample_sqlmap_payload, mock_successful_command):
        """Test sqlmap with POST data."""
        response = flask_client.post(
            '/api/tools/sqlmap',
            data=json.dumps(sample_sqlmap_payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_sqlmap_missing_url(self, flask_client):
        """Test sqlmap without URL returns 400."""
        response = flask_client.post(
            '/api/tools/sqlmap',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestMetasploitEndpoint:
    """Test /api/tools/metasploit endpoint."""

    @patch('builtins.open', create=True)
    @patch('os.remove')
    def test_metasploit_basic_exploit(self, mock_remove, mock_open, flask_client, mock_successful_command):
        """Test basic metasploit exploit."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        payload = {
            "module": "exploit/windows/smb/ms17_010_eternalblue",
            "options": {"RHOST": "192.168.1.100"}
        }

        response = flask_client.post(
            '/api/tools/metasploit',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    @patch('builtins.open', create=True)
    @patch('os.remove')
    def test_metasploit_with_multiple_options(self, mock_remove, mock_open, flask_client, mock_successful_command):
        """Test metasploit with multiple options."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        payload = {
            "module": "exploit/test",
            "options": {
                "RHOST": "192.168.1.100",
                "RPORT": "445",
                "LHOST": "192.168.1.50"
            }
        }

        response = flask_client.post(
            '/api/tools/metasploit',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_metasploit_missing_module(self, flask_client):
        """Test metasploit without module returns 400."""
        response = flask_client.post(
            '/api/tools/metasploit',
            data=json.dumps({"options": {}}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestHydraEndpoint:
    """Test /api/tools/hydra endpoint."""

    def test_hydra_ssh_attack(self, flask_client, mock_successful_command):
        """Test hydra SSH attack."""
        payload = {
            "target": "192.168.1.100",
            "service": "ssh",
            "username": "admin",
            "password_file": "/usr/share/wordlists/rockyou.txt"
        }

        response = flask_client.post(
            '/api/tools/hydra',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_hydra_with_username_file(self, flask_client, mock_successful_command):
        """Test hydra with username file."""
        payload = {
            "target": "192.168.1.100",
            "service": "ftp",
            "username_file": "/tmp/users.txt",
            "password_file": "/tmp/passwords.txt"
        }

        response = flask_client.post(
            '/api/tools/hydra',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_hydra_missing_target(self, flask_client):
        """Test hydra without target returns 400."""
        payload = {
            "service": "ssh",
            "username": "admin",
            "password": "test"
        }

        response = flask_client.post(
            '/api/tools/hydra',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_hydra_missing_service(self, flask_client):
        """Test hydra without service returns 400."""
        payload = {
            "target": "192.168.1.100",
            "username": "admin",
            "password": "test"
        }

        response = flask_client.post(
            '/api/tools/hydra',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestJohnEndpoint:
    """Test /api/tools/john endpoint."""

    def test_john_basic_crack(self, flask_client, mock_successful_command):
        """Test basic john the ripper crack."""
        payload = {"hash_file": "/tmp/hashes.txt"}

        response = flask_client.post(
            '/api/tools/john',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_john_with_format(self, flask_client, mock_successful_command):
        """Test john with hash format specification."""
        payload = {
            "hash_file": "/tmp/hashes.txt",
            "format": "md5",
            "wordlist": "/usr/share/wordlists/rockyou.txt"
        }

        response = flask_client.post(
            '/api/tools/john',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_john_missing_hash_file(self, flask_client):
        """Test john without hash file returns 400."""
        response = flask_client.post(
            '/api/tools/john',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestWPScanEndpoint:
    """Test /api/tools/wpscan endpoint."""

    def test_wpscan_basic(self, flask_client, mock_successful_command):
        """Test basic wpscan."""
        payload = {"url": "http://example.com"}

        response = flask_client.post(
            '/api/tools/wpscan',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_wpscan_with_args(self, flask_client, mock_successful_command):
        """Test wpscan with additional arguments."""
        payload = {
            "url": "http://example.com",
            "additional_args": "--enumerate u"
        }

        response = flask_client.post(
            '/api/tools/wpscan',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_wpscan_missing_url(self, flask_client):
        """Test wpscan without URL returns 400."""
        response = flask_client.post(
            '/api/tools/wpscan',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestEnum4linuxEndpoint:
    """Test /api/tools/enum4linux endpoint."""

    def test_enum4linux_basic(self, flask_client, mock_successful_command):
        """Test basic enum4linux scan."""
        payload = {"target": "192.168.1.100"}

        response = flask_client.post(
            '/api/tools/enum4linux',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_enum4linux_custom_args(self, flask_client, mock_successful_command):
        """Test enum4linux with custom arguments."""
        payload = {
            "target": "192.168.1.100",
            "additional_args": "-U -S"
        }

        response = flask_client.post(
            '/api/tools/enum4linux',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_enum4linux_missing_target(self, flask_client):
        """Test enum4linux without target returns 400."""
        response = flask_client.post(
            '/api/tools/enum4linux',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestCommandEndpoint:
    """Test /api/command endpoint."""

    def test_command_valid_action(self, flask_client, mock_successful_command):
        """Test executing a valid allowlisted command."""
        for action in kali_server.COMMAND_ALLOWLIST.keys():
            response = flask_client.post(
                '/api/command',
                data=json.dumps({"action": action}),
                content_type='application/json'
            )

            assert response.status_code == 200

    def test_command_invalid_action(self, flask_client):
        """Test that invalid actions are rejected."""
        response = flask_client.post(
            '/api/command',
            data=json.dumps({"action": "invalid_action"}),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_command_missing_action(self, flask_client):
        """Test that missing action is rejected."""
        response = flask_client.post(
            '/api/command',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestErrorResponses:
    """Test error handling and response formats."""

    def test_500_error_on_exception(self, flask_client):
        """Test that exceptions return 500 errors."""
        with patch.object(kali_server, 'execute_command', side_effect=Exception("Test error")):
            response = flask_client.post(
                '/api/tools/nmap',
                data=json.dumps({"target": "127.0.0.1"}),
                content_type='application/json'
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data

    def test_json_error_response_format(self, flask_client):
        """Test that error responses are valid JSON."""
        response = flask_client.post(
            '/api/tools/nmap',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
