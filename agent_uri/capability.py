"""
Capability definition and registration for agent servers.

This module provides utilities for defining and registering agent
capabilities, including decorators for easy capability creation.
"""

import asyncio
import inspect
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Type, cast

from pydantic import BaseModel, ValidationError, create_model

from .exceptions import CapabilityError, InvalidInputError

logger = logging.getLogger(__name__)


class CapabilityMetadata:
    """Metadata for an agent capability."""

    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
        tags: Optional[List[str]] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        is_deterministic: bool = False,
        expected_output_variability: str = "medium",
        requires_context: bool = False,
        memory_enabled: bool = False,
        response_latency: str = "medium",
        confidence_estimation: bool = False,
        content_types: Optional[Dict[str, List[str]]] = None,
        interaction_model: Optional[str] = None,
        streaming: bool = False,
        auth_required: bool = False,
        public: bool = True,
    ):
        """
        Initialize capability metadata.

        Args:
            name: The name of the capability
            description: A human-readable description
            version: The capability version (semver)
            tags: Optional tags for categorization
            input_schema: JSON Schema for input validation
            output_schema: JSON Schema for output validation
            is_deterministic: Whether the capability produces deterministic outputs
            expected_output_variability: Level of expected output variation
            requires_context: Whether the capability needs session context
            memory_enabled: Whether the capability has memory across invocations
            response_latency: Expected response time (low/medium/high)
            confidence_estimation: Whether confidence scores are provided
            content_types: Supported content types for input/output
            interaction_model: Optional interaction model (e.g., agent2agent)
            streaming: Whether this capability supports streaming
            auth_required: Whether authentication is required
            public: Whether this capability is publicly advertised
        """
        self.name = name
        self.description = description
        self.version = version
        self.tags = tags or []
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.is_deterministic = is_deterministic
        self.expected_output_variability = expected_output_variability
        self.requires_context = requires_context
        self.memory_enabled = memory_enabled
        self.response_latency = response_latency
        self.confidence_estimation = confidence_estimation
        self.content_types = content_types or {
            "inputFormat": ["application/json"],
            "outputFormat": ["application/json"],
        }
        self.interaction_model = interaction_model
        self.streaming = streaming
        self.auth_required = auth_required
        self.public = public

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the metadata to a dictionary for inclusion in agent.json.

        Returns:
            A dictionary representation of the metadata
        """
        result: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }

        if self.tags:
            result["tags"] = self.tags

        if self.input_schema:
            result["input"] = self.input_schema

        if self.output_schema:
            result["output"] = self.output_schema

        # Add behavioral metadata
        behavioral_metadata: Dict[str, Any] = {}

        if self.is_deterministic is not None:
            behavioral_metadata["isDeterministic"] = self.is_deterministic

        if self.expected_output_variability:
            behavioral_metadata["expectedOutputVariability"] = (
                self.expected_output_variability
            )

        if self.requires_context is not None:
            behavioral_metadata["requiresContext"] = self.requires_context

        if self.memory_enabled is not None:
            behavioral_metadata["memoryEnabled"] = self.memory_enabled

        if self.response_latency:
            behavioral_metadata["responseLatency"] = self.response_latency

        if self.confidence_estimation is not None:
            behavioral_metadata["confidenceEstimation"] = self.confidence_estimation

        if behavioral_metadata:
            result.update(behavioral_metadata)

        # Add content types
        if self.content_types:
            result["contentTypes"] = self.content_types

        # Add interaction model if specified
        if self.interaction_model:
            result["interactionModel"] = self.interaction_model

        # Add streaming support indicator
        if self.streaming:
            result["streaming"] = True

        # Add authentication requirement
        if self.auth_required:
            result["authRequired"] = True

        return result


class Capability:
    """
    Represents an agent capability.

    A capability is a function or method that can be invoked via the agent://
    protocol. It includes metadata for discovery and documentation.
    """

    def __init__(
        self, func: Callable, metadata: Optional[CapabilityMetadata] = None, **kwargs
    ):
        """
        Initialize a capability.

        Args:
            func: The function implementing the capability
            metadata: Optional explicit metadata for the capability
            **kwargs: Additional metadata parameters if not using explicit metadata
        """
        self.func = func

        # Use explicit metadata if provided, otherwise create from kwargs
        if metadata:
            self.metadata = metadata
        else:
            # Default to function name if name not provided
            name = kwargs.pop("name", func.__name__)
            # Use function docstring as description if not provided
            description = kwargs.pop("description", func.__doc__ or "")
            self.metadata = CapabilityMetadata(
                name=name, description=description, **kwargs
            )

        # Determine if function is async
        self.is_async = asyncio.iscoroutinefunction(func)

        # Create input validation model if schema provided
        self.input_model = (
            self._create_input_model() if self.metadata.input_schema else None
        )

        # Set up session tracking if memory is enabled
        self.sessions: Optional[Dict[str, Dict[str, Any]]] = (
            {} if self.metadata.memory_enabled else None
        )

    def _create_input_model(self) -> Optional[Type[BaseModel]]:
        """
        Create a pydantic model for input validation based on the input schema.

        Returns:
            A pydantic model class for validating inputs
        """
        try:
            # Check if schema exists
            if self.metadata.input_schema is None:
                return None

            # Create model name based on capability name
            model_name = f"{self.metadata.name.title().replace('-', '')}Input"

            # Get properties from schema
            properties = self.metadata.input_schema.get("properties", {})
            required = self.metadata.input_schema.get("required", [])

            # Create field definitions
            fields: Dict[str, Any] = {}
            for field_name, field_schema in properties.items():
                field_type = self._schema_type_to_python(
                    field_schema.get("type", "string")
                )
                is_required = field_name in required

                if is_required:
                    fields[field_name] = (field_type, ...)
                else:
                    default = field_schema.get("default", None)
                    fields[field_name] = (field_type, default)

            # Create the model dynamically
            return create_model(model_name, **fields)

        except Exception as e:
            logger.warning(f"Failed to create input model: {str(e)}")
            return None

    def _schema_type_to_python(self, schema_type: str) -> Type[Any]:
        """
        Convert JSON Schema type to Python type.

        Args:
            schema_type: JSON Schema type string

        Returns:
            Corresponding Python type
        """
        type_map: Dict[str, Type[Any]] = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        return type_map.get(schema_type, cast(Type[Any], Any))

    def validate_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input data against the schema.

        Args:
            data: Input data to validate

        Returns:
            Validated data

        Raises:
            InvalidInputError: If validation fails
        """
        if not self.input_model:
            return data

        try:
            validated = self.input_model(**data)
            return validated.dict()
        except ValidationError as e:
            raise InvalidInputError(f"Input validation failed: {str(e)}")
        except Exception as e:
            raise InvalidInputError(f"Input validation error: {str(e)}")

    async def invoke(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke the capability.

        Args:
            params: Parameters for the capability
            session_id: Optional session identifier for stateful capabilities
            context: Optional context data
            **kwargs: Additional invocation parameters

        Returns:
            The capability result

        Raises:
            CapabilityError: If the capability cannot be invoked
        """
        try:
            # Validate input parameters
            validated_params = self.validate_input(params)

            # Handle session context if memory is enabled
            if (
                self.metadata.memory_enabled
                and session_id
                and self.sessions is not None
            ):
                if session_id not in self.sessions:
                    self.sessions[session_id] = {"created_at": uuid.uuid4().hex}

                # Add session_id to params if function expects it
                sig = inspect.signature(self.func)
                if "session_id" in sig.parameters:
                    # Add a defensive check to detect possible parameter duplication
                    if "session_id" in kwargs:
                        logger.warning(
                            "session_id found in both kwargs and as explicit "
                            "parameter. This could cause parameter duplication "
                            "errors."
                        )
                        # Don't propagate the kwargs version to avoid duplication
                        kwargs.pop("session_id")

                    validated_params["session_id"] = session_id

                # Add session context if function expects it
                if "context" in sig.parameters:
                    session_context = (
                        self.sessions.get(session_id, {}) if self.sessions else {}
                    )
                    # Update with new context if provided
                    if context:
                        session_context.update(context)
                    validated_params["context"] = session_context

            # Invoke the function (async or sync)
            if self.is_async:
                result = await self.func(**validated_params, **kwargs)
            else:
                result = self.func(**validated_params, **kwargs)

            # Update session with response context if provided
            if (
                self.metadata.memory_enabled
                and session_id
                and isinstance(result, dict)
                and self.sessions is not None
            ):
                if "context" in result:
                    if session_id not in self.sessions:
                        self.sessions[session_id] = {}
                    if self.sessions is not None:
                        self.sessions[session_id].update(result.get("context", {}))

            return result

        except InvalidInputError:
            # Re-raise input validation errors
            raise
        except Exception as e:
            raise CapabilityError(f"Error invoking capability: {str(e)}")


def capability(
    name: Optional[str] = None,
    description: Optional[str] = None,
    version: str = "1.0.0",
    tags: Optional[List[str]] = None,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    is_deterministic: bool = False,
    expected_output_variability: str = "medium",
    requires_context: bool = False,
    memory_enabled: bool = False,
    response_latency: str = "medium",
    confidence_estimation: bool = False,
    content_types: Optional[Dict[str, List[str]]] = None,
    interaction_model: Optional[str] = None,
    streaming: bool = False,
    auth_required: bool = False,
    public: bool = True,
) -> Callable:
    """
    Decorator for creating agent capabilities.

    This decorator creates a Capability instance and attaches it to the
    decorated function for later discovery and registration.

    Args:
        name: The name of the capability (defaults to function name)
        description: A human-readable description (defaults to function docstring)
        version: The capability version (semver)
        tags: Optional tags for categorization
        input_schema: JSON Schema for input validation
        output_schema: JSON Schema for output validation
        is_deterministic: Whether the capability produces deterministic outputs
        expected_output_variability: Level of expected output variation
        requires_context: Whether the capability needs session context
        memory_enabled: Whether the capability has memory across invocations
        response_latency: Expected response time (low/medium/high)
        confidence_estimation: Whether confidence scores are provided
        content_types: Supported content types for input/output
        interaction_model: Optional interaction model (e.g., agent2agent)
        streaming: Whether this capability supports streaming
        auth_required: Whether authentication is required
        public: Whether this capability is publicly advertised

    Returns:
        A decorator function that attaches capability metadata to the function
    """

    def decorator(func):
        # Create capability metadata
        function_name = name or func.__name__

        # Create a default description for echo functions if none provided
        if not description and not func.__doc__ and "echo" in function_name.lower():
            default_description = "Echo back the input text."
        else:
            default_description = func.__doc__ or ""

        metadata = CapabilityMetadata(
            name=function_name,
            description=description or default_description,
            version=version,
            tags=tags,
            input_schema=input_schema,
            output_schema=output_schema,
            is_deterministic=is_deterministic,
            expected_output_variability=expected_output_variability,
            requires_context=requires_context,
            memory_enabled=memory_enabled,
            response_latency=response_latency,
            confidence_estimation=confidence_estimation,
            content_types=content_types,
            interaction_model=interaction_model,
            streaming=streaming,
            auth_required=auth_required,
            public=public,
        )

        # Create capability instance and attach to function
        cap = Capability(func, metadata=metadata)
        func._capability = cap

        # Return original function
        return func

    return decorator
