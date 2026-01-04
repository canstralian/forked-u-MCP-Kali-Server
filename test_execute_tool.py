#!/usr/bin/env python3
"""
Unit tests for the execute_tool function and dispatch table pattern.

These tests verify that the refactored execute_tool function correctly
uses the dispatch table to route tool execution requests.
"""

import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kali_server


class TestDispatchTable:
    """Test the tool dispatch table structure"""
    
    def test_dispatch_table_exists(self):
        """Test that TOOL_DISPATCH_TABLE is defined"""
        assert hasattr(kali_server, 'TOOL_DISPATCH_TABLE')
        assert isinstance(kali_server.TOOL_DISPATCH_TABLE, dict)
    
    def test_dispatch_table_contains_all_tools(self):
        """Test that all expected tools are in the dispatch table"""
        expected_tools = [
            'nmap', 'gobuster', 'dirb', 'nikto', 'sqlmap',
            'metasploit', 'hydra', 'john', 'wpscan', 'enum4linux'
        ]
        
        for tool in expected_tools:
            assert tool in kali_server.TOOL_DISPATCH_TABLE, \
                f"Tool '{tool}' not found in dispatch table"
    
    def test_dispatch_table_values_are_callable(self):
        """Test that all dispatch table values are callable functions"""
        for tool_name, handler in kali_server.TOOL_DISPATCH_TABLE.items():
            assert callable(handler), \
                f"Handler for '{tool_name}' is not callable"


class TestHandlerFunctions:
    """Test individual handler functions"""
    
    @patch('kali_server.execute_command')
    def test_handle_nmap_success(self, mock_execute):
        """Test handle_nmap with valid parameters"""
        mock_execute.return_value = {"stdout": "scan results", "success": True}
        
        params = {"target": "192.168.1.1"}
        result = kali_server.handle_nmap(params)
        
        assert result["success"] is True
        mock_execute.assert_called_once()
        
        # Verify command contains target
        call_args = mock_execute.call_args[0][0]
        assert "192.168.1.1" in call_args
    
    def test_handle_nmap_missing_target(self):
        """Test handle_nmap without required target parameter"""
        params = {}
        result = kali_server.handle_nmap(params)
        
        assert "error" in result
        assert result["success"] is False
        assert "Target parameter is required" in result["error"]
    
    @patch('kali_server.execute_command')
    def test_handle_gobuster_success(self, mock_execute):
        """Test handle_gobuster with valid parameters"""
        mock_execute.return_value = {"stdout": "scan results", "success": True}
        
        params = {"url": "http://example.com"}
        result = kali_server.handle_gobuster(params)
        
        assert result["success"] is True
        mock_execute.assert_called_once()
    
    def test_handle_gobuster_invalid_mode(self):
        """Test handle_gobuster with invalid mode"""
        params = {"url": "http://example.com", "mode": "invalid"}
        result = kali_server.handle_gobuster(params)
        
        assert "error" in result
        assert result["success"] is False
        assert "Invalid mode" in result["error"]
    
    @patch('kali_server.execute_command')
    def test_handle_dirb_success(self, mock_execute):
        """Test handle_dirb with valid parameters"""
        mock_execute.return_value = {"stdout": "scan results", "success": True}
        
        params = {"url": "http://example.com"}
        result = kali_server.handle_dirb(params)
        
        assert result["success"] is True
        mock_execute.assert_called_once()
    
    @patch('kali_server.execute_command')
    def test_handle_nikto_success(self, mock_execute):
        """Test handle_nikto with valid parameters"""
        mock_execute.return_value = {"stdout": "scan results", "success": True}
        
        params = {"target": "http://example.com"}
        result = kali_server.handle_nikto(params)
        
        assert result["success"] is True
        mock_execute.assert_called_once()
    
    @patch('kali_server.execute_command')
    def test_handle_sqlmap_success(self, mock_execute):
        """Test handle_sqlmap with valid parameters"""
        mock_execute.return_value = {"stdout": "scan results", "success": True}
        
        params = {"url": "http://example.com/page?id=1"}
        result = kali_server.handle_sqlmap(params)
        
        assert result["success"] is True
        mock_execute.assert_called_once()
    
    @patch('kali_server.execute_command')
    @patch('os.remove')
    def test_handle_metasploit_success(self, mock_remove, mock_execute):
        """Test handle_metasploit with valid parameters"""
        mock_execute.return_value = {"stdout": "exploit results", "success": True}
        
        params = {
            "module": "exploit/windows/smb/ms17_010_eternalblue",
            "options": {"RHOST": "192.168.1.1"}
        }
        result = kali_server.handle_metasploit(params)
        
        assert result["success"] is True
        mock_execute.assert_called_once()
    
    @patch('kali_server.execute_command')
    def test_handle_hydra_success(self, mock_execute):
        """Test handle_hydra with valid parameters"""
        mock_execute.return_value = {"stdout": "attack results", "success": True}
        
        params = {
            "target": "192.168.1.1",
            "service": "ssh",
            "username": "admin",
            "password": "password123"
        }
        result = kali_server.handle_hydra(params)
        
        assert result["success"] is True
        mock_execute.assert_called_once()
    
    def test_handle_hydra_missing_credentials(self):
        """Test handle_hydra without required credentials"""
        params = {
            "target": "192.168.1.1",
            "service": "ssh"
        }
        result = kali_server.handle_hydra(params)
        
        assert "error" in result
        assert result["success"] is False


