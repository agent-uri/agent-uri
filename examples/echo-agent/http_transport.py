"""HTTP Transport implementation for agent:// protocol communication."""

import logging
import re
from typing import Any, Dict, Optional, Tuple

import requests

# Import from the installed agent_uri package
from agent_uri.transport.base import AgentTransport

logger = logging.getLogger(__name__)


class HttpTransport(AgentTransport):
    """HTTP Transport implementation for agent:// protocol."""

    def __init__(self):
        super().__init__()
        self._protocol = "agent+http"

    @property
    def protocol(self) -> str:
        """Return the transport protocol identifier."""
        return self._protocol

    def _parse_agent_uri(self, uri: str) -> Tuple[str, str, str]:
        """
        Parse an agent URI into transport, authority, and path components.

        Args:
            uri: The agent URI (e.g., agent://localhost:8765/echo or
                 agent+http://localhost:8765/echo)

        Returns:
            Tuple containing: (transport, authority, path)
        """
        # Match agent URI patterns
        agent_uri_pattern = r"^(agent)(\+([a-z]+))?://([^/]+)(/.*)?$"
        match = re.match(agent_uri_pattern, uri)

        if not match:
            # If not an agent URI, assume it's a direct HTTP URL
            return ("http", uri, "")

        protocol = match.group(3) or "https"  # Default to HTTPS if not specified
        authority = match.group(4)
        path = match.group(5) or ""

        return (protocol, authority, path)

    def _resolve_agent_uri(self, uri: str, capability: Optional[str] = None) -> str:
        """
        Resolve an agent URI to an HTTP endpoint.

        Args:
            uri: The agent URI (e.g., agent://localhost:8765 or
                agent+http://localhost:8765)
            capability: Optional capability to append to the path

        Returns:
            HTTP endpoint URL
        """
        transport, authority, path = self._parse_agent_uri(uri)

        # Construct HTTP URL
        endpoint = f"{transport}://{authority}{path}"

        # Append capability if provided and not already in path
        if capability and not path.endswith(f"/{capability}"):
            endpoint = f"{endpoint}/{capability}"

        return endpoint

    async def stream(
        self,
        endpoint: str,
        capability: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = 30,
        **kwargs,
    ) -> Any:
        """Stream responses from an agent capability via this transport.

        Args:
            endpoint: The base URL of the agent server
            capability: The capability name to invoke
            params: The parameters to pass to the capability
            headers: Optional HTTP headers
            timeout: Optional timeout in seconds

        Returns:
            An iterator that yields response parts

        Raises:
            NotImplementedError: This method is not implemented for basic HTTP
        """
        raise NotImplementedError(
            "Streaming is not implemented for basic HTTP transport"
        )

    async def invoke(
        self,
        endpoint: str,
        capability: str = None,
        params: Dict[str, Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = 30,
        **kwargs,
    ) -> Dict[str, Any]:
        """Invoke a capability on an agent URI.

        Args:
            endpoint: The agent URI (e.g., agent://localhost:8765)
            capability: The capability name to invoke (e.g., echo)
            params: The parameters to pass to the capability
            headers: Optional HTTP headers
            timeout: Optional timeout in seconds

        Returns:
            The JSON response from the agent
        """
        # Set default params if None
        if params is None:
            params = {}

        # Handle both agent:// URIs and direct HTTP URLs
        if endpoint.startswith("agent"):
            url = self._resolve_agent_uri(endpoint, capability)
        else:
            # Legacy support for direct HTTP endpoints
            url = f"{endpoint}/{capability}" if capability else endpoint

        # Combine default headers with user-provided headers
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        try:
            logger.info(f"Invoking {url} with params: {params}")
            response = requests.post(
                url=url, json=params, headers=request_headers, timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            raise
