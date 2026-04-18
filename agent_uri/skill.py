"""
Skill definition and registration for agent servers.

Aligned with draft-narvaneni-agent-uri-03. A Skill is the runtime
counterpart to the ``skills[]`` array in an agent descriptor. Provides
the ``@skill`` decorator and the ``SkillMetadata`` / ``Skill`` types.
"""

import asyncio
import inspect
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Type, cast

from pydantic import BaseModel, ValidationError, create_model

from .exceptions import InvalidInputError, SkillError

logger = logging.getLogger(__name__)


class SkillMetadata:
    """Metadata for an agent skill.

    Field names match the spec's ``skills[]`` object: ``id``, ``name``,
    ``description`` are required; the rest are optional. Application-level
    behavioral metadata (determinism, variability, latency quartiles,
    pricing, model info) is out of scope for this spec — carry those under
    a vendor ``x-`` namespace via ``extensions``.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        version: Optional[str] = None,
        tags: Optional[List[str]] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        content_types: Optional[Dict[str, List[str]]] = None,
        streaming: bool = False,
        streaming_format: Optional[str] = None,
        idempotent: Optional[bool] = None,
        status: Optional[str] = None,
        authentication: Optional[Dict[str, Any]] = None,
        depends: Optional[List[Dict[str, Any]]] = None,
        auth_required: bool = False,
        public: bool = True,
        extensions: Optional[Dict[str, Any]] = None,
        memory_enabled: bool = False,
    ):
        """Initialize skill metadata.

        Args:
            id: Skill identifier (required, spec-normative).
            name: Human-readable skill name (required, spec-normative).
            description: Human-readable description (required, spec-normative).
            version: Skill version, SemVer recommended.
            tags: Classification tags for discovery.
            input_schema: JSON Schema describing input.
            output_schema: JSON Schema describing output.
            content_types: ``{"accepts": [...], "produces": [...]}``.
            streaming: Whether the skill supports streaming responses.
            streaming_format: "sse", "ndjson", or "grpc-stream".
            idempotent: Whether the skill is safe to retry.
            status: "active" | "deprecated" | "experimental".
            authentication: Per-skill auth override (same shape as agent-level).
            depends: List of ``{uri, relation, versionConstraint}`` entries.
            auth_required: Runtime flag — whether an authenticated caller is required.
            public: Whether to advertise in the generated descriptor.
            extensions: Extra JSON fields (vendor-prefixed) to carry through.
            memory_enabled: Local server-side flag; does NOT appear in the descriptor.
                Controls whether the runtime keeps per-session state for this skill.
        """
        self.id = id
        self.name = name
        self.description = description
        self.version = version
        self.tags = tags or []
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.content_types = content_types
        self.streaming = streaming
        self.streaming_format = streaming_format
        self.idempotent = idempotent
        self.status = status
        self.authentication = authentication
        self.depends = depends or []
        self.auth_required = auth_required
        self.public = public
        self.extensions = extensions or {}
        self.memory_enabled = memory_enabled

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to the descriptor ``skills[]`` entry shape."""
        result: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }
        if self.version is not None:
            result["version"] = self.version
        if self.tags:
            result["tags"] = list(self.tags)
        if self.input_schema:
            result["input"] = self.input_schema
        if self.output_schema:
            result["output"] = self.output_schema
        if self.content_types:
            result["contentTypes"] = self.content_types
        if self.streaming:
            result["streaming"] = True
            if self.streaming_format:
                result["streamingFormat"] = self.streaming_format
        if self.idempotent is not None:
            result["idempotent"] = self.idempotent
        if self.status:
            result["status"] = self.status
        if self.authentication:
            result["authentication"] = self.authentication
        if self.depends:
            result["depends"] = self.depends
        # Extensions merged in last so they can't clobber normative keys.
        for key, value in self.extensions.items():
            if key not in result:
                result[key] = value
        return result


