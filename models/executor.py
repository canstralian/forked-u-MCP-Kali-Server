"""
Command Executor Model

This module contains the CommandExecutor class for handling
command execution with timeout management.
"""

import logging
import subprocess
import threading
import traceback
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Default configuration
COMMAND_TIMEOUT = 180  # 3 minutes default timeout


class CommandExecutor:
    """Class to handle command execution with better timeout management"""

    def __init__(self, command: str, timeout: int = COMMAND_TIMEOUT):
        """
        Initialize the Command Executor

        Args:
            command: The command to execute
            timeout: Timeout in seconds for command execution
        """
        self.command = command
        self.timeout = timeout
        self.process = None
        self.stdout_data = ""
        self.stderr_data = ""
        self.stdout_thread = None
        self.stderr_thread = None
        self.return_code = None
        self.timed_out = False

    def _read_stdout(self):
        """Thread function to continuously read stdout"""
        for line in iter(self.process.stdout.readline, ""):
            self.stdout_data += line

    def _read_stderr(self):
        """Thread function to continuously read stderr"""
        for line in iter(self.process.stderr.readline, ""):
            self.stderr_data += line

    def execute(self) -> Dict[str, Any]:
        """
        Execute the command and handle timeout gracefully

        Returns:
            Dictionary containing execution results including stdout, stderr,
            return code, success status, timeout status, and partial results flag
        """
        logger.info(f"Executing command: {self.command}")

        try:
            self.process = subprocess.Popen(
                self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1  # Line buffered
            )

            # Start threads to read output continuously
            self.stdout_thread = threading.Thread(target=self._read_stdout)
            self.stderr_thread = threading.Thread(target=self._read_stderr)
            self.stdout_thread.daemon = True
            self.stderr_thread.daemon = True
            self.stdout_thread.start()
            self.stderr_thread.start()

            # Wait for the process to complete or timeout
            try:
                self.return_code = self.process.wait(timeout=self.timeout)
                # Process completed, join the threads
                self.stdout_thread.join()
                self.stderr_thread.join()
            except subprocess.TimeoutExpired:
                # Process timed out but we might have partial results
                self.timed_out = True
                logger.warning(f"Command timed out after {self.timeout} seconds. Terminating process.")

                # Try to terminate gracefully first
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)  # Give it 5 seconds to terminate
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    logger.warning("Process not responding to termination. Killing.")
                    self.process.kill()

                # Update final output
                self.return_code = -1

            # Always consider it a success if we have output, even with timeout
            success = True if self.timed_out and (self.stdout_data or self.stderr_data) else (self.return_code == 0)

            return {
                "stdout": self.stdout_data,
                "stderr": self.stderr_data,
                "return_code": self.return_code,
                "success": success,
                "timed_out": self.timed_out,
                "partial_results": self.timed_out and (self.stdout_data or self.stderr_data),
            }

        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "stdout": self.stdout_data,
                "stderr": self.stderr_data + f"\nError: {str(e)}",
                "return_code": -1,
                "success": False,
                "timed_out": False,
                "partial_results": False,
            }

    def is_running(self) -> bool:
        """
        Check if the command is currently running

        Returns:
            True if the process is running, False otherwise
        """
        return self.process is not None and self.process.poll() is None

    def terminate(self) -> bool:
        """
        Terminate the running command

        Returns:
            True if termination was successful, False otherwise
        """
        if self.is_running():
            try:
                self.process.terminate()
                return True
            except Exception as e:
                logger.error(f"Error terminating process: {str(e)}")
                return False
        return False
