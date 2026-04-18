"""
Validator for agent.json descriptors.

Aligned with draft-narvaneni-agent-uri-03. The canonical JSON Schema
lives at ``docs/rfc/schemas/agent-descriptor.schema.json`` in this
repository; when present on disk, it is the source of truth. Otherwise
a minimal embedded schema is used.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Union

from .models import AgentDescriptor


@dataclass
class ValidationError:
    """Validation error information."""

    path: str
    message: str
    severity: str = "error"  # "error", "warning", "info"


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    valid: bool
    errors: List[ValidationError] = field(default_factory=list)

    def add_error(self, path: str, message: str, severity: str = "error") -> None:
        self.errors.append(ValidationError(path, message, severity))
        if severity == "error":
            self.valid = False

    def __bool__(self) -> bool:
        return self.valid


def _get_schema() -> Dict[str, Any]:
    """Load the normative JSON Schema, falling back to a minimal embedded copy."""
    here = Path(__file__).resolve().parent
    candidates = [
        here
        / ".."
        / ".."
        / "docs"
        / "rfc"
        / "schemas"
        / "agent-descriptor.schema.json",
        Path("docs/rfc/schemas/agent-descriptor.schema.json"),
        Path("agent-descriptor.schema.json"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

    # Minimal embedded schema (kept in lockstep with the published schema).
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["name", "version", "skills"],
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "version": {"type": "string"},
            "skills": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["id", "name", "description"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            },
        },
        "additionalProperties": True,
    }


def validate_required_fields(descriptor_data: Dict[str, Any]) -> ValidationResult:
    """Validate that the descriptor contains all required fields per the spec."""
    result = ValidationResult(valid=True)

    # Top-level required fields
    for field_name in ("name", "version", "skills"):
        if field_name not in descriptor_data:
            result.add_error(field_name, f"Missing required field: {field_name}")

    skills = descriptor_data.get("skills")
    if skills is None:
        return result
    if not isinstance(skills, list):
        result.add_error("skills", "skills must be an array")
        return result
    if len(skills) == 0:
        result.add_error("skills", "At least one skill is required")
        return result

    for i, skill in enumerate(skills):
        if not isinstance(skill, dict):
            result.add_error(f"skills[{i}]", "skill must be an object")
            continue
        for field_name in ("id", "name", "description"):
            if field_name not in skill:
                result.add_error(
                    f"skills[{i}]", f"skill missing required field: {field_name}"
                )

    # Authentication shape check (optional field, but when present, schemes
    # must be a list)
    auth = descriptor_data.get("authentication")
    if isinstance(auth, dict):
        schemes = auth.get("schemes")
        if schemes is not None and not isinstance(schemes, list):
            result.add_error(
                "authentication.schemes", "authentication.schemes must be an array"
            )

    # Provider check
    provider = descriptor_data.get("provider")
    if isinstance(provider, dict) and "organization" not in provider:
        result.add_error("provider", "provider missing required field: organization")

    # conformanceLevel bounds (0-3)
    cl = descriptor_data.get(
        "conformanceLevel", descriptor_data.get("conformance_level")
    )
    if cl is not None:
        if not isinstance(cl, int) or not 0 <= cl <= 3:
            result.add_error(
                "conformanceLevel", "conformanceLevel must be an integer in [0, 3]"
            )

    # status enum
    status = descriptor_data.get("status")
    if status is not None and status not in ("active", "deprecated", "experimental"):
        result.add_error(
            "status", "status must be one of: active, deprecated, experimental"
        )

    return result


def _check_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "null":
        return value is None
    return False


def _validate_type(
    value: Any,
    expected_type: Union[str, List[str]],
    path: str,
    result: ValidationResult,
) -> None:
    types = expected_type if isinstance(expected_type, list) else [expected_type]
    if not any(_check_type(value, t) for t in types):
        result.add_error(
            path,
            f"Expected {expected_type}, got {type(value).__name__}",
        )


def _validate_against_schema(
    value: Any,
    schema: Dict[str, Any],
    path: str,
    result: ValidationResult,
) -> None:
    """Lightweight recursive validator. Handles a subset of JSON Schema."""
    if "type" in schema:
        _validate_type(value, schema["type"], path, result)
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_check_type(value, t) for t in types):
            return

    if isinstance(value, dict):
        for required_prop in schema.get("required", []):
            if required_prop not in value:
                result.add_error(
                    f"{path}.{required_prop}",
                    f"Missing required property: {required_prop}",
                )
        for prop_name, prop_schema in schema.get("properties", {}).items():
            if prop_name in value:
                _validate_against_schema(
                    value[prop_name],
                    prop_schema,
                    f"{path}.{prop_name}" if path else prop_name,
                    result,
                )

    elif isinstance(value, list):
        items_schema = schema.get("items")
        if items_schema:
            for i, item in enumerate(value):
                _validate_against_schema(item, items_schema, f"{path}[{i}]", result)
        if "minItems" in schema and len(value) < schema["minItems"]:
            result.add_error(
                path,
                f"Array length {len(value)} is less than minimum {schema['minItems']}",
            )

    if isinstance(value, str) and "enum" in schema and value not in schema["enum"]:
        result.add_error(path, f"Value {value!r} not in enum: {schema['enum']}")


def validate_descriptor(descriptor_data: Dict[str, Any]) -> ValidationResult:
    """Validate a descriptor dict against the normative schema."""
    result = validate_required_fields(descriptor_data)
    if not result:
        return result
    schema = _get_schema()
    _validate_against_schema(descriptor_data, schema, "", result)
    return result


def validate_agent_card_compatibility(
    descriptor_data: Dict[str, Any],
) -> ValidationResult:
    """Validate a descriptor is reasonably interoperable with AgentCard.

    Since ``skills`` is now aligned 1:1 with AgentCard ``skills``, this is
    mostly a sanity check that the required AgentCard fields are present.
    """
    result = ValidationResult(valid=True)

    # AgentCard requires these top-level fields. ``version`` and ``name`` are
    # required by this spec too; ``url`` and ``description`` are recommended.
    for field_name in ("name", "url", "version", "skills", "description"):
        if field_name not in descriptor_data:
            result.add_error(
                field_name,
                f"Missing field useful for AgentCard compatibility: {field_name}",
                "warning",
            )

    skills = descriptor_data.get("skills")
    if isinstance(skills, list):
        for i, skill in enumerate(skills):
            if not isinstance(skill, dict):
                continue
            for field_name in ("id", "name", "description"):
                if field_name not in skill:
                    result.add_error(
                        f"skills[{i}].{field_name}",
                        f"skill missing required field: {field_name}",
                        "warning",
                    )

    return result


def check_json_ld_extensions(descriptor_data: Dict[str, Any]) -> ValidationResult:
    """Informational: note whether JSON-LD extensions are in use."""
    result = ValidationResult(valid=True)
    if "@context" not in descriptor_data:
        result.add_error(
            "@context",
            "No JSON-LD @context present; extensions cannot be semantically resolved.",
            "info",
        )
    for prop in ("@id", "@type", "@graph"):
        if prop in descriptor_data:
            result.add_error(prop, f"Found JSON-LD property: {prop}", "info")
    return result


def validate_model(descriptor: AgentDescriptor) -> ValidationResult:
    """Validate an AgentDescriptor model instance."""
    result = ValidationResult(valid=True)
    if not descriptor.name:
        result.add_error("name", "Missing required field: name")
    if not descriptor.version:
        result.add_error("version", "Missing required field: version")
    if not descriptor.skills:
        result.add_error("skills", "At least one skill is required")
    for i, skill in enumerate(descriptor.skills):
        if not skill.id:
            result.add_error(f"skills[{i}].id", "skill missing id")
        if not skill.name:
            result.add_error(f"skills[{i}].name", "skill missing name")
        if not skill.description:
            result.add_error(f"skills[{i}].description", "skill missing description")
    if (
        descriptor.conformance_level is not None
        and not 0 <= descriptor.conformance_level <= 3
    ):
        result.add_error("conformance_level", "conformance_level must be in [0, 3]")
    return result
