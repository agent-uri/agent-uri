"""
Transport layer for agent:// protocol.

This package provides the transport layer for communicating with agents
via the agent:// protocol.
"""

from .base import AgentTransport, TransportError, TransportTimeoutError
from .registry import TransportRegistry, default_registry
from .transports import HttpsTransport, LocalTransport, WebSocketTransport

# Register transport implementations
default_registry.register_transport(HttpsTransport)
default_registry.register_transport(WebSocketTransport)
default_registry.register_transport(LocalTransport)

__all__ = [
    "AgentTransport",
    "TransportRegistry",
    "default_registry",
    "TransportError",
    "TransportTimeoutError",
    "HttpsTransport",
    "WebSocketTransport",
    "LocalTransport",
]
