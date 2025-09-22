"""
Test cases for models package
"""

import pytest
from unittest.mock import Mock, patch
from models.client import KaliToolsClient
from models.executor import CommandExecutor


class TestKaliToolsClient:
    """Test cases for KaliToolsClient"""
    
    def test_init(self):
        """Test client initialization"""
        client = KaliToolsClient("http://localhost:5000")
        assert client.server_url == "http://localhost:5000"
        assert client.timeout == 300
    
    def test_init_with_trailing_slash(self):
        """Test client initialization with trailing slash"""
        client = KaliToolsClient("http://localhost:5000/")
        assert client.server_url == "http://localhost:5000"
    
    @patch('models.client.requests.get')
    def test_safe_get_success(self, mock_get):
        """Test successful GET request"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = KaliToolsClient("http://localhost:5000")
        result = client.safe_get("test")
        
        assert result == {"status": "ok"}
        mock_get.assert_called_once()
    
    @patch('models.client.requests.post')
    def test_safe_post_success(self, mock_post):
        """Test successful POST request"""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = KaliToolsClient("http://localhost:5000")
        result = client.safe_post("test", {"data": "test"})
        
        assert result == {"result": "success"}
        mock_post.assert_called_once()


class TestCommandExecutor:
    """Test cases for CommandExecutor"""
    
    def test_init(self):
        """Test executor initialization"""
        executor = CommandExecutor("echo test")
        assert executor.command == "echo test"
        assert executor.timeout == 180
        assert not executor.timed_out
    
    def test_init_custom_timeout(self):
        """Test executor initialization with custom timeout"""
        executor = CommandExecutor("echo test", timeout=60)
        assert executor.timeout == 60
    
    @patch('models.executor.subprocess.Popen')
    def test_execute_success(self, mock_popen):
        """Test successful command execution"""
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_popen.return_value = mock_process
        
        executor = CommandExecutor("echo test")
        result = executor.execute()
        
        assert result["return_code"] == 0
        assert result["success"] is True
        assert not result["timed_out"]
    
    def test_is_running_false(self):
        """Test is_running when no process"""
        executor = CommandExecutor("echo test")
        assert not executor.is_running()
    
    def test_terminate_no_process(self):
        """Test terminate when no process running"""
        executor = CommandExecutor("echo test")
        assert not executor.terminate()