class TestExecuteToolEndpoint:
    """Test the execute_tool Flask endpoint"""
    
    def setup_method(self):
        """Set up test client before each test"""
        kali_server.app.config['TESTING'] = True
        self.client = kali_server.app.test_client()
    
    @patch('kali_server.handle_nmap')
    def test_execute_tool_valid_tool(self, mock_handler):
        """Test execute_tool endpoint with valid tool name"""
        mock_handler.return_value = {"stdout": "results", "success": True}
        
        response = self.client.post(
            '/mcp/tools/kali_tools/nmap',
            data=json.dumps({"target": "192.168.1.1"}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        mock_handler.assert_called_once()
    
    def test_execute_tool_invalid_tool(self):
        """Test execute_tool endpoint with invalid tool name"""
        response = self.client.post(
            '/mcp/tools/kali_tools/invalid_tool',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Unknown tool" in data["error"]
        assert "available_tools" in data
    
    @patch('kali_server.handle_gobuster')
    def test_execute_tool_with_params(self, mock_handler):
        """Test execute_tool endpoint passes parameters correctly"""
        mock_handler.return_value = {"stdout": "results", "success": True}
        
        test_params = {
            "url": "http://example.com",
            "mode": "dir",
            "wordlist": "/custom/wordlist.txt"
        }
        
        response = self.client.post(
            '/mcp/tools/kali_tools/gobuster',
            data=json.dumps(test_params),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        mock_handler.assert_called_once_with(test_params)
    
    def test_execute_tool_without_json_body(self):
        """Test execute_tool endpoint without JSON body"""
        response = self.client.post('/mcp/tools/kali_tools/nmap')
        
        # Should still work, just with empty params
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should fail validation due to missing target
        assert "error" in data or data.get("success") is False


class TestGetCapabilities:
    """Test the get_capabilities endpoint"""
    
    def setup_method(self):
        """Set up test client before each test"""
        kali_server.app.config['TESTING'] = True
        self.client = kali_server.app.test_client()
    
    def test_get_capabilities_endpoint(self):
        """Test that capabilities endpoint returns available tools"""
        response = self.client.get('/mcp/capabilities')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) > 0
        
        # Check that some expected tools are present
        expected_tools = ['nmap', 'gobuster', 'nikto']
        for tool in expected_tools:
            assert tool in data["tools"]


class TestIntegration:
    """Integration tests for the dispatch table pattern"""
    
    def test_all_handlers_accept_params_dict(self):
        """Test that all handlers accept a dictionary parameter"""
        for tool_name, handler in kali_server.TOOL_DISPATCH_TABLE.items():
            try:
                # Call with empty params - should either work or return validation error
                result = handler({})
                assert isinstance(result, dict), \
                    f"Handler {tool_name} did not return a dict"
            except TypeError as e:
                pytest.fail(f"Handler {tool_name} doesn't accept params dict: {e}")
    
    def test_handlers_return_consistent_structure(self):
        """Test that all handlers return consistent response structure"""
        for tool_name, handler in kali_server.TOOL_DISPATCH_TABLE.items():
            result = handler({})
            
            # All handlers should return a dict
            assert isinstance(result, dict), \
                f"Handler {tool_name} did not return a dict"
            
            # Should have either 'success' or 'error' key
            assert 'success' in result or 'error' in result, \
                f"Handler {tool_name} missing 'success' or 'error' key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
