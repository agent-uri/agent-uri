"""
Data models for the agent descriptor (agent.json).

Aligned with draft-narvaneni-agent-uri-03. The descriptor exposes skills
(not "capabilities"), consistent with AgentCard field naming. Application
and behavioral metadata is out of scope; use JSON-LD @context or vendor
namespaces to carry extensions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class Provider:
    """Information about the provider of the agent."""

    organization: str
    url: Optional[str] = None


@dataclass
class ContentTypes:
    """Content type information for a skill, aligned with HTTP Accept/Content-Type."""

    accepts: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)


@dataclass
class Example:
    """Example invocation of a skill."""

    input: Dict[str, Any]
    output: Dict[str, Any]
    description: Optional[str] = None


@dataclass
class Dependency:
    """A declarative reference from one skill to another agent's skill.

    Informs orchestrators and topology tooling; clients MUST NOT
    pre-invoke based on this alone. Per spec ``depends`` field.
    """

    uri: str
    relation: Optional[str] = None
    version_constraint: Optional[str] = None


@dataclass
class Authentication:
    """Authentication metadata.

    Rather than embedding OAuth specifics, we reference the standard
    metadata documents (RFC 8414 Authorization Server Metadata or
    RFC 9728 Protected Resource Metadata) or a JWKS endpoint.
    """

    schemes: List[str] = field(default_factory=list)
    authorization_server: Optional[str] = None
    protected_resource_metadata: Optional[str] = None
    jwks_uri: Optional[str] = None
    jwks: Optional[Dict[str, Any]] = None


@dataclass
class Skill:
    """A skill the agent exposes, aligned with AgentCard ``skills``.

    The spec-required fields are ``id``, ``name``, ``description``.
    """

    id: str
    name: str
    description: str
    version: Optional[Union[str, float]] = None
    tags: List[str] = field(default_factory=list)
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    content_types: Optional[ContentTypes] = None
    streaming: Optional[bool] = None
    streaming_format: Optional[str] = None  # "sse", "ndjson", "grpc-stream"
    idempotent: Optional[bool] = None
    status: Optional[str] = None  # "active", "deprecated", "experimental"
    authentication: Optional[Authentication] = None
    depends: List[Dependency] = field(default_factory=list)
    examples: List[Example] = field(default_factory=list)


@dataclass
class Transport:
    """Transport metadata for an agent.

    The object MUST contain at least one of the per-transport keys. The
    ``endpoint`` key is the default when the URI carries no explicit
    ``+protocol`` binding.
    """

    endpoint: Optional[str] = None
    https: Optional[str] = None
    wss: Optional[str] = None
    grpc: Optional[str] = None
    mqtt: Optional[str] = None
    local: Optional[str] = None
    unix: Optional[str] = None

    def __post_init__(self) -> None:
        if not any(
            (
                self.endpoint,
                self.https,
                self.wss,
                self.grpc,
                self.mqtt,
                self.local,
                self.unix,
            )
        ):
            raise ValueError(
                "Transport must specify at least one of endpoint, https, wss, "
                "grpc, mqtt, local, unix"
            )


@dataclass
class Contact:
    """Contact information for the agent provider."""

    name: Optional[str] = None
    email: Optional[str] = None
    url: Optional[str] = None


@dataclass
class AgentDescriptor:
    """An agent descriptor (agent.json) per draft-narvaneni-agent-uri-03.

    Required: ``name``, ``version``, ``skills`` (non-empty list of Skill
    objects, each with ``id``, ``name``, ``description``).
    """

    name: str
    version: Union[str, float]
    skills: List[Skill]
    description: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None  # "active", "deprecated", "experimental"
    conformance_level: Optional[int] = None  # 0, 1, 2, or 3
    environment: Optional[str] = None  # production, staging, sandbox, ...
    provider: Optional[Provider] = None
    documentation_url: Optional[str] = None
    transport: Optional[Transport] = None
    authentication: Optional[Authentication] = None
    interaction_model: List[str] = field(default_factory=list)
    supported_versions: Dict[str, str] = field(default_factory=dict)
    terms_of_service: Optional[str] = None
    privacy: Optional[str] = None
    contact: Optional[Contact] = None
    context: Optional[Any] = None  # JSON-LD @context (string, object, or array)
    # Vendor / extension fields are permitted at the JSON level but are not
    # declared here; use a dict-based extension mechanism in your own code.
