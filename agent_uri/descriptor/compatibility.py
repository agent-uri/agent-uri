"""
Compatibility converters between the agent:// descriptor and external formats.

Aligned with draft-narvaneni-agent-uri-03. Since our descriptor's
``skills[]`` already maps 1:1 to AgentCard's ``skills``, the converter
is straightforward. AgentCard-specific fields that don't exist in our
schema (``capabilities`` boolean flags, ``defaultInputModes``,
``defaultOutputModes``) are carried through the descriptor's extension
namespace under an ``x-a2a-`` prefix.
"""

from enum import Enum, auto
from typing import Any, Dict, List, Protocol, Type

from .models import AgentDescriptor, Authentication, Provider, Skill


class DescriptorFormat(Enum):
    """Supported descriptor-format conversions."""

    AGENT2AGENT = auto()
    JSONLD = auto()


class CompatibilityConverter(Protocol):
    """Interface for descriptor-format converters."""

    @staticmethod
    def to_external(descriptor: AgentDescriptor) -> Dict[str, Any]: ...

    @staticmethod
    def from_external(external_data: Dict[str, Any]) -> AgentDescriptor: ...

    @staticmethod
    def is_compatible(descriptor: AgentDescriptor) -> bool: ...


def _skill_to_agent_card(skill: Skill) -> Dict[str, Any]:
    card: Dict[str, Any] = {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
    }
    if skill.tags:
        card["tags"] = list(skill.tags)
    if skill.examples:
        card["examples"] = [ex.description or "" for ex in skill.examples]
    # AgentCard-specific extensions arrive via the x-a2a- namespace;
    # here we expose them if present on the source skill.
    return card


def _skill_from_agent_card(data: Dict[str, Any]) -> Skill:
    if "id" not in data or "name" not in data:
        raise ValueError("AgentCard skill missing required id or name")
    return Skill(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        tags=data.get("tags", []),
    )


class Agent2AgentConverter:
    """Convert between AgentDescriptor and an Agent2Agent AgentCard.

    The mapping:

    * ``name``, ``version``, ``url`` — same semantics both ways.
    * ``description`` — same.
    * ``provider`` — mapped directly.
    * ``authentication.schemes`` — carried through as AgentCard schemes.
    * ``skills`` — aligned 1:1.
    * AgentCard-specific fields (``capabilities`` boolean flags,
      ``defaultInputModes``, ``defaultOutputModes``) are carried as
      top-level extension fields on the AgentCard side; on the
      descriptor side they are not represented (use vendor-prefixed
      ``x-a2a-*`` extension fields in custom tooling if you need to
      preserve them).
    """

    @staticmethod
    def to_external(descriptor: AgentDescriptor) -> Dict[str, Any]:
        agent_card: Dict[str, Any] = {
            "name": descriptor.name,
            "version": descriptor.version,
            "url": descriptor.url or f"agent://{descriptor.name}/",
        }
        if descriptor.description:
            agent_card["description"] = descriptor.description
        if descriptor.documentation_url:
            agent_card["documentationUrl"] = descriptor.documentation_url

        if descriptor.provider:
            agent_card["provider"] = {"organization": descriptor.provider.organization}
            if descriptor.provider.url:
                agent_card["provider"]["url"] = descriptor.provider.url

        if descriptor.authentication:
            agent_card["authentication"] = {
                "schemes": list(descriptor.authentication.schemes or []),
            }

        # Default A2A capability-flag object when not provided explicitly.
        agent_card["capabilities"] = {
            "streaming": any(s.streaming for s in descriptor.skills),
            "pushNotifications": False,
            "stateTransitionHistory": False,
        }

        agent_card["defaultInputModes"] = ["text"]
        agent_card["defaultOutputModes"] = ["text"]

        agent_card["skills"] = [
            _skill_to_agent_card(skill) for skill in descriptor.skills
        ]

        return agent_card

    @staticmethod
    def from_external(agent_card: Dict[str, Any]) -> AgentDescriptor:
        for field_name in ("name", "url", "version", "skills"):
            if field_name not in agent_card:
                raise ValueError(f"Missing required field in AgentCard: {field_name}")

        provider = None
        if isinstance(agent_card.get("provider"), dict):
            provider_data = agent_card["provider"]
            if "organization" not in provider_data:
                raise ValueError("Provider missing required field: organization")
            provider = Provider(
                organization=provider_data["organization"],
                url=provider_data.get("url"),
            )

        authentication = None
        if isinstance(agent_card.get("authentication"), dict):
            auth_data = agent_card["authentication"]
            schemes = auth_data.get("schemes") or []
            if not isinstance(schemes, list):
                raise ValueError("Authentication schemes must be a list")
            authentication = Authentication(schemes=schemes)

        skills: List[Skill] = [_skill_from_agent_card(s) for s in agent_card["skills"]]

        return AgentDescriptor(
            name=agent_card["name"],
            version=agent_card["version"],
            skills=skills,
            description=agent_card.get("description"),
            url=agent_card["url"],
            provider=provider,
            documentation_url=agent_card.get("documentationUrl"),
            authentication=authentication,
        )

    @staticmethod
    def is_compatible(descriptor: AgentDescriptor) -> bool:
        if not descriptor.name or not descriptor.version:
            return False
        if not descriptor.skills:
            return False
        for skill in descriptor.skills:
            if not skill.id or not skill.name or not skill.description:
                return False
        return True


