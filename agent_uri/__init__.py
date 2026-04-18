"""
Agent URI Protocol — Reference Implementation

Implementation of draft-narvaneni-agent-uri-03.

Basic usage::

    from agent_uri import AgentUri, parse_agent_uri, AgentClient
    uri = parse_agent_uri("agent://example.com/my-skill")
    print(uri.host, uri.path)
"""

__version__ = "1.0.0"
__author__ = "Yaswanth Narvaneni"
__email__ = "yaswanth@gmail.com"

from .client import AgentClient, AgentSession
from .exceptions import (
    AgentClientError,
    AgentError,
    AgentGoneError,
    AgentServerError,
    AuthenticationError,
    ContentNegotiationError,
    DelegationError,
    DescriptorError,
    DIDResolutionError,
    ErrorCode,
    HandlerError,
    InvalidInputError,
    InvocationError,
    KeyDiscoveryError,
    RedirectViolationError,
    ResolutionError,
    ResolverError,
    ScopeNarrowingViolationError,
    SessionError,
    SignatureVerificationError,
    SkillError,
    SkillNotFoundError,
    SSRFViolationError,
    StreamingError,
    TransportError,
    TransportNotSupportedError,
    TransportTimeoutError,
)
from .parser import AgentUri, parse_agent_uri
from .server import FastAPIAgentServer
from .skill import Skill, SkillMetadata, skill

__all__ = [
    "__version__",
    "AgentUri",
    "parse_agent_uri",
    "AgentClient",
    "AgentSession",
    "FastAPIAgentServer",
    "skill",
    "Skill",
    "SkillMetadata",
    # Exceptions
    "AgentError",
    "AgentClientError",
    "AgentServerError",
    "ErrorCode",
    "SkillError",
    "SkillNotFoundError",
    "HandlerError",
    "DescriptorError",
    "AuthenticationError",
    "InvalidInputError",
    "ContentNegotiationError",
    "AgentGoneError",
    "InvocationError",
    "ResolutionError",
    "ResolverError",
    "SessionError",
    "StreamingError",
    "TransportError",
    "TransportTimeoutError",
    "TransportNotSupportedError",
    "SSRFViolationError",
    "RedirectViolationError",
    "DIDResolutionError",
    "SignatureVerificationError",
    "KeyDiscoveryError",
    "DelegationError",
    "ScopeNarrowingViolationError",
]


def get_version() -> str:
    """Return the installed agent-uri version string."""
    return __version__
