"""
Compatibility module for converting between AgentDescriptor and other formats.

This module provides a framework for converting between the internal
AgentDescriptor format and external descriptor formats like Agent2Agent's
AgentCard, JSON-LD, etc. It supports extensibility to easily add new
compatibility formats in the future.
"""

from enum import Enum, auto
from typing import Any, Dict, List, Protocol, Type

from .models import (
    AgentCapabilities,
    AgentDescriptor,
    Authentication,
    Capability,
    Provider,
    Skill,
)


class DescriptorFormat(Enum):
    """Enum representing supported descriptor formats."""

    AGENT2AGENT = auto()  # Agent2Agent protocol's AgentCard
    JSONLD = auto()  # JSON-LD extended format
    # Additional formats can be added here in the future


class CompatibilityConverter(Protocol):
    """Protocol defining the interface for descriptor format converters."""

    @staticmethod
    def to_external(descriptor: AgentDescriptor) -> Dict[str, Any]:
        """Convert an AgentDescriptor to the external format."""
        ...

    @staticmethod
    def from_external(external_data: Dict[str, Any]) -> AgentDescriptor:
        """Convert from the external format to an AgentDescriptor."""
        ...

    @staticmethod
    def is_compatible(descriptor: AgentDescriptor) -> bool:
        """Check if an AgentDescriptor is compatible with the external
        format."""
        ...


