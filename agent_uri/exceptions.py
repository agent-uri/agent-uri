"""
Exceptions for the agent-server package.

This module defines custom exceptions used throughout the server SDK.
"""


class AgentServerError(Exception):
    """Base exception for all agent server errors."""

    pass


class CapabilityNotFoundError(AgentServerError):
    """Raised when a capability is not found."""

    pass


class CapabilityError(AgentServerError):
    """Raised when a capability cannot be invoked."""

    pass


class HandlerError(AgentServerError):
    """Raised when a handler encounters an error."""

    pass


class DescriptorError(AgentServerError):
    """Raised when there is an error generating or validating a descriptor."""

    pass


class ConfigurationError(AgentServerError):
    """Raised when there is an error in the server configuration."""

    pass


class AuthenticationError(AgentServerError):
    """Raised when authentication fails."""

    pass


class InvalidInputError(AgentServerError):
    """Raised when input validation fails."""

    pass


# Client-side exceptions
class AgentClientError(Exception):
    """Base exception for client errors."""

    pass


class InvocationError(AgentClientError):
    """Raised when capability invocation fails."""

    pass


class ResolutionError(AgentClientError):
    """Raised when agent resolution fails."""

    pass


class SessionError(AgentClientError):
    """Raised when session management fails."""

    pass


class TransportError(AgentClientError):
    """Raised when transport layer fails."""

    pass


class TransportTimeoutError(TransportError):
    """Raised when transport operation times out."""

    pass


class ResolverError(AgentClientError):
    """Raised when URI resolution fails."""

    pass


class StreamingError(AgentClientError):
    """Raised when streaming operations fail."""

    pass
