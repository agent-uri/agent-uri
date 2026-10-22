"""
Agent server implementations for the agent:// protocol.

Aligned with draft-narvaneni-agent-uri-03. Servers register ``Skill``
runtime objects and expose them over HTTPS (and optionally WebSocket)
with an auto-generated ``agent.json`` descriptor.
"""

import abc
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    from fastapi.routing import APIRouter

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    FastAPI = None  # type: ignore
    APIRouter = None  # type: ignore
    HTTPException = None  # type: ignore
    Request = None  # type: ignore
    WebSocket = None  # type: ignore
    CORSMiddleware = None  # type: ignore
    JSONResponse = None  # type: ignore
    StreamingResponse = None  # type: ignore


from .descriptor import AgentDescriptorGenerator
from .exceptions import (
    AgentGoneError,
    AuthenticationError,
    ConfigurationError,
    ContentNegotiationError,
    HandlerError,
    InvalidInputError,
    SkillNotFoundError,
)
from .handler import BaseHandler, HTTPHandler, WebSocketHandler
from .skill import Skill

logger = logging.getLogger(__name__)


class AgentServer(abc.ABC):
    """Abstract base class for agent servers."""

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
        conformance_level: Optional[int] = 2,
        environment: Optional[str] = None,
        status: Optional[str] = None,
        server_url: Optional[str] = None,
    ):
        """Initialize an agent server.

        Args:
            name: Agent name.
            version: SemVer agent version.
            description: Human-readable description.
            provider: ``{"organization": str, "url": str}``.
            documentation_url: Human-readable documentation URL.
            interaction_model: Registered interaction models, e.g. ``["agent2agent"]``.
            auth: Authentication descriptor object (schemes, authorizationServer, ...).
            transport: Transport object; or omit to derive from ``server_url``.
            conformance_level: Self-declared conformance level (0-3). Defaults to 2.
            environment: Deployment environment hint.
            status: "active" | "deprecated" | "experimental".
            server_url: Convenience — if set and ``transport`` is absent, used
                as the HTTPS endpoint.
        """
        self.name = name
        self.version = version
        self.description = description

        self.descriptor_generator = AgentDescriptorGenerator(
            name=name,
            version=version,
            description=description,
            provider=provider,
            documentation_url=documentation_url,
            interaction_model=interaction_model,
            auth=auth,
            transport=transport,
            conformance_level=conformance_level,
            environment=environment,
            status=status,
            server_url=server_url,
        )

        self._handlers: Dict[str, BaseHandler] = {
            "http": HTTPHandler(),
            "websocket": WebSocketHandler(),
        }

        self._skills: Dict[str, Skill] = {}
        self._authenticator: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Skill registration
    # ------------------------------------------------------------------

    def register_skill(self, path: str, skill: Skill) -> None:
        """Register a Skill at a URI path."""
        self._skills[path] = skill
        self.descriptor_generator.register_skill(skill)
        for handler in self._handlers.values():
            handler.register_skill(path, skill)
        logger.info("Registered skill '%s' at path '%s'", skill.metadata.name, path)

    def register_skills_from_module(self, module: Any) -> int:
        """Register all ``@skill``-decorated callables on a module."""
        count = 0
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue
            attr = getattr(module, attr_name)
            maybe = getattr(attr, "_skill", None)
            if isinstance(maybe, Skill):
                self.register_skill(attr.__name__, maybe)
                count += 1
        return count

    def register_skills_from_object(self, obj: Any) -> int:
        """Register all ``@skill``-decorated methods on an object."""
        count = 0
        for attr_name in dir(obj):
            if attr_name.startswith("_"):
                continue
            attr = getattr(obj, attr_name)
            maybe = getattr(attr, "_skill", None)
            if isinstance(maybe, Skill):
                self.register_skill(attr.__name__, maybe)
                count += 1
        return count

    def register_authenticator(
        self,
        authenticator: Callable[[Dict[str, Any]], Union[bool, Dict[str, Any]]],
    ) -> None:
        """Register a global authenticator function."""
        self._authenticator = authenticator
        for handler in self._handlers.values():
            handler.register_authenticator(authenticator)
        logger.info("Registered authenticator")

    # ------------------------------------------------------------------
    # Descriptor
    # ------------------------------------------------------------------

    def get_agent_descriptor(self) -> Dict[str, Any]:
        """Return the current agent descriptor as a dict."""
        return self.descriptor_generator.generate_descriptor()

    def save_agent_descriptor(self, path: str) -> None:
        """Save the descriptor to disk."""
        self.descriptor_generator.save(path)

    # ------------------------------------------------------------------
    # Abstract transport hooks
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def handle_http_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    async def handle_websocket_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        raise NotImplementedError


