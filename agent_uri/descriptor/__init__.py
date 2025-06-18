"""
Agent Descriptor package for parsing and validating agent.json descriptors.

This package provides utilities to work with agent.json descriptors
as defined in the agent:// protocol specification.
"""

# Import version from main package
from .. import __version__  # noqa: F401
from .compatibility import from_agent_card, to_agent_card  # noqa: F401
from .generator import AgentDescriptorGenerator  # noqa: F401
from .models import (  # noqa: F401
    AgentDescriptor,
    Authentication,
    Capability,
    Provider,
    Skill,
)
from .parser import load_descriptor, parse_descriptor  # noqa: F401
from .validator import (  # noqa: F401
    ValidationError,
    ValidationResult,
    validate_descriptor,
    validate_required_fields,
)
