"""
Client SDK for the agent:// protocol.

This package provides a client SDK for the agent:// protocol, integrating
URI parsing, descriptor handling, resolution, and transport binding into
a simple interface for invoking agent capabilities.
"""

from agent_client.client import AgentClient, AgentSession
from agent_client.auth import AuthProvider, BearerTokenAuth, ApiKeyAuth
from agent_client.exceptions import (
    AgentClientError,
    AuthenticationError,
    ResolutionError,
    InvocationError,
    StreamingError,
    SessionError
)

__version__ = "0.1.0"

__all__ = [
    "AgentClient",
    "AgentSession",
    "AuthProvider",
    "BearerTokenAuth",
    "ApiKeyAuth",
    "AgentClientError",
    "AuthenticationError",
    "ResolutionError",
    "InvocationError",
    "StreamingError",
    "SessionError",
]
