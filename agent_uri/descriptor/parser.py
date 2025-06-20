"""
Parser for agent.json descriptors.

This module provides functions to parse agent.json descriptors
from various sources, including JSON objects, files, and URLs.
"""

import json
import os
import urllib.request
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from .models import (
    AgentCapabilities,
    AgentDescriptor,
    Authentication,
    Capability,
    Contact,
    ContentTypes,
    Endpoints,
    Example,
    Provider,
    Skill,
)


def _snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _convert_keys(obj: Any) -> Any:
    """
    Recursively convert keys from snake_case to camelCase.
    Used when converting from internal model to external JSON.
    """
    if isinstance(obj, dict):
        return {_snake_to_camel(k): _convert_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_keys(item) for item in obj]
    return obj


def _camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _convert_dict_keys(d: Any) -> Any:
    """
    Recursively convert dictionary keys from camelCase to snake_case.
    Used when parsing external JSON to internal model.
    """
    if not isinstance(d, dict):
        return d

    result: Dict[str, Any] = {}
    for key, value in d.items():
        snake_key = _camel_to_snake(key)

        if isinstance(value, dict):
            result[snake_key] = _convert_dict_keys(value)
        elif isinstance(value, list):
            result[snake_key] = [
                _convert_dict_keys(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[snake_key] = value

    return result


def _parse_provider(data: Dict[str, Any]) -> Optional[Provider]:
    """Parse provider data from a dictionary."""
    if not data:
        return None

    return Provider(organization=data.get("organization", ""), url=data.get("url"))


def _parse_content_types(data: Dict[str, Any]) -> Optional[ContentTypes]:
    """Parse content types data from a dictionary."""
    if not data:
        return None

    return ContentTypes(
        input_format=data.get("input_format", []),
        output_format=data.get("output_format", []),
    )


def _parse_examples(examples_data: list) -> list:
    """Parse capability examples from a list."""
    if not examples_data:
        return []

    examples = []
    for example_data in examples_data:
        examples.append(
            Example(
                input=example_data.get("input", {}),
                output=example_data.get("output", {}),
                description=example_data.get("description"),
            )
        )

    return examples


def _parse_capabilities(capabilities_data: list) -> list:
    """Parse capabilities from a list."""
    if not capabilities_data:
        return []

    capabilities = []
    for capability_data in capabilities_data:
        content_types_data = capability_data.get("content_types")
        content_types = (
            _parse_content_types(content_types_data) if content_types_data else None
        )

        examples_data = capability_data.get("examples")
        examples = _parse_examples(examples_data) if examples_data else []

        capabilities.append(
            Capability(
                name=capability_data.get("name", ""),
                description=capability_data.get("description"),
                version=capability_data.get("version"),
                input=capability_data.get("input"),
                output=capability_data.get("output"),
                is_deterministic=capability_data.get("is_deterministic"),
                expected_output_variability=capability_data.get(
                    "expected_output_variability"
                ),
                content_types=content_types,
                requires_context=capability_data.get("requires_context"),
                memory_enabled=capability_data.get("memory_enabled"),
                response_latency=capability_data.get("response_latency"),
                streaming=capability_data.get("streaming"),
                tags=capability_data.get("tags", []),
                deprecated=capability_data.get("deprecated"),
                deprecated_reason=capability_data.get("deprecated_reason"),
                examples=examples,
            )
        )

    return capabilities


def _parse_authentication(data: Dict[str, Any]) -> Optional[Authentication]:
    """Parse authentication data from a dictionary."""
    if not data:
        return None

    return Authentication(schemes=data.get("schemes", []), details=data.get("details"))


def _parse_skills(skills_data: list) -> list:
    """Parse skills from a list."""
    if not skills_data:
        return []

    skills = []
    for skill_data in skills_data:
        skills.append(
            Skill(
                id=skill_data.get("id", ""),
                name=skill_data.get("name", ""),
                description=skill_data.get("description"),
                tags=skill_data.get("tags"),
                examples=skill_data.get("examples"),
                input_modes=skill_data.get("input_modes"),
                output_modes=skill_data.get("output_modes"),
            )
        )

    return skills


def _parse_endpoints(data: Dict[str, Any]) -> Optional[Endpoints]:
    """Parse endpoints data from a dictionary."""
    if not data:
        return None

    return Endpoints(
        https=data.get("https"), wss=data.get("wss"), local=data.get("local")
    )


def _parse_contact(data: Dict[str, Any]) -> Optional[Contact]:
    """Parse contact data from a dictionary."""
    if not data:
        return None

    return Contact(name=data.get("name"), email=data.get("email"), url=data.get("url"))


def _parse_agent_capabilities(data: Dict[str, Any]) -> Optional[AgentCapabilities]:
    """Parse agent capabilities data from a dictionary."""
    if not data:
        return None

    return AgentCapabilities(
        streaming=data.get("streaming", False),
        push_notifications=data.get("push_notifications", False),
        state_transition_history=data.get("state_transition_history", False),
    )


def parse_descriptor(descriptor_data: Dict[str, Any]) -> AgentDescriptor:
    """
    Parse an agent descriptor from a dictionary.

    Args:
        descriptor_data: A dictionary containing the descriptor data

    Returns:
        An AgentDescriptor object

    Raises:
        ValueError: If required fields are missing
    """
    # Convert camelCase keys to snake_case for our internal model
    data = _convert_dict_keys(descriptor_data)

    # Extract required fields
    if "name" not in data:
        raise ValueError("Descriptor missing required field: name")
    if "version" not in data:
        raise ValueError("Descriptor missing required field: version")
    if "capabilities" not in data:
        raise ValueError("Descriptor missing required field: capabilities")

    # Parse nested objects
    provider_data = data.get("provider")
    provider = _parse_provider(provider_data) if provider_data else None

    capabilities_data = data.get("capabilities", [])
    capabilities = _parse_capabilities(capabilities_data)

    authentication_data = data.get("authentication")
    authentication = (
        _parse_authentication(authentication_data) if authentication_data else None
    )

    skills_data = data.get("skills", [])
    skills = _parse_skills(skills_data)

    endpoints_data = data.get("endpoints")
    endpoints = _parse_endpoints(endpoints_data) if endpoints_data else None

    contact_data = data.get("contact")
    contact = _parse_contact(contact_data) if contact_data else None

    agent_capabilities_data = data.get("agent_capabilities")
    agent_capabilities = (
        _parse_agent_capabilities(agent_capabilities_data)
        if agent_capabilities_data
        else None
    )

    # Create and return the AgentDescriptor
    return AgentDescriptor(
        name=data["name"],
        version=data["version"],
        capabilities=capabilities,
        description=data.get("description"),
        url=data.get("url"),
        provider=provider,
        documentation_url=data.get("documentation_url"),
        interaction_model=data.get("interaction_model"),
        orchestration=data.get("orchestration"),
        envelope_schemas=data.get("envelope_schemas", []),
        supported_versions=data.get("supported_versions", {}),
        authentication=authentication,
        skills=skills,
        endpoints=endpoints,
        status=data.get("status"),
        terms_of_service=data.get("terms_of_service"),
        privacy=data.get("privacy"),
        contact=contact,
        context=data.get("@context"),
        default_input_modes=data.get("default_input_modes", ["text"]),
        default_output_modes=data.get("default_output_modes", ["text"]),
        agent_capabilities=agent_capabilities,
    )


def load_descriptor(source: Union[str, Dict[str, Any]]) -> AgentDescriptor:
    """
    Load an agent descriptor from a file path, URL, or dictionary.

    Args:
        source: A file path, URL, or dictionary containing the descriptor data

    Returns:
        An AgentDescriptor object

    Raises:
        ValueError: If the source type is invalid or required fields are missing
        FileNotFoundError: If the source file does not exist
        urllib.error.URLError: If the URL cannot be accessed
    """
    if isinstance(source, dict):
        return parse_descriptor(source)

    if not isinstance(source, str):
        raise ValueError(f"Invalid source type: {type(source)}")

    # Check if source is a URL
    parsed_url = urlparse(source)
    if parsed_url.scheme in ("http", "https"):
        with urllib.request.urlopen(source) as response:  # nosec B310
            descriptor_data = json.loads(response.read())
            return parse_descriptor(descriptor_data)

    # Otherwise, treat as file path
    if not os.path.isfile(source):
        raise FileNotFoundError(f"File not found: {source}")

    with open(source, "r", encoding="utf-8") as f:
        descriptor_data = json.load(f)
        return parse_descriptor(descriptor_data)


def descriptor_to_dict(descriptor: AgentDescriptor) -> Dict[str, Any]:
    """
    Convert an AgentDescriptor object to a dictionary.

    Args:
        descriptor: An AgentDescriptor object

    Returns:
        A dictionary representation of the descriptor
    """
    # Convert to dictionary using dataclasses.asdict
    from dataclasses import asdict

    descriptor_dict = asdict(descriptor)

    # Remove None values
    descriptor_dict = {k: v for k, v in descriptor_dict.items() if v is not None}

    # Change '@context' key
    if "context" in descriptor_dict:
        descriptor_dict["@context"] = descriptor_dict.pop("context")

    # Convert snake_case keys to camelCase
    return _convert_keys(descriptor_dict)


def save_descriptor(descriptor: AgentDescriptor, file_path: str) -> None:
    """
    Save an AgentDescriptor object to a JSON file.

    Args:
        descriptor: An AgentDescriptor object
        file_path: Path to save the JSON file

    Raises:
        OSError: If the file cannot be written
    """
    descriptor_dict = descriptor_to_dict(descriptor)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(descriptor_dict, f, indent=2)