if FASTAPI_AVAILABLE:

    def _problem_response(
        status: int,
        title: str,
        detail: str,
        type_uri: str = "about:blank",
        error_code: Optional[str] = None,
    ) -> JSONResponse:
        """Build an RFC 9457 problem-details response."""
        body: Dict[str, Any] = {
            "type": type_uri,
            "title": title,
            "status": status,
            "detail": detail,
        }
        if error_code:
            body["errorCode"] = error_code
        return JSONResponse(
            status_code=status,
            content=body,
            media_type="application/problem+json",
        )

    class FastAPIAgentServer(AgentServer):
        """FastAPI implementation of an agent server."""

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
            conformance_level: Optional[int] = 2,
            environment: Optional[str] = None,
            status: Optional[str] = None,
            server_url: Optional[str] = None,
            prefix: str = "",
            app: Optional["FastAPI"] = None,
            enable_cors: bool = True,
            cors_origins: Optional[List[str]] = None,
            enable_docs: bool = True,
            enable_agent_json: bool = True,
        ):
            super().__init__(
                name=name,
                version=version,
                description=description,
                provider=provider,
                documentation_url=documentation_url,
                interaction_model=interaction_model,
                auth=auth,
                transport=transport,
                conformance_level=conformance_level,
                environment=environment,
                status=status,
                server_url=server_url,
            )

            self.prefix = prefix
            self.enable_cors = enable_cors
            self.cors_origins = cors_origins or ["*"]
            self.enable_docs = enable_docs
            self.enable_agent_json = enable_agent_json

            self.app = app or FastAPI(
                title=name,
                description=description,
                version=version,
                docs_url="/docs" if enable_docs else None,
                redoc_url="/redoc" if enable_docs else None,
            )

            self.router = APIRouter(prefix=prefix)

            if enable_cors:
                self.app.add_middleware(
                    CORSMiddleware,
                    allow_origins=self.cors_origins,
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )

            self._setup_routes()
            self.app.include_router(self.router)

        # --------------------------------------------------------------

        def _setup_routes(self) -> None:
            if self.enable_agent_json:
                self.router.add_api_route(
                    "/agent.json",
                    self._get_agent_json,
                    methods=["GET"],
                    response_model=None,
                    summary="Get agent descriptor",
                )
                if not self.prefix:
                    # Spec: /.well-known/agents.json (plural).
                    self.app.add_api_route(
                        "/.well-known/agents.json",
                        self._get_agents_json,
                        methods=["GET"],
                        response_model=None,
                        summary="Well-known agents index",
                    )

            self.router.add_api_route(
                "/{path:path}",
                self._handle_http_request,
                methods=["GET", "POST"],
                response_model=None,
                summary="Invoke a skill",
            )

            async def websocket_wrapper(websocket: "WebSocket") -> None:
                path = websocket.url.path.lstrip("/")
                await self._handle_websocket_connection(websocket, path)

            self.router.add_websocket_route(
                "/{path:path}",
                websocket_wrapper,
                name="websocket",
            )

        async def _get_agent_json(self) -> JSONResponse:
            return JSONResponse(
                content=self.get_agent_descriptor(),
                media_type="application/agent+json",
            )

        async def _get_agents_json(self) -> JSONResponse:
            """Well-known agents index: one entry per registered agent name."""
            return JSONResponse(
                content={
                    "agents": {
                        self.name: {
                            "descriptor": (
                                f"{self.prefix}/agent.json"
                                if self.prefix
                                else "/agent.json"
                            )
                        }
                    }
                },
                media_type="application/json",
            )

        # --------------------------------------------------------------

        async def _handle_http_request(
            self, request: "Request", path: str
        ) -> Union[JSONResponse, StreamingResponse]:
            try:
                params: Dict[str, Any] = dict(request.query_params)

                if request.method == "POST":
                    body = await request.body()
                    if body:
                        try:
                            body_data = json.loads(body)
                            if isinstance(body_data, dict):
                                params.update(body_data)
                        except json.JSONDecodeError:
                            params["body"] = body.decode("utf-8")

                headers = dict(request.headers)

                # W3C Baggage / Trace Context propagate as-is in headers; the
                # skill receives them via handler kwargs if it opts in.
                session_metadata: Dict[str, Any] = {}
                # Spec-aligned correlation: prefer Baggage session.id, fall
                # back to legacy X-Session-ID for transitional compatibility.
                baggage = headers.get("baggage") or headers.get("Baggage")
                if baggage:
                    for entry in baggage.split(","):
                        entry = entry.strip()
                        if entry.startswith("session.id="):
                            session_metadata["session_id"] = entry.split("=", 1)[1]
                            break
                if "session_id" not in session_metadata and headers.get("X-Session-ID"):
                    session_metadata["session_id"] = headers.get("X-Session-ID")

                result = await self.handle_http_request(
                    path=path,
                    params=params,
                    headers=headers,
                    session_metadata=session_metadata,
                )

                return JSONResponse(
                    content=result,
                    media_type="application/json",
                )

            except SkillNotFoundError as e:
                return _problem_response(
                    404, "Skill Not Found", str(e), error_code=e.error_code.value
                )
            except AuthenticationError as e:
                return _problem_response(
                    401,
                    "Authentication Required",
                    str(e),
                    error_code=e.error_code.value,
                )
            except InvalidInputError as e:
                return _problem_response(
                    400, "Invalid Input", str(e), error_code=e.error_code.value
                )
            except ContentNegotiationError as e:
                return _problem_response(
                    406, "Not Acceptable", str(e), error_code=e.error_code.value
                )
            except AgentGoneError as e:
                return _problem_response(
                    410, "Gone", str(e), error_code=e.error_code.value
                )
            except HandlerError as e:
                return _problem_response(
                    500, "Handler Error", str(e), error_code=e.error_code.value
                )
            except Exception as e:
                logger.exception("Unexpected error handling HTTP request")
                return _problem_response(500, "Internal Server Error", str(e))

        # --------------------------------------------------------------

        async def _handle_websocket_connection(
            self, websocket: "WebSocket", path: str
        ) -> None:
            await websocket.accept()

            try:
                params_raw = await websocket.receive_text()
                params = json.loads(params_raw)

                session_metadata: Dict[str, Any] = {}
                if params.get("session_id"):
                    session_metadata["session_id"] = params.get("session_id")

                headers: Dict[str, str] = {}

                async for chunk in self.handle_websocket_request(
                    path=path,
                    params=params,
                    headers=headers,
                    session_metadata=session_metadata,
                ):
                    if isinstance(chunk, (dict, list)):
                        # NDJSON framing: one JSON value per line.
                        await websocket.send_text(json.dumps(chunk))
                    elif isinstance(chunk, str):
                        await websocket.send_text(chunk)
                    elif isinstance(chunk, bytes):
                        await websocket.send_bytes(chunk)
                    else:
                        await websocket.send_text(str(chunk))

            except SkillNotFoundError as e:
                await websocket.send_text(
                    json.dumps(
                        {
                            "error": "SkillNotFound",
                            "errorCode": e.error_code.value,
                            "message": str(e),
                        }
                    )
                )
            except AuthenticationError as e:
                await websocket.send_text(
                    json.dumps(
                        {
                            "error": "AuthenticationError",
                            "errorCode": e.error_code.value,
                            "message": str(e),
                        }
                    )
                )
            except InvalidInputError as e:
                await websocket.send_text(
                    json.dumps(
                        {
                            "error": "InvalidInput",
                            "errorCode": e.error_code.value,
                            "message": str(e),
                        }
                    )
                )
            except HandlerError as e:
                await websocket.send_text(
                    json.dumps(
                        {
                            "error": "HandlerError",
                            "errorCode": e.error_code.value,
                            "message": str(e),
                        }
                    )
                )
            except Exception as e:
                logger.exception("Unexpected error handling WebSocket request")
                await websocket.send_text(
                    json.dumps({"error": "InternalServerError", "message": str(e)})
                )
            finally:
                await websocket.close()

        # --------------------------------------------------------------

        async def handle_http_request(
            self,
            path: str,
            params: Dict[str, Any],
            headers: Optional[Dict[str, str]] = None,
            **kwargs: Any,
        ) -> Any:
            handler = self._handlers.get("http")
            if not handler:
                raise ConfigurationError("No HTTP handler registered")
            result = handler.handle_request(
                path=path, params=params, headers=headers, **kwargs
            )
            if asyncio.iscoroutine(result):
                return await result
            raise ConfigurationError("HTTP handler returned unexpected result type")

        async def handle_websocket_request(
            self,
            path: str,
            params: Dict[str, Any],
            headers: Optional[Dict[str, str]] = None,
            **kwargs: Any,
        ) -> Any:
            handler = self._handlers.get("websocket")
            if not handler:
                raise ConfigurationError("No WebSocket handler registered")
            result = handler.handle_request(
                path=path, params=params, headers=headers, **kwargs
            )
            if hasattr(result, "__aiter__"):
                async for chunk in result:  # type: ignore[union-attr]
                    yield chunk
            else:
                yield await result  # type: ignore[misc]

else:

    class FastAPIAgentServer(AgentServer):  # type: ignore[no-redef]
        """Placeholder when FastAPI is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "FastAPI is not installed. Install it with: pip install "
                "'agent-uri[server]' or pip install fastapi uvicorn"
            )

        async def handle_http_request(self, *args: Any, **kwargs: Any) -> Any:
            pass

        async def handle_websocket_request(self, *args: Any, **kwargs: Any) -> Any:
            pass
