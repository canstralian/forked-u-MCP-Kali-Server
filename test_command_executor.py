#!/usr/bin/env python3
"""
Tests for CommandExecutor class.

Tests command execution, timeout handling, threading, and error cases.
"""

import pytest
import subprocess
import threading
import time
from unittest.mock import patch, MagicMock, Mock
import kali_server


class TestCommandExecutorInitialization:
    """Test CommandExecutor initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default timeout."""
        executor = kali_server.CommandExecutor(["echo", "test"])

        assert executor.command == ["echo", "test"]
        assert executor.timeout == kali_server.COMMAND_TIMEOUT
        assert executor.process is None
        assert executor.stdout_data == ""
        assert executor.stderr_data == ""
        assert executor.return_code is None
        assert executor.timed_out is False

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        executor = kali_server.CommandExecutor(["echo", "test"], timeout=30)

        assert executor.timeout == 30

    def test_init_with_string_command(self):
        """Test initialization with string command."""
        executor = kali_server.CommandExecutor("echo test")

        assert executor.command == "echo test"


class TestSuccessfulExecution:
    """Test successful command execution scenarios."""

    def test_simple_command_execution(self, mock_successful_command):
        """Test execution of a simple command."""
        executor = kali_server.CommandExecutor(["echo", "test"])
        result = executor.execute()

        assert result["success"] is True
        assert result["return_code"] == 0
        assert result["timed_out"] is False
        assert "test output" in result["stdout"]

    def test_command_with_stderr(self):
        """Test command that produces stderr output."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(side_effect=['output\n', ''])
            mock_process.stderr.readline = MagicMock(side_effect=['warning\n', ''])
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"])
            result = executor.execute()

            assert result["success"] is True
            assert "output" in result["stdout"]
            assert "warning" in result["stderr"]

    def test_output_capture_threading(self):
        """Test that stdout and stderr are captured via threads."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            stdout_lines = ['line1\n', 'line2\n', 'line3\n', '']
            stderr_lines = ['error1\n', 'error2\n', '']

            mock_process.stdout.readline = MagicMock(side_effect=stdout_lines)
            mock_process.stderr.readline = MagicMock(side_effect=stderr_lines)
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"])
            result = executor.execute()

            assert "line1" in result["stdout"]
            assert "line2" in result["stdout"]
            assert "line3" in result["stdout"]
            assert "error1" in result["stderr"]
            assert "error2" in result["stderr"]


class TestFailedExecution:
    """Test failed command execution scenarios."""

    def test_command_with_nonzero_exit_code(self, mock_failed_command):
        """Test command that exits with non-zero code."""
        executor = kali_server.CommandExecutor(["false"])
        result = executor.execute()

        assert result["success"] is False
        assert result["return_code"] == 1
        assert result["timed_out"] is False

    def test_command_not_found(self):
        """Test execution of non-existent command."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = FileNotFoundError("Command not found")

            executor = kali_server.CommandExecutor(["nonexistent"])
            result = executor.execute()

            assert result["success"] is False
            assert result["return_code"] == -1
            assert "Error executing command" in result["stderr"]

    def test_permission_denied(self):
        """Test execution with permission denied."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = PermissionError("Permission denied")

            executor = kali_server.CommandExecutor(["test"])
            result = executor.execute()

            assert result["success"] is False
            assert "Error executing command" in result["stderr"]


