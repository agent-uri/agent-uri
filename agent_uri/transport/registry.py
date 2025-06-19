"""
Transport registry for agent:// protocol.

This module provides a registry for transport protocol implementations,
allowing dynamic registration and lookup of transports based on the
protocol specified in agent+<protocol>:// URIs.
"""

import logging
from typing import Dict, Set, Type

from .base import AgentTransport, TransportNotSupportedError

logger = logging.getLogger(__name__)


class TransportRegistry:
    """
    Registry of transport protocol implementations.

    This class maintains a mapping of protocol identifiers to transport
    class implementations, allowing dynamic registration and lookup
    of transports based on the protocol specified in agent URIs.
    """

    def __init__(self) -> None:
        """Initialize an empty transport registry."""
        self._transports: Dict[str, Type[AgentTransport]] = {}
        self._instances: Dict[str, AgentTransport] = {}

    def register_transport(self, transport_class: Type[AgentTransport]) -> None:
        """
        Register a transport protocol implementation.

        Args:
            transport_class: The transport class to register
        """
        # Create a temporary instance to get the protocol
        temp_instance = transport_class()
        protocol = temp_instance.protocol

        if protocol in self._transports:
            logger.warning(f"Overriding existing transport for protocol '{protocol}'")

        self._transports[protocol] = transport_class
        logger.debug(f"Registered transport for protocol '{protocol}'")

    def unregister_transport(self, protocol: str) -> bool:
        """
        Unregister a transport protocol.

        Args:
            protocol: The protocol identifier to unregister

        Returns:
            True if the transport was unregistered, False if not found
        """
        if protocol in self._transports:
            del self._transports[protocol]
            if protocol in self._instances:
                del self._instances[protocol]
            logger.debug(f"Unregistered transport for protocol '{protocol}'")
            return True
        return False

    def get_transport(self, protocol: str) -> AgentTransport:
        """
        Get a transport instance for a specific protocol.

        Args:
            protocol: The protocol identifier (e.g., 'https', 'wss', 'local')

        Returns:
            An instance of the appropriate transport

        Raises:
            TransportNotSupportedError: If no transport is registered for the protocol
        """
        # Return cached instance if available
        if protocol in self._instances:
            return self._instances[protocol]

        # Create new instance if transport class is registered
        if protocol in self._transports:
            transport = self._transports[protocol]()
            self._instances[protocol] = transport
            return transport

        # Check for fallback to https transport if available
        if protocol == "agent" and "https" in self._transports:
            logger.debug("Using https transport as fallback for agent:// URI")
            transport = self._transports["https"]()
            self._instances["agent"] = transport
            return transport

        raise TransportNotSupportedError(
            f"No transport registered for protocol '{protocol}'"
        )

    def list_supported_protocols(self) -> Set[str]:
        """
        List all supported transport protocols.

        Returns:
            A set of protocol identifiers
        """
        return set(self._transports.keys())

    def is_protocol_supported(self, protocol: str) -> bool:
        """
        Check if a specific protocol is supported.

        Args:
            protocol: The protocol identifier to check

        Returns:
            True if the protocol is supported, False otherwise
        """
        # Special case: 'agent' is supported if 'https' is registered (fallback)
        if protocol == "agent":
            return "https" in self._transports
        return protocol in self._transports


# Global registry instance for convenient access
default_registry = TransportRegistry()
