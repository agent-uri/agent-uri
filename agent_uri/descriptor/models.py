"""
Data models for the agent descriptor (agent.json).

This module defines the data classes that represent an agent descriptor
as specified in the agent:// protocol RFC Section 7.
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
    """Content type information for a capability."""

    input_format: List[str] = field(default_factory=list)
    output_format: List[str] = field(default_factory=list)


@dataclass
class Example:
    """Example invocation of a capability."""

    input: Dict[str, Any]
    output: Dict[str, Any]
    description: Optional[str] = None


@dataclass
class Capability:
    """A capability offered by an agent."""

    name: str
    description: Optional[str] = None
    version: Optional[Union[str, float]] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    is_deterministic: Optional[bool] = None
    expected_output_variability: Optional[str] = None
    content_types: Optional[ContentTypes] = None
    requires_context: Optional[bool] = None
    memory_enabled: Optional[bool] = None
    response_latency: Optional[str] = None
    streaming: Optional[bool] = None
    tags: List[str] = field(default_factory=list)
    deprecated: Optional[bool] = None
    deprecated_reason: Optional[str] = None
    examples: List[Example] = field(default_factory=list)


@dataclass
class Authentication:
    """Authentication methods supported by the agent."""

    schemes: List[str]
    details: Optional[Dict[str, Any]] = None


@dataclass
class Skill:
    """A skill the agent possesses, which may map to multiple capabilities."""

    id: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    input_modes: Optional[List[str]] = None
    output_modes: Optional[List[str]] = None


@dataclass
class Endpoints:
    """Transport-specific endpoints for the agent."""

    https: Optional[str] = None
    wss: Optional[str] = None
    local: Optional[str] = None


@dataclass
class Contact:
    """Contact information for the agent provider."""

    name: Optional[str] = None
    email: Optional[str] = None
    url: Optional[str] = None


@dataclass
class AgentCapabilities:
    """Capabilities configuration for A2A compatibility."""

    streaming: bool = False
    push_notifications: bool = False
    state_transition_history: bool = False


@dataclass
class AgentDescriptor:
    """
    Main class representing an agent descriptor (agent.json).

    This class maps directly to the structure of agent.json files
    as specified in the agent:// protocol RFC Section 7.
    """

    name: str
    version: Union[str, float]
    capabilities: List[Capability]
    description: Optional[str] = None
    url: Optional[str] = None
    provider: Optional[Provider] = None
    documentation_url: Optional[str] = None
    interaction_model: Optional[str] = None
    orchestration: Optional[str] = None
    envelope_schemas: List[str] = field(default_factory=list)
    supported_versions: Dict[str, str] = field(default_factory=dict)
    authentication: Optional[Authentication] = None
    skills: List[Skill] = field(default_factory=list)
    endpoints: Optional[Endpoints] = None
    status: Optional[str] = None
    terms_of_service: Optional[str] = None
    privacy: Optional[str] = None
    contact: Optional[Contact] = None
    context: Optional[str] = None  # JSON-LD context

    # A2A compatibility fields
    default_input_modes: List[str] = field(default_factory=lambda: ["text"])
    default_output_modes: List[str] = field(default_factory=lambda: ["text"])
    agent_capabilities: Optional[AgentCapabilities] = None