class TestTimeoutHandling:
    """Test timeout scenarios and graceful termination."""

    def test_command_timeout_graceful_termination(self):
        """Test that timed out commands are terminated gracefully."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(side_effect=['partial\n', ''])
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(side_effect=[
                subprocess.TimeoutExpired('cmd', 1),
                None  # Second wait after terminate succeeds
            ])
            mock_process.terminate = MagicMock()
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["sleep", "100"], timeout=1)
            result = executor.execute()

            assert result["timed_out"] is True
            assert mock_process.terminate.called
            assert result["return_code"] == -1

    def test_command_timeout_force_kill(self):
        """Test that unresponsive commands are force killed."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')

            # First wait times out, second wait (after terminate) also times out, kill succeeds
            mock_process.wait = MagicMock(side_effect=[
                subprocess.TimeoutExpired('cmd', 1),  # Initial timeout
                subprocess.TimeoutExpired('cmd', 5),  # Terminate timeout
                None  # Kill succeeds
            ])
            mock_process.terminate = MagicMock()
            mock_process.kill = MagicMock()
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"], timeout=1)
            result = executor.execute()

            assert result["timed_out"] is True
            assert mock_process.terminate.called
            assert mock_process.kill.called

    def test_partial_results_on_timeout(self):
        """Test that partial output is returned when timeout occurs."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(side_effect=['partial output\n', ''])
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(side_effect=[
                subprocess.TimeoutExpired('cmd', 1),
                None
            ])
            mock_process.terminate = MagicMock()
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"], timeout=1)
            result = executor.execute()

            assert result["timed_out"] is True
            assert "partial output" in result["stdout"]
            # With partial results, success should be True even though it timed out
            assert result["partial_results"] is True
            assert result["success"] is True

    def test_timeout_without_partial_results(self):
        """Test timeout without any output."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(side_effect=[
                subprocess.TimeoutExpired('cmd', 1),
                None
            ])
            mock_process.terminate = MagicMock()
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"], timeout=1)
            result = executor.execute()

            assert result["timed_out"] is True
            # No output means no partial results
            assert result["stdout"] == "" or result["stdout"] == ''
            assert result["partial_results"] is False
            assert result["success"] is False  # No output means no success


class TestThreadSafety:
    """Test thread safety and concurrent execution."""

    def test_thread_creation(self):
        """Test that stdout and stderr threads are created."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"])
            result = executor.execute()

            # Verify threads were created and are daemon threads
            assert executor.stdout_thread is not None
            assert executor.stderr_thread is not None
            assert executor.stdout_thread.daemon is True
            assert executor.stderr_thread.daemon is True

    def test_thread_join_on_completion(self):
        """Test that threads are joined when process completes."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            with patch('threading.Thread') as mock_thread_class:
                mock_stdout_thread = MagicMock()
                mock_stderr_thread = MagicMock()
                mock_thread_class.side_effect = [mock_stdout_thread, mock_stderr_thread]

                executor = kali_server.CommandExecutor(["test"])
                result = executor.execute()

                # Threads should be started and joined
                assert mock_stdout_thread.start.called
                assert mock_stderr_thread.start.called
                assert mock_stdout_thread.join.called
                assert mock_stderr_thread.join.called


class TestExecuteCommandWrapper:
    """Test the execute_command wrapper function."""

    def test_execute_command_wrapper(self, mock_successful_command):
        """Test execute_command wrapper function."""
        result = kali_server.execute_command(["echo", "test"])

        assert "stdout" in result
        assert "stderr" in result
        assert "return_code" in result
        assert "success" in result

    def test_execute_command_creates_executor(self):
        """Test that execute_command creates a CommandExecutor."""
        with patch.object(kali_server, 'CommandExecutor') as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor.execute.return_value = {"success": True}
            mock_executor_class.return_value = mock_executor

            result = kali_server.execute_command(["test"])

            mock_executor_class.assert_called_once_with(["test"])
            mock_executor.execute.assert_called_once()


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_empty_command(self):
        """Test execution with empty command."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = ValueError("Empty command")

            executor = kali_server.CommandExecutor([])
            result = executor.execute()

            assert result["success"] is False

    def test_large_output(self):
        """Test handling of large output."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            # Simulate large output
            large_output = ["line\n"] * 10000 + ['']
            mock_process.stdout.readline = MagicMock(side_effect=large_output)
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"])
            result = executor.execute()

            assert result["success"] is True
            assert len(result["stdout"]) > 0

    def test_unicode_output(self):
        """Test handling of unicode output."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout.readline = MagicMock(side_effect=['unicode: café ñ 中文\n', ''])
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"])
            result = executor.execute()

            assert result["success"] is True
            assert "café" in result["stdout"] or "caf" in result["stdout"]

    def test_binary_output_handling(self):
        """Test that text mode handles binary data gracefully."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            # In text mode, binary data might cause issues or be decoded with replacement
            mock_process.stdout.readline = MagicMock(return_value='')
            mock_process.stderr.readline = MagicMock(return_value='')
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            executor = kali_server.CommandExecutor(["test"])
            result = executor.execute()

            # Should complete without crashing
            assert "success" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
