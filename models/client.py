"""
Kali Tools Client Model

This module contains the KaliToolsClient class for communicating
with the Kali Linux Tools API Server.
"""

import logging
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_REQUEST_TIMEOUT = 300  # 5 minutes default timeout for API requests


class KaliToolsClient:
    """Client for communicating with the Kali Linux Tools API Server"""

    def __init__(self, server_url: str, timeout: int = DEFAULT_REQUEST_TIMEOUT):
        """
        Initialize the Kali Tools Client

        Args:
            server_url: URL of the Kali Tools API Server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        logger.info(f"Initialized Kali Tools Client connecting to {server_url}")

    def safe_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform a GET request with optional query parameters.

        Args:
            endpoint: API endpoint path (without leading slash)
            params: Optional query parameters

        Returns:
            Response data as dictionary
        """
        if params is None:
            params = {}

        url = f"{self.server_url}/{endpoint}"

        try:
            logger.debug(f"GET {url} with params: {params}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}", "success": False}

    def safe_post(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a POST request with JSON data.

        Args:
            endpoint: API endpoint path (without leading slash)
            json_data: JSON data to send

        Returns:
            Response data as dictionary
        """
        url = f"{self.server_url}/{endpoint}"

        try:
            logger.debug(f"POST {url} with data: {json_data}")
            response = requests.post(url, json=json_data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}", "success": False}

    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a generic command on the Kali server

        Args:
            command: The command to execute

        Returns:
            Command execution results
        """
        data = {"command": command}
        return self.safe_post("api/command", data)

    def check_health(self) -> Dict[str, Any]:
        """
        Check if the Kali server is healthy and responsive

        Returns:
            Health check results
        """
        return self.safe_get("health")

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of the Kali server

        Returns:
            Server capabilities
        """
        return self.safe_get("mcp/capabilities")
