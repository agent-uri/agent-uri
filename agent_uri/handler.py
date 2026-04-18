"""
Request handlers for the agent:// protocol.

Aligned with draft-narvaneni-agent-uri-03. Handlers route incoming
skill invocations over different transports (HTTPS, WebSocket) to the
registered ``Skill`` runtime objects.
"""

import abc
import asyncio
import logging
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Optional,
    Union,
)

from .exceptions import (
    AuthenticationError,
    HandlerError,
    InvalidInputError,
    SkillNotFoundError,
)
from .skill import Skill

logger = logging.getLogger(__name__)


class BaseHandler(abc.ABC):
    """Abstract base class for transport-specific request handlers."""

    def __init__(self) -> None:
        self._skills: Dict[str, Skill] = {}
        self._authenticator: Optional[Callable] = None

    def register_skill(self, path: str, skill: Skill) -> None:
        """Register a Skill at the given path."""
        self._skills[path] = skill
        logger.debug("Registered skill at path '%s'", path)

    def register_authenticator(
        self,
        authenticator: Callable[
            [Dict[str, Any]], Union[bool, Dict[str, Any], Awaitable[Any]]
        ],
    ) -> None:
        """Register an authenticator. May return bool or auth metadata dict."""
        self._authenticator = authenticator
        logger.debug("Registered authenticator")

    def get_skill(self, path: str) -> Skill:
        """Look up a Skill by path.

        Falls back to prefix-matching (``a/b/c`` → ``a/b`` → ``a``) so
        nested routes resolve to their parent skill if registered.

        Raises:
            SkillNotFoundError: If no skill is registered at the path.
        """
        normalized = path.strip("/")
        if normalized in self._skills:
            return self._skills[normalized]

        parts = normalized.split("/")
        while parts:
            parts.pop()
            candidate = "/".join(parts)
            if candidate in self._skills:
                return self._skills[candidate]

        raise SkillNotFoundError(
            skill_id=path,
            available_skills=list(self._skills.keys()),
        )

    async def authenticate(
        self, request_data: Dict[str, Any]
    ) -> Union[bool, Dict[str, Any]]:
        """Run the registered authenticator (if any) against a request."""
        if not self._authenticator:
            return True
        try:
            result = self._authenticator(request_data)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {e}")

    @abc.abstractmethod
    def handle_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Union[Coroutine[Any, Any, Any], AsyncGenerator[Any, None]]:
        """Handle a skill invocation request."""
        raise NotImplementedError


class HTTPHandler(BaseHandler):
    """Handler for HTTPS skill invocations."""

    def handle_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Coroutine[Any, Any, Any]:
        return self._handle(path, params, headers, **kwargs)

    async def _handle(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        try:
            skill = self.get_skill(path)

            if skill.metadata.auth_required:
                auth_data = kwargs.get("auth", {})
                auth_result = await self.authenticate(
                    {
                        "path": path,
                        "params": params,
                        "headers": headers or {},
                        **auth_data,
                    }
                )
                if not auth_result:
                    raise AuthenticationError("Authentication required")
                if isinstance(auth_result, dict):
                    kwargs["auth_metadata"] = auth_result

            session_metadata = kwargs.pop("session_metadata", {})
            session_id = session_metadata.get("session_id")
            context = kwargs.pop("context", None)

            return await skill.invoke(
                params=params,
                session_id=session_id,
                context=context,
                **kwargs,
            )

        except (SkillNotFoundError, AuthenticationError, InvalidInputError):
            raise
        except Exception as e:
            raise HandlerError(f"Error handling HTTP request: {e}")


class WebSocketHandler(BaseHandler):
    """Handler for WebSocket skill invocations (including streaming)."""

    def handle_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        return self._handle(path, params, headers, **kwargs)

    async def _handle(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        try:
            skill = self.get_skill(path)

            if not skill.metadata.streaming:
                result = await self._non_streaming(path, params, headers, **kwargs)
                yield result
                return

            if skill.metadata.auth_required:
                auth_data = kwargs.get("auth", {})
                auth_result = await self.authenticate(
                    {
                        "path": path,
                        "params": params,
                        "headers": headers or {},
                        **auth_data,
                    }
                )
                if not auth_result:
                    raise AuthenticationError("Authentication required")
                if isinstance(auth_result, dict):
                    kwargs["auth_metadata"] = auth_result

            session_metadata = kwargs.pop("session_metadata", {})
            session_id = session_metadata.get("session_id")
            context = kwargs.pop("context", None)

            result = await skill.invoke(
                params=params,
                session_id=session_id,
                context=context,
                streaming=True,
                **kwargs,
            )

            if asyncio.iscoroutine(result):
                yield await result
            elif hasattr(result, "__aiter__"):
                async for chunk in result:
                    yield chunk
            elif hasattr(result, "__iter__") and not isinstance(
                result, (str, bytes, dict)
            ):
                for chunk in result:
                    yield chunk
            else:
                yield result

        except (SkillNotFoundError, AuthenticationError, InvalidInputError):
            raise
        except Exception as e:
            raise HandlerError(f"Error handling WebSocket request: {e}")

    async def _non_streaming(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Delegate a non-streaming request to an HTTPHandler."""
        http_handler = HTTPHandler()
        http_handler._skills = self._skills
        http_handler._authenticator = self._authenticator
        return await http_handler.handle_request(path, params, headers, **kwargs)
