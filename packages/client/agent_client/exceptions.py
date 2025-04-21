"""
Exceptions for the agent:// client SDK.

This module defines the various exception classes that can be raised
by the agent client SDK.
"""


class AgentClientError(Exception):
    """Base exception for all agent client errors."""
    pass


class AuthenticationError(AgentClientError):
    """Exception raised for authentication errors."""
    pass


class ResolutionError(AgentClientError):
    """Exception raised when resolving an agent URI fails."""
    pass


class InvocationError(AgentClientError):
    """Exception raised when an agent capability invocation fails."""
    pass


class StreamingError(AgentClientError):
    """Exception raised when streaming from an agent fails."""
    pass


class SessionError(AgentClientError):
    """Exception raised for session-related errors."""
    pass