class Agent2AgentConverter:
    """Converter for Agent2Agent protocol's AgentCard format."""

    @staticmethod
    def to_external(descriptor: AgentDescriptor) -> Dict[str, Any]:
        """
        Convert an AgentDescriptor to an Agent2Agent protocol AgentCard.

        Args:
            descriptor: The AgentDescriptor to convert

        Returns:
            A dictionary representation of an Agent2Agent AgentCard
        """
        # Initialize the AgentCard with required fields
        agent_card: Dict[str, Any] = {
            "name": descriptor.name,
            "version": descriptor.version,
            "url": descriptor.url or f"agent://{descriptor.name}/",
        }

        # Add optional fields if they exist
        if descriptor.description:
            agent_card["description"] = descriptor.description

        if descriptor.documentation_url:
            agent_card["documentationUrl"] = descriptor.documentation_url

        # Convert provider
        if descriptor.provider:
            agent_card["provider"] = {"organization": descriptor.provider.organization}
            if descriptor.provider.url:
                agent_card["provider"]["url"] = descriptor.provider.url

        # Convert capabilities
        agent_capabilities = descriptor.agent_capabilities or AgentCapabilities()
        agent_card["capabilities"] = {
            "streaming": agent_capabilities.streaming,
            "pushNotifications": agent_capabilities.push_notifications,
            "stateTransitionHistory": (agent_capabilities.state_transition_history),
        }

        # Convert authentication
        if descriptor.authentication:
            agent_card["authentication"] = {
                "schemes": descriptor.authentication.schemes
            }
            if (
                descriptor.authentication.details
                and "credentials" in descriptor.authentication.details
            ):
                agent_card["authentication"]["credentials"] = (
                    descriptor.authentication.details["credentials"]
                )

        # Add defaultInputModes and defaultOutputModes
        agent_card["defaultInputModes"] = descriptor.default_input_modes
        agent_card["defaultOutputModes"] = descriptor.default_output_modes

        # Convert skills
        agent_card["skills"] = []
        for skill in descriptor.skills:
            skill_dict: Dict[str, Any] = {"id": skill.id, "name": skill.name}

            if skill.description:
                skill_dict["description"] = skill.description

            if skill.tags:
                skill_dict["tags"] = skill.tags

            if skill.examples:
                skill_dict["examples"] = skill.examples

            if skill.input_modes:
                skill_dict["inputModes"] = skill.input_modes

            if skill.output_modes:
                skill_dict["outputModes"] = skill.output_modes

            agent_card["skills"].append(skill_dict)

        return agent_card

    @staticmethod
    def from_external(agent_card: Dict[str, Any]) -> AgentDescriptor:
        """
        Convert an Agent2Agent protocol AgentCard to an AgentDescriptor.

        Args:
            agent_card: A dictionary representing an Agent2Agent AgentCard

        Returns:
            An AgentDescriptor object

        Raises:
            ValueError: If required fields are missing from the AgentCard
        """
        # Validate required fields
        required_fields = ["name", "url", "version", "capabilities", "skills"]
        for field in required_fields:
            if field not in agent_card:
                raise ValueError(f"Missing required field in AgentCard: {field}")

        # Parse provider if it exists
        provider = None
        if "provider" in agent_card and agent_card["provider"]:
            provider_data = agent_card["provider"]
            if "organization" not in provider_data:
                raise ValueError("Provider missing required field: organization")

            provider = Provider(
                organization=provider_data["organization"], url=provider_data.get("url")
            )

        # Parse authentication if it exists
        authentication = None
        if "authentication" in agent_card and agent_card["authentication"]:
            auth_data = agent_card["authentication"]
            if "schemes" not in auth_data:
                raise ValueError("Authentication missing required field: schemes")

            details = {}
            if "credentials" in auth_data:
                details["credentials"] = auth_data["credentials"]

            authentication = Authentication(
                schemes=auth_data["schemes"], details=details if details else None
            )

        # Parse capabilities
        capabilities_data = agent_card["capabilities"]
        agent_capabilities = AgentCapabilities(
            streaming=capabilities_data.get("streaming", False),
            push_notifications=capabilities_data.get("pushNotifications", False),
            state_transition_history=capabilities_data.get(
                "stateTransitionHistory", False
            ),
        )

        # Parse skills
        skills: List[Skill] = []
        for skill_data in agent_card["skills"]:
            if "id" not in skill_data or "name" not in skill_data:
                raise ValueError("Skill missing required fields: id or name")

            skill = Skill(
                id=skill_data["id"],
                name=skill_data["name"],
                description=skill_data.get("description"),
                tags=skill_data.get("tags"),
                examples=skill_data.get("examples"),
                input_modes=skill_data.get("inputModes"),
                output_modes=skill_data.get("outputModes"),
            )
            skills.append(skill)

        # Build a minimal capability list from skills
        capabilities: List[Capability] = []
        for skill in skills:
            capability = Capability(
                name=f"capability-{skill.id}",
                description=skill.description,
                tags=skill.tags or [],
            )
            capabilities.append(capability)

        # Create and return the AgentDescriptor
        return AgentDescriptor(
            name=agent_card["name"],
            version=agent_card["version"],
            capabilities=capabilities,
            description=agent_card.get("description"),
            url=agent_card["url"],
            provider=provider,
            documentation_url=agent_card.get("documentationUrl"),
            skills=skills,
            authentication=authentication,
            default_input_modes=agent_card.get("defaultInputModes", ["text"]),
            default_output_modes=agent_card.get("defaultOutputModes", ["text"]),
            agent_capabilities=agent_capabilities,
        )

    @staticmethod
    def is_compatible(descriptor: AgentDescriptor) -> bool:
        """
        Check if an AgentDescriptor is compatible with the Agent2Agent
        protocol's AgentCard format.

        Args:
            descriptor: The AgentDescriptor to check

        Returns:
            True if the descriptor is compatible, False otherwise
        """
        # Check required fields
        if not descriptor.name or not descriptor.version:
            return False

        if not descriptor.url:
            # Not a deal-breaker, but less compatible
            pass

        # Should have at least one skill for A2A compatibility
        if not descriptor.skills:
            return False

        # Each skill should have id and name
        for skill in descriptor.skills:
            if not skill.id or not skill.name:
                return False

        # Should have at least one capability
        if not descriptor.capabilities:
            return False

        return True


