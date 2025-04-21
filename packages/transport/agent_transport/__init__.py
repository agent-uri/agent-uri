"""
Transport layer for agent:// protocol.

This package provides the transport layer for communicating with agents
via the agent:// protocol.
"""

from agent_transport.base import AgentTransport, TransportError, TransportTimeoutError
from agent_transport.registry import TransportRegistry, default_registry
from agent_transport.transports import HttpsTransport, WebSocketTransport, LocalTransport

# Register transport implementations
default_registry.register_transport(HttpsTransport)
default_registry.register_transport(WebSocketTransport)
default_registry.register_transport(LocalTransport)

__all__ = [
    'AgentTransport',
    'TransportRegistry',
    'default_registry',
    'TransportError',
    'TransportTimeoutError',
    'HttpsTransport',
    'WebSocketTransport',
    'LocalTransport',
]
