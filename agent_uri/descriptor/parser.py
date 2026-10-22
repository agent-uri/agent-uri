"""
Parser and serializer for agent.json descriptors.

Aligned with draft-narvaneni-agent-uri-03. Descriptors use ``skills``
(not "capabilities"). Authentication references OAuth metadata docs
rather than embedded fields.
"""

import json
import os
import re
import urllib.request
from dataclasses import asdict
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from .models import (
    AgentDescriptor,
    Authentication,
    Contact,
    ContentTypes,
    Dependency,
    Example,
    Provider,
    Skill,
    Transport,
)

# ---------------------------------------------------------------------------
# Case conversion helpers
# ---------------------------------------------------------------------------

_CAMEL_STEP_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_STEP_2 = re.compile(r"([a-z0-9])([A-Z])")


def _snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    s1 = _CAMEL_STEP_1.sub(r"\1_\2", name)
    return _CAMEL_STEP_2.sub(r"\1_\2", s1).lower()


def _convert_keys_to_camel(obj: Any) -> Any:
    """Recursively convert dict keys from snake_case to camelCase (for JSON output)."""
    if isinstance(obj, dict):
        return {_snake_to_camel(k): _convert_keys_to_camel(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_keys_to_camel(item) for item in obj]
    return obj


def _convert_keys_to_snake(obj: Any) -> Any:
    """Recursively convert dict keys from camelCase to snake_case (for internal model).

    ``@context`` is preserved as-is (JSON-LD convention). Inner values inside
    ``input`` / ``output`` / ``jwks`` objects are left untouched because they
    are user-provided JSON Schema fragments or JWK sets, not this spec's
    fields.
    """
    if not isinstance(obj, dict):
        return obj
    result: Dict[str, Any] = {}
    for key, value in obj.items():
        if key == "@context":
            result[key] = value
            continue
        snake_key = _camel_to_snake(key)
        # Fields whose values are user-provided and must not be rekeyed.
        if snake_key in {"input", "output", "jwks"}:
            result[snake_key] = value
        elif isinstance(value, dict):
            result[snake_key] = _convert_keys_to_snake(value)
        elif isinstance(value, list):
            result[snake_key] = [
                _convert_keys_to_snake(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[snake_key] = value
    return result


# ---------------------------------------------------------------------------
# Nested-object parsers
# ---------------------------------------------------------------------------


def _parse_provider(data: Optional[Dict[str, Any]]) -> Optional[Provider]:
    if not data:
        return None
    return Provider(organization=data.get("organization", ""), url=data.get("url"))


def _parse_content_types(data: Optional[Dict[str, Any]]) -> Optional[ContentTypes]:
    if not data:
        return None
    return ContentTypes(
        accepts=data.get("accepts", []),
        produces=data.get("produces", []),
    )


def _parse_examples(examples_data: Optional[list]) -> list:
    if not examples_data:
        return []
    return [
        Example(
            input=item.get("input", {}),
            output=item.get("output", {}),
            description=item.get("description"),
        )
        for item in examples_data
    ]


def _parse_dependencies(depends_data: Optional[list]) -> list:
    """Parse the ``depends`` array on a skill.

    Each entry should be an object ``{uri, relation?, versionConstraint?}``.
    For backwards-compat with older input, a bare string URI is also accepted
    and treated as ``{uri: <str>}``.
    """
    if not depends_data:
        return []
    result: list = []
    for item in depends_data:
        if isinstance(item, str):
            result.append(Dependency(uri=item))
        elif isinstance(item, dict):
            result.append(
                Dependency(
                    uri=item.get("uri", ""),
                    relation=item.get("relation"),
                    version_constraint=item.get("version_constraint"),
                )
            )
    return result


def _parse_authentication(data: Optional[Dict[str, Any]]) -> Optional[Authentication]:
    if not data:
        return None
    return Authentication(
        schemes=data.get("schemes", []),
        authorization_server=data.get("authorization_server"),
        protected_resource_metadata=data.get("protected_resource_metadata"),
        jwks_uri=data.get("jwks_uri"),
        jwks=data.get("jwks"),
    )


def _parse_skills(skills_data: Optional[list]) -> list:
    if not skills_data:
        return []
    skills: list = []
    for item in skills_data:
        content_types = _parse_content_types(item.get("content_types"))
        auth = _parse_authentication(item.get("authentication"))
        examples = _parse_examples(item.get("examples"))
        depends = _parse_dependencies(item.get("depends"))
        # Spec requires id, name, description.
        if "id" not in item or "name" not in item or "description" not in item:
            raise ValueError("Each skill must have id, name, and description")
        skills.append(
            Skill(
                id=item["id"],
                name=item["name"],
                description=item["description"],
                version=item.get("version"),
                tags=item.get("tags", []),
                input=item.get("input"),
                output=item.get("output"),
                content_types=content_types,
                streaming=item.get("streaming"),
                streaming_format=item.get("streaming_format"),
                idempotent=item.get("idempotent"),
                status=item.get("status"),
                authentication=auth,
                depends=depends,
                examples=examples,
            )
        )
    return skills


def _parse_transport(data: Optional[Dict[str, Any]]) -> Optional[Transport]:
    if not data:
        return None
    return Transport(
        endpoint=data.get("endpoint"),
        https=data.get("https"),
        wss=data.get("wss"),
        grpc=data.get("grpc"),
        mqtt=data.get("mqtt"),
        local=data.get("local"),
        unix=data.get("unix"),
    )


def _parse_contact(data: Optional[Dict[str, Any]]) -> Optional[Contact]:
    if not data:
        return None
    return Contact(name=data.get("name"), email=data.get("email"), url=data.get("url"))


def _normalize_interaction_model(value: Any) -> list:
    """Accept either a string (legacy) or a list (spec-03)."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


# ---------------------------------------------------------------------------
# Top-level parse / serialize
# ---------------------------------------------------------------------------


def parse_descriptor(descriptor_data: Dict[str, Any]) -> AgentDescriptor:
    """Parse an agent descriptor dict into an AgentDescriptor.

    Raises:
        ValueError: If the descriptor is missing required fields or has an
            invalid structure.
    """
    data = _convert_keys_to_snake(descriptor_data)

    if "name" not in data:
        raise ValueError("Descriptor missing required field: name")
    if "version" not in data:
        raise ValueError("Descriptor missing required field: version")
    if "skills" not in data:
        raise ValueError("Descriptor missing required field: skills")

    skills = _parse_skills(data.get("skills", []))
    if not skills:
        raise ValueError("Descriptor must declare at least one skill")

    return AgentDescriptor(
        name=data["name"],
        version=data["version"],
        skills=skills,
        description=data.get("description"),
        url=data.get("url"),
        status=data.get("status"),
        conformance_level=data.get("conformance_level"),
        environment=data.get("environment"),
        provider=_parse_provider(data.get("provider")),
        documentation_url=data.get("documentation_url"),
        transport=_parse_transport(data.get("transport")),
        authentication=_parse_authentication(data.get("authentication")),
        interaction_model=_normalize_interaction_model(data.get("interaction_model")),
        supported_versions=data.get("supported_versions", {}),
        terms_of_service=data.get("terms_of_service"),
        privacy=data.get("privacy"),
        contact=_parse_contact(data.get("contact")),
        context=data.get("@context"),
    )


def load_descriptor(source: Union[str, Dict[str, Any]]) -> AgentDescriptor:
    """Load an agent descriptor from a file path, URL, or dict.

    Raises:
        ValueError: If the source type is invalid.
        FileNotFoundError: If the source file does not exist.
        urllib.error.URLError: If the URL cannot be accessed.
    """
    if isinstance(source, dict):
        return parse_descriptor(source)

    if not isinstance(source, str):
        raise ValueError(f"Invalid source type: {type(source)}")

    parsed_url = urlparse(source)
    if parsed_url.scheme in ("http", "https"):
        with urllib.request.urlopen(source) as response:  # nosec B310
            descriptor_data = json.loads(response.read())
            return parse_descriptor(descriptor_data)

    if not os.path.isfile(source):
        raise FileNotFoundError(f"File not found: {source}")

    with open(source, "r", encoding="utf-8") as f:
        return parse_descriptor(json.load(f))


def descriptor_to_dict(descriptor: AgentDescriptor) -> Dict[str, Any]:
    """Serialize an AgentDescriptor to a JSON-compatible dict.

    Produces a dict with camelCase keys and None-values stripped, suitable
    for writing out as ``agent.json``.
    """
    descriptor_dict = asdict(descriptor)
    descriptor_dict = _strip_nones(descriptor_dict)
    # @context preserved literally
    if "context" in descriptor_dict:
        descriptor_dict["@context"] = descriptor_dict.pop("context")
    return _convert_keys_to_camel(descriptor_dict)


def _strip_nones(obj: Any) -> Any:
    """Recursively strip None values from dicts; preserve empty lists/dicts."""
    if isinstance(obj, dict):
        return {k: _strip_nones(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_nones(item) for item in obj]
    return obj


def save_descriptor(descriptor: AgentDescriptor, file_path: str) -> None:
    """Serialize an AgentDescriptor to a JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(descriptor_to_dict(descriptor), f, indent=2)
