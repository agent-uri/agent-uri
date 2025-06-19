"""
Agent descriptor generator for server implementations.

This module provides utilities for generating agent.json descriptors.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from ..capability import Capability
from ..exceptions import DescriptorError
from .validator import validate_descriptor

logger = logging.getLogger(__name__)


class AgentDescriptorGenerator:
    """
    Generator for agent.json descriptors.

    This class provides utilities for creating and validating agent descriptors
    from capability registrations.
    """

    def __init__(
        self,
        name: str,
        version: str,
        description: str = "",
        provider: Optional[Dict[str, Any]] = None,
        documentation_url: Optional[str] = None,
        interaction_model: Optional[str] = None,
        auth_schemes: Optional[List[str]] = None,
        skills: Optional[List[Dict[str, str]]] = None,
        server_url: Optional[str] = None,
    ):
        """
        Initialize the descriptor generator.

        Args:
            name: The agent name
            version: The agent version (semver)
            description: A human-readable description
            provider: Optional provider information
            documentation_url: Optional documentation URL
            interaction_model: Optional interaction model
            auth_schemes: Optional list of authentication schemes
            skills: Optional list of agent skills
            server_url: Optional server URL for generating endpoints
        """
        self.name = name
        self.version = version
        self.description = description
        self.provider = provider or {}
        self.documentation_url = documentation_url
        self.interaction_model = interaction_model
        self.auth_schemes = auth_schemes or []
        self.skills = skills or []
        self.server_url = server_url

        # Store registered capabilities
        self._capabilities: List[Capability] = []

        # Cached descriptor
        self._descriptor: Optional[Dict[str, Any]] = None

    def register_capability(self, capability: Capability) -> None:
        """
        Register a capability with the generator.

        Args:
            capability: The capability to register
        """
        self._capabilities.append(capability)
        # Invalidate cached descriptor
        self._descriptor = None
        logger.debug(f"Registered capability '{capability.metadata.name}'")

    def scan_object_for_capabilities(self, obj: Any) -> int:
        """
        Scan an object for capability-decorated methods.

        Args:
            obj: The object to scan

        Returns:
            Number of capabilities registered
        """
        count = 0

        # Find all methods with _capability attribute
        for attr_name in dir(obj):
            if attr_name.startswith("_"):
                continue

            attr = getattr(obj, attr_name)
            if hasattr(attr, "_capability") and isinstance(
                attr._capability, Capability
            ):
                self.register_capability(attr._capability)
                count += 1

        return count

    def scan_module_for_capabilities(self, module) -> int:
        """
        Scan a module for capability-decorated functions.

        Args:
            module: The module to scan

        Returns:
            Number of capabilities registered
        """
        count = 0

        # Find all functions with _capability attribute
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue

            attr = getattr(module, attr_name)
            if hasattr(attr, "_capability") and isinstance(
                attr._capability, Capability
            ):
                self.register_capability(attr._capability)
                count += 1

        return count

    def generate_descriptor(self) -> Dict[str, Any]:
        """
        Generate an agent descriptor from registered capabilities.

        Returns:
            The generated agent descriptor as a dictionary
        """
        # Return cached descriptor if available
        if self._descriptor:
            return self._descriptor

        # Base descriptor
        descriptor: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }

        # Add URL if available
        if self.server_url:
            descriptor["url"] = self.server_url

        # Add provider if available
        if self.provider:
            descriptor["provider"] = self.provider

        # Add documentation URL if available
        if self.documentation_url:
            descriptor["documentationUrl"] = self.documentation_url

        # Add interaction model if available
        if self.interaction_model:
            descriptor["interactionModel"] = self.interaction_model

        # Add capabilities
        capabilities = []
        for capability in self._capabilities:
            # Only include public capabilities
            if capability.metadata.public:
                capabilities.append(capability.metadata.to_dict())

        descriptor["capabilities"] = capabilities

        # Add authentication schemes if available
        if self.auth_schemes:
            descriptor["authentication"] = {"schemes": self.auth_schemes}

        # Add skills if available
        if self.skills:
            descriptor["skills"] = self.skills

        # Cache the descriptor
        self._descriptor = descriptor

        return descriptor

    def validate(self) -> bool:
        """
        Validate the generated descriptor against the schema.

        Returns:
            True if valid, False otherwise

        Raises:
            DescriptorError: If validation fails
        """
        try:
            descriptor = self.generate_descriptor()

            # If agent-descriptor package is available, use schema validation
            if callable(validate_descriptor):
                validate_descriptor(descriptor)

            return True
        except Exception as e:
            raise DescriptorError(f"Descriptor validation failed: {str(e)}")

    def to_json(self, indent: int = 2) -> str:
        """
        Convert the descriptor to JSON.

        Args:
            indent: JSON indentation level

        Returns:
            The JSON string
        """
        descriptor = self.generate_descriptor()
        return json.dumps(descriptor, indent=indent)

    def save(self, path: str, indent: int = 2) -> None:
        """
        Save the descriptor to a file.

        Args:
            path: The file path
            indent: JSON indentation level

        Raises:
            DescriptorError: If the file cannot be saved
        """
        try:
            # Make directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

            # Generate and save the descriptor
            with open(path, "w") as f:
                f.write(self.to_json(indent=indent))

            logger.info(f"Saved agent descriptor to {path}")
        except Exception as e:
            raise DescriptorError(f"Failed to save descriptor: {str(e)}")