class Skill:
    """A runtime skill: a function invokable through the agent:// protocol.

    Wraps a callable with its metadata and provides input validation plus
    (optionally) per-session state.
    """

    def __init__(
        self,
        func: Callable,
        metadata: Optional[SkillMetadata] = None,
        **kwargs: Any,
    ) -> None:
        self.func = func
        if metadata:
            self.metadata = metadata
        else:
            skill_id = kwargs.pop("id", func.__name__)
            name = kwargs.pop("name", skill_id)
            description = kwargs.pop("description", func.__doc__ or "")
            self.metadata = SkillMetadata(
                id=skill_id, name=name, description=description, **kwargs
            )
        self.is_async = asyncio.iscoroutinefunction(func)
        self.input_model = (
            self._create_input_model() if self.metadata.input_schema else None
        )
        self.sessions: Optional[Dict[str, Dict[str, Any]]] = (
            {} if self.metadata.memory_enabled else None
        )

    # ------------------------------------------------------------------

    def _create_input_model(self) -> Optional[Type[BaseModel]]:
        try:
            if self.metadata.input_schema is None:
                return None
            model_name = f"{self.metadata.id.title().replace('-', '')}Input"
            properties = self.metadata.input_schema.get("properties", {})
            required = self.metadata.input_schema.get("required", [])
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
            return create_model(model_name, **fields)
        except Exception as e:
            logger.warning(
                "Failed to create input model for %s: %s", self.metadata.id, e
            )
            return None

    @staticmethod
    def _schema_type_to_python(schema_type: str) -> Type[Any]:
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
        if not self.input_model:
            return data
        try:
            validated = self.input_model(**data)
            # pydantic v2: model_dump(); v1 fallback: dict()
            dumper = getattr(validated, "model_dump", None) or validated.dict
            return dumper()
        except ValidationError as e:
            raise InvalidInputError(f"Input validation failed: {e}")
        except Exception as e:
            raise InvalidInputError(f"Input validation error: {e}")

    # ------------------------------------------------------------------

    async def invoke(
        self,
        params: Dict[str, Any],
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Invoke the skill.

        Raises:
            InvalidInputError: If input validation fails.
            SkillError: For any other runtime error.
        """
        try:
            validated_params = self.validate_input(params)

            if (
                self.metadata.memory_enabled
                and session_id
                and self.sessions is not None
            ):
                if session_id not in self.sessions:
                    self.sessions[session_id] = {"created_at": uuid.uuid4().hex}
                sig = inspect.signature(self.func)
                if "session_id" in sig.parameters:
                    kwargs.pop("session_id", None)
                    validated_params["session_id"] = session_id
                if "context" in sig.parameters:
                    session_context = dict(self.sessions.get(session_id, {}))
                    if context:
                        session_context.update(context)
                    validated_params["context"] = session_context

            if self.is_async:
                result = await self.func(**validated_params, **kwargs)
            else:
                result = self.func(**validated_params, **kwargs)

            if (
                self.metadata.memory_enabled
                and session_id
                and isinstance(result, dict)
                and self.sessions is not None
                and "context" in result
            ):
                self.sessions.setdefault(session_id, {}).update(
                    result.get("context", {})
                )

            return result

        except InvalidInputError:
            raise
        except Exception as e:
            raise SkillError(f"Error invoking skill: {e}", skill_id=self.metadata.id)


def skill(
    id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    version: Optional[str] = None,
    tags: Optional[List[str]] = None,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    content_types: Optional[Dict[str, List[str]]] = None,
    streaming: bool = False,
    streaming_format: Optional[str] = None,
    idempotent: Optional[bool] = None,
    status: Optional[str] = None,
    authentication: Optional[Dict[str, Any]] = None,
    depends: Optional[List[Dict[str, Any]]] = None,
    auth_required: bool = False,
    public: bool = True,
    extensions: Optional[Dict[str, Any]] = None,
    memory_enabled: bool = False,
) -> Callable:
    """Decorator that attaches a ``Skill`` to a callable.

    The resulting function gains a ``_skill`` attribute that servers and
    descriptor generators use to discover skills.

    Required fields default to the function's own attributes:
    ``id`` and ``name`` default to ``func.__name__``;
    ``description`` defaults to ``func.__doc__``.
    """

    def decorator(func: Callable) -> Callable:
        skill_id = id or func.__name__
        skill_name = name or skill_id
        skill_description = description or (func.__doc__ or "").strip()
        if not skill_description:
            raise ValueError(
                "Skill must have a description (via @skill(description=...) or docstring)"
            )
        metadata = SkillMetadata(
            id=skill_id,
            name=skill_name,
            description=skill_description,
            version=version,
            tags=tags,
            input_schema=input_schema,
            output_schema=output_schema,
            content_types=content_types,
            streaming=streaming,
            streaming_format=streaming_format,
            idempotent=idempotent,
            status=status,
            authentication=authentication,
            depends=depends,
            auth_required=auth_required,
            public=public,
            extensions=extensions,
            memory_enabled=memory_enabled,
        )
        skill_obj = Skill(func, metadata=metadata)
        setattr(func, "_skill", skill_obj)
        return func

    return decorator
