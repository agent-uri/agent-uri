"""
Agent descriptor generator for server implementations.

Aligned with draft-narvaneni-agent-uri-03. Generated descriptors expose
``skills`` (not "capabilities"). Accepts Skill objects and emits the
spec-shaped JSON.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from ..exceptions import DescriptorError
from ..skill import Skill as RuntimeSkill
from .validator import validate_descriptor

logger = logging.getLogger(__name__)


class AgentDescriptorGenerator:
    """Generate agent.json descriptors from registered skills."""

    def __init__(
        self,
        name: str,
        version: str,
        description: str = "",
        provider: Optional[Dict[str, Any]] = None,
        documentation_url: Optional[str] = None,
        interaction_model: Optional[List[str]] = None,
        auth: Optional[Dict[str, Any]] = None,
        transport: Optional[Dict[str, Any]] = None,
        conformance_level: Optional[int] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None,
        server_url: Optional[str] = None,
    ):
        """Initialize the descriptor generator.

        Args:
            name: Agent identifier.
            version: Agent version (SemVer).
            description: Human-readable description.
            provider: ``{"organization": str, "url": str}``.
            documentation_url: Human-readable documentation URL.
            interaction_model: List of registered interaction-model IDs
                (e.g., ``["agent2agent", "mcp"]``).
            auth: Authentication descriptor object (schemes,
                authorizationServer, protectedResourceMetadata, jwksUri, jwks).
            transport: Transport object with keys such as ``endpoint``,
                ``https``, ``wss``, etc.
            conformance_level: Self-declared conformance level (0-3).
            environment: Deployment environment hint.
            status: "active" | "deprecated" | "experimental".
            server_url: Convenience — if set and ``transport`` is not
                provided, populates ``transport.https``.
        """
        self.name = name
        self.version = version
        self.description = description
        self.provider = provider or {}
        self.documentation_url = documentation_url
        self.interaction_model = list(interaction_model) if interaction_model else []
        self.auth = auth
        self.conformance_level = conformance_level
        self.environment = environment
        self.status = status
        self.server_url = server_url

        if transport:
            self.transport: Optional[Dict[str, Any]] = dict(transport)
        elif server_url:
            self.transport = {"endpoint": server_url, "https": server_url}
        else:
            self.transport = None

        self._skills: List[RuntimeSkill] = []
        self._descriptor: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Skill registration
    # ------------------------------------------------------------------

    def register_skill(self, skill: RuntimeSkill) -> None:
        """Register a Skill with the generator."""
        self._skills.append(skill)
        self._descriptor = None
        logger.debug("Registered skill '%s'", skill.metadata.id)

    def scan_object_for_skills(self, obj: Any) -> int:
        """Scan an object for skill-decorated methods; returns the count registered."""
        count = 0
        for attr_name in dir(obj):
            if attr_name.startswith("_"):
                continue
            attr = getattr(obj, attr_name)
            maybe = getattr(attr, "_skill", None)
            if isinstance(maybe, RuntimeSkill):
                self.register_skill(maybe)
                count += 1
        return count

    def scan_module_for_skills(self, module: Any) -> int:
        """Scan a module for skill-decorated functions; returns the count registered."""
        count = 0
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue
            attr = getattr(module, attr_name)
            maybe = getattr(attr, "_skill", None)
            if isinstance(maybe, RuntimeSkill):
                self.register_skill(maybe)
                count += 1
        return count

    # ------------------------------------------------------------------
    # Descriptor emission
    # ------------------------------------------------------------------

    def generate_descriptor(self) -> Dict[str, Any]:
        """Produce the JSON-compatible descriptor dict."""
        if self._descriptor:
            return self._descriptor

        descriptor: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
        }
        if self.description:
            descriptor["description"] = self.description
        if self.server_url:
            descriptor["url"] = self.server_url
        if self.status:
            descriptor["status"] = self.status
        if self.conformance_level is not None:
            descriptor["conformanceLevel"] = self.conformance_level
        if self.environment:
            descriptor["environment"] = self.environment
        if self.provider:
            descriptor["provider"] = self.provider
        if self.documentation_url:
            descriptor["documentationUrl"] = self.documentation_url
        if self.transport:
            descriptor["transport"] = self.transport
        if self.interaction_model:
            descriptor["interactionModel"] = list(self.interaction_model)
        if self.auth:
            descriptor["authentication"] = self.auth

        descriptor["skills"] = [
            skill.metadata.to_dict() for skill in self._skills if skill.metadata.public
        ]

        self._descriptor = descriptor
        return descriptor

    def validate(self) -> bool:
        """Validate the generated descriptor against the normative schema.

        Raises:
            DescriptorError: If validation fails.
        """
        try:
            descriptor = self.generate_descriptor()
            result = validate_descriptor(descriptor)
            if not result.valid:
                msg = "; ".join(f"{e.path}: {e.message}" for e in result.errors)
                raise DescriptorError(f"Descriptor validation failed: {msg}")
            return True
        except DescriptorError:
            raise
        except Exception as e:
            raise DescriptorError(f"Descriptor validation failed: {e}")

    def to_json(self, indent: int = 2) -> str:
        """Serialize the descriptor to a JSON string."""
        return json.dumps(self.generate_descriptor(), indent=indent)

    def save(self, path: str, indent: int = 2) -> None:
        """Save the descriptor to a file.

        Raises:
            DescriptorError: If the file cannot be written.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.to_json(indent=indent))
            logger.info("Saved agent descriptor to %s", path)
        except Exception as e:
            raise DescriptorError(f"Failed to save descriptor: {e}")
