"""
Agent Descriptor package for parsing and validating agent.json descriptors.

This package provides utilities to work with agent.json descriptors
as defined in the agent:// protocol specification.
"""

from agent_descriptor.models import (
    AgentDescriptor,
    Capability,
    Provider,
    Authentication,
    Skill
)
from agent_descriptor.parser import parse_descriptor, load_descriptor
from agent_descriptor.validator import (
    validate_descriptor,
    validate_required_fields,
    ValidationError,
    ValidationResult
)
from agent_descriptor.compatibility import (
    to_agent_card,
    from_agent_card
)

__version__ = "0.1.0"
