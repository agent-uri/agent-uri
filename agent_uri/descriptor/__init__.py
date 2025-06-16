"""
Agent Descriptor package for parsing and validating agent.json descriptors.

This package provides utilities to work with agent.json descriptors
as defined in the agent:// protocol specification.
"""

from .compatibility import from_agent_card, to_agent_card
from .generator import AgentDescriptorGenerator
from .models import AgentDescriptor, Authentication, Capability, Provider, Skill
from .parser import load_descriptor, parse_descriptor
from .validator import (
    ValidationError,
    ValidationResult,
    validate_descriptor,
    validate_required_fields,
)

__version__ = "0.1.0"
