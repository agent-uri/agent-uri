"""
Exceptions for the agent-uri package.

Aligned with draft-narvaneni-agent-uri-03. HTTP-extended 4-digit error
codes provide a lookup key parallel to HTTP status codes; see ErrorCode.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorCode(str, Enum):
    """Error codes for agent-uri operations, extending HTTP status patterns."""

    # Client errors (4xxx) — bad request / input issues
    INVALID_URI_FORMAT = "4001"
    INVALID_SCHEME = "4002"
    INVALID_TRANSPORT = "4003"
    MISSING_AUTHORITY = "4004"
    INVALID_QUERY = "4005"
    INVALID_INPUT = "4006"
    MALFORMED_DESCRIPTOR = "4007"

    AUTHENTICATION_ERROR = "4011"
    AUTHENTICATION_REQUIRED = "4012"

    SKILL_NOT_FOUND = "4041"  # HTTP 404 — skill id unknown
    AGENT_NOT_FOUND = "4042"
    ENDPOINT_NOT_FOUND = "4043"

    CONTENT_NOT_ACCEPTABLE = "4061"  # HTTP 406 — content negotiation failure

    AGENT_GONE = "4101"  # HTTP 410 — agent deprecated / decommissioned

    TRANSPORT_TIMEOUT = "4081"
    RESOLUTION_TIMEOUT = "4082"

    # Server errors (5xxx) — internal / processing
    SKILL_ERROR = "5001"  # runtime error inside a skill
    HANDLER_ERROR = "5002"
    DESCRIPTOR_ERROR = "5003"
    CONFIGURATION_ERROR = "5004"
    INVOCATION_ERROR = "5005"
    SESSION_ERROR = "5006"
    STREAMING_ERROR = "5007"

    TRANSPORT_ERROR = "5021"
    TRANSPORT_UNAVAILABLE = "5022"

    AGENT_UNAVAILABLE = "5031"
    RESOLVER_ERROR = "5032"
    RESOLUTION_ERROR = "5033"
    SSRF_VIOLATION = "5034"
    REGISTRY_NOT_FOUND = "5035"
    DESCRIPTOR_FETCH_ERROR = "5036"
    REDIRECT_VIOLATION = "5037"
    DID_RESOLUTION_ERROR = "5038"

    SIGNATURE_VERIFICATION_ERROR = "5041"
    KEY_DISCOVERY_ERROR = "5042"
    DELEGATION_ERROR = "5043"
    SCOPE_NARROWING_VIOLATION = "5044"

    UNKNOWN_ERROR = "5999"


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


# ---------------------------------------------------------------------------
# Server-side exceptions
# ---------------------------------------------------------------------------


class AgentServerError(AgentError):
    """Base exception for all agent server errors."""


class SkillNotFoundError(AgentServerError):
    """Raised when a skill is not found."""

    def __init__(
        self,
        skill_id: str,
        available_skills: Optional[List[str]] = None,
    ):
        message = f"Skill '{skill_id}' not found"
        if available_skills:
            message += f". Available skills: {', '.join(available_skills)}"
        details = {
            "skill_id": skill_id,
            "available_skills": available_skills or [],
        }
        super().__init__(message, ErrorCode.SKILL_NOT_FOUND, details)


class SkillError(AgentServerError):
    """Raised when a skill cannot be invoked."""

    def __init__(self, message: str, skill_id: Optional[str] = None):
        details = {"skill_id": skill_id} if skill_id else {}
        super().__init__(message, ErrorCode.SKILL_ERROR, details)


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


class ContentNegotiationError(AgentServerError):
    """Raised when content negotiation fails (HTTP 406)."""

    def __init__(
        self,
        message: str,
        requested: Optional[str] = None,
        supported: Optional[List[str]] = None,
    ):
        details = {"requested": requested, "supported": supported or []}
        super().__init__(message, ErrorCode.CONTENT_NOT_ACCEPTABLE, details)


class AgentGoneError(AgentServerError):
    """Raised when an agent or skill is permanently gone (HTTP 410)."""

    def __init__(self, message: str, agent_uri: Optional[str] = None):
        details = {"agent_uri": agent_uri} if agent_uri else {}
        super().__init__(message, ErrorCode.AGENT_GONE, details)


# ---------------------------------------------------------------------------
# Client-side exceptions
# ---------------------------------------------------------------------------


class AgentClientError(AgentError):
    """Base exception for client errors."""


class InvocationError(AgentClientError):
    """Raised when a skill invocation fails client-side."""

    def __init__(
        self,
        message: str,
        agent_uri: Optional[str] = None,
        skill_id: Optional[str] = None,
    ):
        details = {"agent_uri": agent_uri, "skill_id": skill_id}
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
    """Raised when the transport layer fails."""

    def __init__(
        self,
        message: str,
        transport_type: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        details = {"transport_type": transport_type, "endpoint": endpoint}
        super().__init__(message, ErrorCode.TRANSPORT_ERROR, details)


class TransportTimeoutError(TransportError):
    """Raised when a transport operation times out."""

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


class TransportNotSupportedError(TransportError):
    """Raised when a requested transport is not supported by the runtime."""

    def __init__(self, message: str, transport_type: Optional[str] = None):
        details = {"transport_type": transport_type} if transport_type else {}
        AgentClientError.__init__(
            self, message, ErrorCode.TRANSPORT_UNAVAILABLE, details
        )


class ResolverError(AgentClientError):
    """Raised when URI resolution fails (generic)."""

    def __init__(self, message: str, agent_uri: Optional[str] = None):
        details = {"agent_uri": agent_uri} if agent_uri else {}
        super().__init__(message, ErrorCode.RESOLVER_ERROR, details)


class ResolverNotFoundError(ResolverError):
    """Raised when no descriptor is found for an agent URI."""


class ResolverTimeoutError(ResolverError):
    """Raised when resolver HTTP requests time out."""

    def __init__(self, message: str, agent_uri: Optional[str] = None):
        details = {"agent_uri": agent_uri} if agent_uri else {}
        AgentClientError.__init__(self, message, ErrorCode.RESOLUTION_TIMEOUT, details)


class SSRFViolationError(ResolverError):
    """Raised when a resolver detects a disallowed (private/loopback) target."""

    def __init__(self, message: str, target: Optional[str] = None):
        details = {"target": target} if target else {}
        AgentClientError.__init__(self, message, ErrorCode.SSRF_VIOLATION, details)


class RedirectViolationError(ResolverError):
    """Raised when a resolver rejects an HTTP redirect target (SSRF / policy)."""

    def __init__(self, message: str, target: Optional[str] = None):
        details = {"target": target} if target else {}
        AgentClientError.__init__(self, message, ErrorCode.REDIRECT_VIOLATION, details)


class DIDResolutionError(ResolverError):
    """Raised when DID authority resolution fails."""

    def __init__(self, message: str, did: Optional[str] = None):
        details = {"did": did} if did else {}
        AgentClientError.__init__(
            self, message, ErrorCode.DID_RESOLUTION_ERROR, details
        )


class StreamingError(AgentClientError):
    """Raised when streaming operations fail."""

    def __init__(self, message: str, stream_id: Optional[str] = None):
        details = {"stream_id": stream_id} if stream_id else {}
        super().__init__(message, ErrorCode.STREAMING_ERROR, details)


class SignatureVerificationError(AgentClientError):
    """Raised when HTTP Message Signatures (RFC 9421) verification fails."""

    def __init__(self, message: str, component: Optional[str] = None):
        details = {"component": component} if component else {}
        super().__init__(message, ErrorCode.SIGNATURE_VERIFICATION_ERROR, details)


class KeyDiscoveryError(AgentClientError):
    """Raised when signature / delegation key discovery fails."""

    def __init__(self, message: str, source: Optional[str] = None):
        details = {"source": source} if source else {}
        super().__init__(message, ErrorCode.KEY_DISCOVERY_ERROR, details)


class DelegationError(AgentClientError):
    """Raised when RFC 8693 delegation chain validation fails."""

    def __init__(self, message: str, reason: Optional[str] = None):
        details = {"reason": reason} if reason else {}
        super().__init__(message, ErrorCode.DELEGATION_ERROR, details)


class ScopeNarrowingViolationError(DelegationError):
    """Raised when a nested act-claim widens scope rather than narrowing it."""

    def __init__(
        self,
        message: str,
        outer_scope: Optional[str] = None,
        inner_scope: Optional[str] = None,
    ):
        details = {"outer_scope": outer_scope, "inner_scope": inner_scope}
        AgentClientError.__init__(
            self, message, ErrorCode.SCOPE_NARROWING_VIOLATION, details
        )
