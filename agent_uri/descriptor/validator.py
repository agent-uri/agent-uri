"""
Validator for agent.json descriptors.

This module provides functions to validate agent.json descriptors
against schema requirements and check for required fields.
"""

import json
import os
from dataclasses import dataclass, field
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
        """Add an error to the validation result."""
        self.errors.append(ValidationError(path, message, severity))
        if severity == "error":
            self.valid = False

    def __bool__(self) -> bool:
        return self.valid


def _get_schema() -> Dict[str, Any]:
    """
    Load the agent descriptor schema.

    This will first check for a local agent-descriptor-schema.json file,
    then fall back to the embedded schema.
    """
    # Try to load from a local file first
    schema_paths = [
        "agent-descriptor-schema.json",
        "docs/spec/agent-descriptor-schema.json",
        "../docs/spec/agent-descriptor-schema.json",
        "../../docs/spec/agent-descriptor-schema.json",
    ]

    for path in schema_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

    # If local file isn't available, use this embedded minimal schema
    # that includes just the required fields
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Agent Descriptor Schema",
        "description": "JSON Schema for the agent.json descriptor format",
        "type": "object",
        "required": ["name", "version", "capabilities"],
        "properties": {
            "name": {
                "type": "string",
                "description": "Unique name of the agent",
            },
            "version": {
                "type": ["string", "number"],
                "description": "Semantic version of the agent",
            },
            "capabilities": {
                "type": "array",
                "description": ("List of capabilities this agent provides"),
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": ("Unique identifier for this capability"),
                        }
                    },
                },
            },
        },
    }