class JsonLdConverter:
    """Converter for JSON-LD extended format."""

    @staticmethod
    def to_external(descriptor: AgentDescriptor) -> Dict[str, Any]:
        """
        Convert an AgentDescriptor to a JSON-LD extended format.

        Args:
            descriptor: The AgentDescriptor to convert

        Returns:
            A dictionary representation in JSON-LD format
        """
        # Start with a basic dict representation
        from .parser import descriptor_to_dict

        jsonld_dict = descriptor_to_dict(descriptor)

        # Add JSON-LD specific fields
        jsonld_dict["@context"] = (
            descriptor.context or "https://example.org/agent-context.jsonld"
        )

        # You could add additional JSON-LD specific transformations here

        return jsonld_dict

    @staticmethod
    def from_external(jsonld_data: Dict[str, Any]) -> AgentDescriptor:
        """
        Convert from a JSON-LD extended format to an AgentDescriptor.

        Args:
            jsonld_data: A dictionary representing data in JSON-LD format

        Returns:
            An AgentDescriptor object
        """
        # Use the standard parser which already handles @context ->
        # context conversion
        from .parser import parse_descriptor

        return parse_descriptor(jsonld_data)

    @staticmethod
    def is_compatible(descriptor: AgentDescriptor) -> bool:
        """
        Check if an AgentDescriptor is compatible with the JSON-LD format.

        Args:
            descriptor: The AgentDescriptor to check

        Returns:
            True if the descriptor is compatible with JSON-LD, False otherwise
        """
        # All descriptors are technically JSON-LD compatible, but ideally
        # have a context
        return True


# Registry of converters for each format
CONVERTERS: Dict[DescriptorFormat, Type[CompatibilityConverter]] = {
    DescriptorFormat.AGENT2AGENT: Agent2AgentConverter,
    DescriptorFormat.JSONLD: JsonLdConverter,
    # Add more converters here as they are implemented
}


def to_format(
    descriptor: AgentDescriptor, format_type: DescriptorFormat
) -> Dict[str, Any]:
    """
    Convert an AgentDescriptor to the specified external format.

    Args:
        descriptor: The AgentDescriptor to convert
        format_type: The target format to convert to

    Returns:
        A dictionary representation in the target format

    Raises:
        ValueError: If the format is not supported
    """
    if format_type not in CONVERTERS:
        raise ValueError(f"Unsupported format: {format_type}")

    converter = CONVERTERS[format_type]
    return converter.to_external(descriptor)


def from_format(data: Dict[str, Any], format_type: DescriptorFormat) -> AgentDescriptor:
    """
    Convert from an external format to an AgentDescriptor.

    Args:
        data: A dictionary representing data in the external format
        format_type: The source format to convert from

    Returns:
        An AgentDescriptor object

    Raises:
        ValueError: If the format is not supported
    """
    if format_type not in CONVERTERS:
        raise ValueError(f"Unsupported format: {format_type}")

    converter = CONVERTERS[format_type]
    return converter.from_external(data)


def is_format_compatible(
    descriptor: AgentDescriptor, format_type: DescriptorFormat
) -> bool:
    """
    Check if an AgentDescriptor is compatible with the specified format.

    Args:
        descriptor: The AgentDescriptor to check
        format_type: The format to check compatibility against

    Returns:
        True if the descriptor is compatible with the format, False otherwise

    Raises:
        ValueError: If the format is not supported
    """
    if format_type not in CONVERTERS:
        raise ValueError(f"Unsupported format: {format_type}")

    converter = CONVERTERS[format_type]
    return converter.is_compatible(descriptor)


# Convenience functions for Agent2Agent format, since it's currently the
# primary use case
def to_agent_card(descriptor: AgentDescriptor) -> Dict[str, Any]:
    """Convert an AgentDescriptor to an Agent2Agent protocol AgentCard."""
    return to_format(descriptor, DescriptorFormat.AGENT2AGENT)


def from_agent_card(agent_card: Dict[str, Any]) -> AgentDescriptor:
    """Convert an Agent2Agent protocol AgentCard to an AgentDescriptor."""
    return from_format(agent_card, DescriptorFormat.AGENT2AGENT)


def is_agent_card_compatible(descriptor: AgentDescriptor) -> bool:
    """Check if an AgentDescriptor is compatible with the Agent2Agent
    protocol's AgentCard format."""
    return is_format_compatible(descriptor, DescriptorFormat.AGENT2AGENT)