class JsonLdConverter:
    """Pass-through converter that attaches an @context."""

    @staticmethod
    def to_external(descriptor: AgentDescriptor) -> Dict[str, Any]:
        from .parser import descriptor_to_dict

        jsonld_dict = descriptor_to_dict(descriptor)
        if "@context" not in jsonld_dict:
            jsonld_dict["@context"] = descriptor.context or []
        return jsonld_dict

    @staticmethod
    def from_external(jsonld_data: Dict[str, Any]) -> AgentDescriptor:
        from .parser import parse_descriptor

        return parse_descriptor(jsonld_data)

    @staticmethod
    def is_compatible(descriptor: AgentDescriptor) -> bool:
        return True


CONVERTERS: Dict[DescriptorFormat, Type[CompatibilityConverter]] = {
    DescriptorFormat.AGENT2AGENT: Agent2AgentConverter,
    DescriptorFormat.JSONLD: JsonLdConverter,
}


def to_format(
    descriptor: AgentDescriptor, format_type: DescriptorFormat
) -> Dict[str, Any]:
    if format_type not in CONVERTERS:
        raise ValueError(f"Unsupported format: {format_type}")
    return CONVERTERS[format_type].to_external(descriptor)


def from_format(data: Dict[str, Any], format_type: DescriptorFormat) -> AgentDescriptor:
    if format_type not in CONVERTERS:
        raise ValueError(f"Unsupported format: {format_type}")
    return CONVERTERS[format_type].from_external(data)


def is_format_compatible(
    descriptor: AgentDescriptor, format_type: DescriptorFormat
) -> bool:
    if format_type not in CONVERTERS:
        raise ValueError(f"Unsupported format: {format_type}")
    return CONVERTERS[format_type].is_compatible(descriptor)


def to_agent_card(descriptor: AgentDescriptor) -> Dict[str, Any]:
    """Convert an AgentDescriptor to an Agent2Agent AgentCard."""
    return to_format(descriptor, DescriptorFormat.AGENT2AGENT)


def from_agent_card(agent_card: Dict[str, Any]) -> AgentDescriptor:
    """Convert an Agent2Agent AgentCard to an AgentDescriptor."""
    return from_format(agent_card, DescriptorFormat.AGENT2AGENT)


def is_agent_card_compatible(descriptor: AgentDescriptor) -> bool:
    """Check if an AgentDescriptor is compatible with Agent2Agent."""
    return is_format_compatible(descriptor, DescriptorFormat.AGENT2AGENT)
