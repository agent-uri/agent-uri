"""
Base classes for agent transport bindings.

This module defines the base abstract classes and exceptions for
the transport binding layer of the agent:// protocol.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union


class TransportError(Exception):
    """Base exception for transport-related errors."""

    pass


class TransportTimeoutError(TransportError):
    """Exception raised when transport requests time out."""

    pass


class TransportNotSupportedError(TransportError):
    """Exception raised when a transport protocol is not supported."""

    pass


class AgentTransport(ABC):
    """
    Abstract base class for agent transport protocol implementations.

    All transport protocols (HTTPS, WebSocket, Local, etc.) must implement
    this interface to provide a consistent way to communicate with agents
    regardless of the underlying transport mechanism.
    """

    @property
    @abstractmethod
    def protocol(self) -> str:
        """
        Return the transport protocol identifier.

        This should match the protocol specified in agent+<protocol>:// URIs.
        """
        pass

    @abstractmethod
    def invoke(
        self,
        endpoint: str,
        capability: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke an agent capability via this transport.

        Args:
            endpoint: The endpoint URL for the agent
            capability: The capability to invoke (path component)
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the request
            timeout: Optional timeout in seconds
            **kwargs: Additional transport-specific parameters

        Returns:
            The response from the agent (format depends on capability)

        Raises:
            TransportError: If there is an error communicating with the agent
            TransportTimeoutError: If the request times out
        """
        pass

    @abstractmethod
    def stream(
        self,
        endpoint: str,
        capability: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """
        Stream responses from an agent capability via this transport.

        This method is similar to invoke() but returns an iterator that
        yields response parts as they become available.

        Args:
            endpoint: The endpoint URL for the agent
            capability: The capability to invoke (path component)
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the request
            timeout: Optional timeout in seconds
            **kwargs: Additional transport-specific parameters

        Returns:
            An iterator that yields response parts

        Raises:
            TransportError: If there is an error communicating with the agent
            TransportTimeoutError: If the request times out
        """
        pass

    def format_body(self, params: Dict[str, Any]) -> Union[str, bytes]:
        """
        Format the parameters into a request body.

        Default implementation converts parameters to JSON.
        Subclasses may override this for different formats.

        Args:
            params: Parameters to format

        Returns:
            Formatted body as string or bytes
        """
        return json.dumps(params)

    def parse_response(self, response: Any) -> Any:
        """
        Parse the raw response into a structured result.

        Default implementation attempts to parse JSON.
        Subclasses may override this for different formats.

        Args:
            response: Raw response from the transport

        Returns:
            Parsed response
        """
        if isinstance(response, (str, bytes)):
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Return as-is if not valid JSON
                return response
        return response