def validate_required_fields(descriptor_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate that the descriptor contains all required fields.

    Args:
        descriptor_data: A dictionary containing the descriptor data

    Returns:
        A ValidationResult object
    """
    result = ValidationResult(valid=True)

    # Check for required top-level fields
    required_fields = ["name", "version", "capabilities"]
    for field_name in required_fields:
        if field_name not in descriptor_data:
            result.add_error(field_name, f"Missing required field: {field_name}")

    # If no capabilities, no need to check further
    if "capabilities" not in descriptor_data:
        return result

    # Check capabilities
    capabilities = descriptor_data["capabilities"]
    if not isinstance(capabilities, list):
        result.add_error("capabilities", "Capabilities must be an array")
        return result

    if len(capabilities) == 0:
        result.add_error("capabilities", "At least one capability is required")

    # Check each capability for required fields
    for i, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            result.add_error(f"capabilities[{i}]", "Capability must be an object")
            continue

        if "name" not in capability:
            result.add_error(
                f"capabilities[{i}]", "Capability missing required field: name"
            )

    # Check if skills contain required fields
    if "skills" in descriptor_data and isinstance(descriptor_data["skills"], list):
        skills = descriptor_data["skills"]
        for i, skill in enumerate(skills):
            if not isinstance(skill, dict):
                result.add_error(f"skills[{i}]", "Skill must be an object")
                continue

            # Check required fields for each skill
            for field_name in ["id", "name"]:
                if field_name not in skill:
                    result.add_error(
                        f"skills[{i}]", f"Skill missing required field: {field_name}"
                    )

    # Check if authentication contains required fields
    if "authentication" in descriptor_data and isinstance(
        descriptor_data["authentication"], dict
    ):
        auth = descriptor_data["authentication"]
        if "schemes" not in auth:
            result.add_error(
                "authentication", "Authentication missing required field: schemes"
            )
        elif not isinstance(auth["schemes"], list):
            result.add_error(
                "authentication.schemes", "Authentication schemes must be an array"
            )

    # Check provider if present
    if "provider" in descriptor_data and isinstance(descriptor_data["provider"], dict):
        provider = descriptor_data["provider"]
        if "organization" not in provider:
            result.add_error(
                "provider", "Provider missing required field: organization"
            )

    return result


def _validate_type(
    value: Any,
    expected_type: Union[str, List[str]],
    path: str,
    result: ValidationResult,
) -> None:
    """
    Validate that a value has the expected type.

    Args:
        value: The value to validate
        expected_type: The expected type or types
        path: The path to the value in the descriptor
        result: The ValidationResult to update
    """
    if isinstance(expected_type, list):
        # If expected_type is a list, check if value matches any of the types
        valid = False
        for t in expected_type:
            if _check_type(value, t):
                valid = True
                break

        if not valid:
            result.add_error(
                path, f"Expected one of {expected_type}, got {type(value).__name__}"
            )
    else:
        # Otherwise, check if value matches the specific type
        if not _check_type(value, expected_type):
            result.add_error(
                path, f"Expected {expected_type}, got {type(value).__name__}"
            )


def _check_type(value: Any, expected_type: str) -> bool:
    """
    Check if a value has the expected type.

    Args:
        value: The value to check
        expected_type: The expected type name

    Returns:
        True if the value has the expected type, False otherwise
    """
    if expected_type == "string":
        return isinstance(value, str)
    elif expected_type == "number":
        return isinstance(value, (int, float))
    elif expected_type == "integer":
        return isinstance(value, int)
    elif expected_type == "boolean":
        return isinstance(value, bool)
    elif expected_type == "array":
        return isinstance(value, list)
    elif expected_type == "object":
        return isinstance(value, dict)
    elif expected_type == "null":
        return value is None
    else:
        return False


def _validate_against_schema(
    value: Any, schema: Dict[str, Any], path: str, result: ValidationResult
) -> None:
    """
    Recursively validate a value against a JSON schema.

    Args:
        value: The value to validate
        schema: The JSON schema to validate against
        path: The path to the value in the descriptor
        result: The ValidationResult to update
    """
    # Check type
    if "type" in schema:
        _validate_type(value, schema["type"], path, result)

    # If the value doesn't match the expected type, don't validate further
    if "type" in schema:
        expected_types = (
            schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        )
        valid_type = False
        for expected_type in expected_types:
            if _check_type(value, expected_type):
                valid_type = True
                break

        if not valid_type:
            return

    # Validate based on the value type
    if isinstance(value, dict):
        # Check required properties
        if "required" in schema:
            for required_prop in schema["required"]:
                if required_prop not in value:
                    result.add_error(
                        f"{path}.{required_prop}",
                        f"Missing required property: {required_prop}",
                    )

        # Validate properties
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                if prop_name in value:
                    _validate_against_schema(
                        value[prop_name],
                        prop_schema,
                        f"{path}.{prop_name}",
                        result,
                    )

        # Check for additional properties
        if "additionalProperties" in schema and not schema.get("additionalProperties"):
            for prop_name in value:
                if "properties" not in schema or prop_name not in schema["properties"]:
                    result.add_error(
                        f"{path}.{prop_name}",
                        f"Additional property not allowed: {prop_name}",
                    )

    elif isinstance(value, list):
        # Check items schema
        if "items" in schema:
            items_schema = schema["items"]
            for i, item in enumerate(value):
                _validate_against_schema(item, items_schema, f"{path}[{i}]", result)

        # Check minItems
        if "minItems" in schema and len(value) < schema["minItems"]:
            result.add_error(
                path,
                f"Array length {len(value)} is less than minimum "
                f"{schema['minItems']}",
            )

        # Check maxItems
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            result.add_error(
                path,
                f"Array length {len(value)} is greater than maximum "
                f"{schema['maxItems']}",
            )

    # Validate string format if specified
    if isinstance(value, str) and "format" in schema:
        format_name = schema["format"]
        if format_name == "uri":
            import re

            uri_pattern = re.compile(r"^(https?|ftp)://[^\s/$.?#].[^\s]*$")
            if not uri_pattern.match(value):
                result.add_error(path, f"Invalid URI format: {value}")

        elif format_name == "email":
            import re

            email_pattern = re.compile(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )
            if not email_pattern.match(value):
                result.add_error(path, f"Invalid email format: {value}")

    # Validate enum values
    if "enum" in schema and value not in schema["enum"]:
        result.add_error(path, f"Value {value} not in enum: {schema['enum']}")


def validate_descriptor(descriptor_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate an agent descriptor against the schema.

    Args:
        descriptor_data: A dictionary containing the descriptor data

    Returns:
        A ValidationResult object
    """
    # First, check required fields
    result = validate_required_fields(descriptor_data)
    if not result:
        return result

    # Then validate against the JSON schema
    schema = _get_schema()
    _validate_against_schema(descriptor_data, schema, "", result)

    return result


def validate_agent_card_compatibility(
    descriptor_data: Dict[str, Any],
) -> ValidationResult:
    """
    Validate an agent descriptor for compatibility with the Agent2Agent
    protocol's AgentCard.

    Args:
        descriptor_data: A dictionary containing the descriptor data

    Returns:
        A ValidationResult object with warnings for compatibility issues
    """
    result = ValidationResult(valid=True)

    # Required fields for AgentCard
    required_fields = ["name", "url", "version", "capabilities", "skills"]
    for field_name in required_fields:
        if field_name not in descriptor_data:
            result.add_error(
                field_name,
                f"Missing field required for AgentCard compatibility: {field_name}",
                "warning",
            )

    # Check capabilities field
    if "capabilities" in descriptor_data:
        if not isinstance(descriptor_data["capabilities"], list):
            result.add_error(
                "capabilities",
                "For AgentCard compatibility, capabilities must be an array",
                "warning",
            )
        elif len(descriptor_data["capabilities"]) == 0:
            result.add_error(
                "capabilities",
                "For AgentCard compatibility, at least one capability " "is required",
                "warning",
            )

    # Check skills field
    if "skills" in descriptor_data:
        if not isinstance(descriptor_data["skills"], list):
            result.add_error(
                "skills",
                "For AgentCard compatibility, skills must be an array",
                "warning",
            )
        else:
            for i, skill in enumerate(descriptor_data["skills"]):
                if not isinstance(skill, dict):
                    result.add_error(
                        f"skills[{i}]",
                        "For AgentCard compatibility, each skill must be " "an object",
                        "warning",
                    )
                    continue

                # Check required fields for each skill
                for field_name in ["id", "name"]:
                    if field_name not in skill:
                        result.add_error(
                            f"skills[{i}]",
                            f"For AgentCard compatibility, skill missing "
                            f"required field: {field_name}",
                            "warning",
                        )

    # Check if the descriptor has capabilities field with the required
    # structure
    if "capabilities" in descriptor_data and isinstance(
        descriptor_data["capabilities"], dict
    ):
        capabilities = descriptor_data["capabilities"]

        # For AgentCard, these are boolean fields
        for capability in [
            "streaming",
            "pushNotifications",
            "stateTransitionHistory",
        ]:
            if capability in capabilities and not isinstance(
                capabilities[capability], bool
            ):
                result.add_error(
                    f"capabilities.{capability}",
                    f"For AgentCard compatibility, {capability} must be " "a boolean",
                    "warning",
                )

    return result


def check_json_ld_extensions(descriptor_data: Dict[str, Any]) -> ValidationResult:
    """
    Check for JSON-LD extensions in an agent descriptor.

    Args:
        descriptor_data: A dictionary containing the descriptor data

    Returns:
        A ValidationResult object with info for JSON-LD features
    """
    result = ValidationResult(valid=True)

    # Check for @context
    if "@context" not in descriptor_data:
        result.add_error(
            "@context",
            "Missing JSON-LD context for semantic interoperability",
            "info",
        )

    # Check for JSON-LD specific properties
    json_ld_properties = ["@id", "@type", "@graph"]
    for prop in json_ld_properties:
        if prop in descriptor_data:
            # This is just informational
            result.add_error(prop, f"Found JSON-LD property: {prop}", "info")

    return result


def validate_model(descriptor: AgentDescriptor) -> ValidationResult:
    """
    Validate an AgentDescriptor model instance.

    Args:
        descriptor: An AgentDescriptor object

    Returns:
        A ValidationResult object
    """
    result = ValidationResult(valid=True)

    # Check basic required fields
    if not descriptor.name:
        result.add_error("name", "Missing required field: name")

    if not descriptor.version:
        result.add_error("version", "Missing required field: version")

    # Check capabilities
    if not descriptor.capabilities:
        result.add_error("capabilities", "Missing required field: capabilities")
    elif len(descriptor.capabilities) == 0:
        result.add_error("capabilities", "At least one capability is required")

    return result
