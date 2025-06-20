"""
Exceptions for the agent-uri package.

This module defines custom exceptions used throughout the agent-uri library
with HTTP-extended 4-digit error codes and enhanced context.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorCode(str, Enum):
    """Error codes for agent-uri operations, extending HTTP status patterns."""

    # Client errors (4xxx) - Bad request/input issues
    INVALID_URI_FORMAT = "4001"  # Bad request - malformed URI
    INVALID_SCHEME = "4002"  # Bad request - wrong scheme
    INVALID_TRANSPORT = "4003"  # Bad request - unsupported transport
    MISSING_AUTHORITY = "4004"  # Bad request - required authority missing
    INVALID_QUERY = "4005"  # Bad request - malformed query params
    INVALID_INPUT = "4006"  # Bad request - validation failed
    MALFORMED_DESCRIPTOR = "4007"  # Bad request - invalid descriptor format

    AUTHENTICATION_ERROR = "4011"  # Unauthorized - auth failed
    AUTHENTICATION_REQUIRED = "4012"  # Unauthorized - auth missing

    CAPABILITY_NOT_FOUND = "4041"  # Not found - capability doesn't exist
    AGENT_NOT_FOUND = "4042"  # Not found - agent doesn't exist
    ENDPOINT_NOT_FOUND = "4043"  # Not found - endpoint unavailable

    TRANSPORT_TIMEOUT = "4081"  # Request timeout - transport layer
    RESOLUTION_TIMEOUT = "4082"  # Request timeout - agent resolution

    # Server errors (5xxx) - Internal/processing issues
    CAPABILITY_ERROR = "5001"  # Internal error - capability execution
    HANDLER_ERROR = "5002"  # Internal error - request handler
    DESCRIPTOR_ERROR = "5003"  # Internal error - descriptor processing
    CONFIGURATION_ERROR = "5004"  # Internal error - server config
    INVOCATION_ERROR = "5005"  # Internal error - capability invocation
    SESSION_ERROR = "5006"  # Internal error - session management
    STREAMING_ERROR = "5007"  # Internal error - streaming operations

    TRANSPORT_ERROR = "5021"  # Bad gateway - transport failure
    TRANSPORT_UNAVAILABLE = "5022"  # Bad gateway - transport not available

    AGENT_UNAVAILABLE = "5031"  # Service unavailable - agent down
    RESOLVER_ERROR = "5032"  # Service unavailable - resolution service
    RESOLUTION_ERROR = "5033"  # Service unavailable - can't resolve agent

    # Unknown/catch-all
    UNKNOWN_ERROR = "5999"  # Internal error - unclassified


class AgentError(Exception):
    """Base exception for all agent-uri errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        base_msg = super().__str__()
        return f"[{self.error_code.value}] {base_msg}"


class AgentServerError(AgentError):
    """Base exception for all agent server errors."""

    pass


class CapabilityNotFoundError(AgentServerError):
    """Raised when a capability is not found."""

    def __init__(
        self, capability_name: str, available_capabilities: Optional[List[str]] = None
    ):
        message = f"Capability '{capability_name}' not found"
        if available_capabilities:
            message += f". Available capabilities: {', '.join(available_capabilities)}"
        details = {
            "capability_name": capability_name,
            "available_capabilities": available_capabilities or [],
        }
        super().__init__(message, ErrorCode.CAPABILITY_NOT_FOUND, details)


class CapabilityError(AgentServerError):
    """Raised when a capability cannot be invoked."""

    def __init__(self, message: str, capability_name: Optional[str] = None):
        details = {"capability_name": capability_name} if capability_name else {}
        super().__init__(message, ErrorCode.CAPABILITY_ERROR, details)


class HandlerError(AgentServerError):
    """Raised when a handler encounters an error."""

    def __init__(self, message: str, handler_type: Optional[str] = None):
        details = {"handler_type": handler_type} if handler_type else {}
        super().__init__(message, ErrorCode.HANDLER_ERROR, details)


class DescriptorError(AgentServerError):
    """Raised when there is an error generating or validating a descriptor."""

    def __init__(self, message: str, descriptor_path: Optional[str] = None):
        details = {"descriptor_path": descriptor_path} if descriptor_path else {}
        super().__init__(message, ErrorCode.DESCRIPTOR_ERROR, details)


class ConfigurationError(AgentServerError):
    """Raised when there is an error in the server configuration."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, ErrorCode.CONFIGURATION_ERROR, details)


class AuthenticationError(AgentServerError):
    """Raised when authentication fails."""

    def __init__(self, message: str, auth_scheme: Optional[str] = None):
        details = {"auth_scheme": auth_scheme} if auth_scheme else {}
        super().__init__(message, ErrorCode.AUTHENTICATION_ERROR, details)


class InvalidInputError(AgentServerError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
    ):
        details = {
            "field_name": field_name,
            "validation_errors": validation_errors or [],
        }
        super().__init__(message, ErrorCode.INVALID_INPUT, details)


# Client-side exceptions
class AgentClientError(AgentError):
    """Base exception for client errors."""

    pass


class InvocationError(AgentClientError):
    """Raised when capability invocation fails."""

    def __init__(
        self,
        message: str,
        agent_uri: Optional[str] = None,
        capability_name: Optional[str] = None,
    ):
        details = {"agent_uri": agent_uri, "capability_name": capability_name}
        super().__init__(message, ErrorCode.INVOCATION_ERROR, details)


class ResolutionError(AgentClientError):
    """Raised when agent resolution fails."""

    def __init__(self, message: str, agent_uri: Optional[str] = None):
        details = {"agent_uri": agent_uri} if agent_uri else {}
        super().__init__(message, ErrorCode.RESOLUTION_ERROR, details)


class SessionError(AgentClientError):
    """Raised when session management fails."""

    def __init__(self, message: str, session_id: Optional[str] = None):
        details = {"session_id": session_id} if session_id else {}
        super().__init__(message, ErrorCode.SESSION_ERROR, details)


class TransportError(AgentClientError):
    """Raised when transport layer fails."""

    def __init__(
        self,
        message: str,
        transport_type: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        details = {"transport_type": transport_type, "endpoint": endpoint}
        super().__init__(message, ErrorCode.TRANSPORT_ERROR, details)


class TransportTimeoutError(TransportError):
    """Raised when transport operation times out."""

    def __init__(
        self,
        message: str,
        transport_type: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        details = {
            "transport_type": transport_type,
            "endpoint": endpoint,
            "timeout_seconds": timeout_seconds,
        }
        AgentClientError.__init__(self, message, ErrorCode.TRANSPORT_TIMEOUT, details)


class ResolverError(AgentClientError):
    """Raised when URI resolution fails."""

    def __init__(self, message: str, agent_uri: Optional[str] = None):
        details = {"agent_uri": agent_uri} if agent_uri else {}
        super().__init__(message, ErrorCode.RESOLVER_ERROR, details)


class StreamingError(AgentClientError):
    """Raised when streaming operations fail."""

    def __init__(self, message: str, stream_id: Optional[str] = None):
        details = {"stream_id": stream_id} if stream_id else {}
        super().__init__(message, ErrorCode.STREAMING_ERROR, details)
