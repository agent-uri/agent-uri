"""
Agent server implementations for the agent:// protocol.

This module provides abstract and concrete agent server implementations
that conform to the agent:// protocol.
"""

import abc
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

# Runtime imports
try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    from fastapi.routing import APIRouter

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    # Runtime placeholders
    FastAPI = None  # type: ignore
    APIRouter = None  # type: ignore
    HTTPException = None  # type: ignore
    Request = None  # type: ignore
    WebSocket = None  # type: ignore
    CORSMiddleware = None  # type: ignore
    JSONResponse = None  # type: ignore
    StreamingResponse = None  # type: ignore


from .capability import Capability
from .descriptor import AgentDescriptorGenerator
from .exceptions import (
    AuthenticationError,
    CapabilityNotFoundError,
    ConfigurationError,
    HandlerError,
    InvalidInputError,
)
from .handler import BaseHandler, HTTPHandler, WebSocketHandler

logger = logging.getLogger(__name__)


class AgentServer(abc.ABC):
    """
    Abstract base class for agent servers.

    This class defines the interface for agent servers that conform to the
    agent:// protocol, providing capability registration and request handling.
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
        Initialize an agent server.

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

        # Create descriptor generator
        self.descriptor_generator = AgentDescriptorGenerator(
            name=name,
            version=version,
            description=description,
            provider=provider,
            documentation_url=documentation_url,
            interaction_model=interaction_model,
            auth_schemes=auth_schemes,
            skills=skills,
            server_url=server_url,
        )

        # Request handlers by type
        self._handlers: Dict[str, BaseHandler] = {
            "http": HTTPHandler(),
            "websocket": WebSocketHandler(),
        }

        # Store registered capabilities
        self._capabilities: Dict[str, Capability] = {}

        # Authenticator function
        self._authenticator: Optional[Callable] = None

    def register_capability(self, path: str, capability: Capability) -> None:
        """
        Register a capability.

        Args:
            path: The URI path to register the capability at
            capability: The capability to register
        """
        # Store capability
        self._capabilities[path] = capability

        # Register with descriptor generator
        self.descriptor_generator.register_capability(capability)

        # Register with handlers
        for handler in self._handlers.values():
            handler.register_capability(path, capability)

        logger.info(
            f"Registered capability '{capability.metadata.name}' at path '{path}'"
        )

    def register_capabilities_from_module(self, module) -> int:
        """
        Register all capabilities from a module.

        Args:
            module: The module to scan for capabilities

        Returns:
            The number of capabilities registered
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
                # Register at default path
                path = attr.__name__
                self.register_capability(path, attr._capability)
                count += 1

        return count

    def register_capabilities_from_object(self, obj) -> int:
        """
        Register all capabilities from an object.

        Args:
            obj: The object to scan for capabilities

        Returns:
            The number of capabilities registered
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
                # Register at default path
                path = attr.__name__
                self.register_capability(path, attr._capability)
                count += 1

        return count

    def register_authenticator(
        self, authenticator: Callable[[Dict[str, Any]], Union[bool, Dict[str, Any]]]
    ) -> None:
        """
        Register an authenticator function.

        Args:
            authenticator: Function to authenticate requests
        """
        self._authenticator = authenticator

        # Register with all handlers
        for handler in self._handlers.values():
            handler.register_authenticator(authenticator)

        logger.info("Registered authenticator function")

    def get_agent_descriptor(self) -> Dict[str, Any]:
        """
        Get the agent descriptor.

        Returns:
            The agent descriptor as a dictionary
        """
        return self.descriptor_generator.generate_descriptor()

    def save_agent_descriptor(self, path: str) -> None:
        """
        Save the agent descriptor to a file.

        Args:
            path: The file path to save to
        """
        self.descriptor_generator.save(path)

    @abc.abstractmethod
    async def handle_http_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Any:
        """
        Handle an HTTP request.

        Args:
            path: The request path
            params: The request parameters
            headers: Optional request headers
            **kwargs: Additional request-specific parameters

        Returns:
            The response

        Raises:
            CapabilityNotFoundError: If no capability is found for the path
            HandlerError: If there is an error handling the request
        """
        pass

    @abc.abstractmethod
    async def handle_websocket_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Any:
        """
        Handle a WebSocket request.

        Args:
            path: The request path
            params: The request parameters
            headers: Optional request headers
            **kwargs: Additional request-specific parameters

        Returns:
            An async generator yielding response chunks

        Raises:
            CapabilityNotFoundError: If no capability is found for the path
            HandlerError: If there is an error handling the request
        """
        pass


if FASTAPI_AVAILABLE:

    class FastAPIAgentServer(AgentServer):
        """
        FastAPI implementation of an agent server.

        This class provides a FastAPI-based implementation of an agent server,
        making it easy to deploy agents as web services.
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
            prefix: str = "",
            app: Optional[FastAPI] = None,
            enable_cors: bool = True,
            cors_origins: Optional[List[str]] = None,
            enable_docs: bool = True,
            enable_agent_json: bool = True,
        ):
            """
            Initialize a FastAPI agent server.

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
                prefix: Optional URL prefix for all routes
                app: Optional existing FastAPI app to add routes to
                enable_cors: Whether to enable CORS
                cors_origins: CORS origins to allow
                enable_docs: Whether to enable API docs
                enable_agent_json: Whether to enable agent.json endpoint
            """
            super().__init__(
                name=name,
                version=version,
                description=description,
                provider=provider,
                documentation_url=documentation_url,
                interaction_model=interaction_model,
                auth_schemes=auth_schemes,
                skills=skills,
                server_url=server_url,
            )

            # Store settings
            self.prefix = prefix
            self.enable_cors = enable_cors
            self.cors_origins = cors_origins or ["*"]
            self.enable_docs = enable_docs
            self.enable_agent_json = enable_agent_json

            # Create or use FastAPI app
            self.app = app or FastAPI(
                title=name,
                description=description,
                version=version,
                docs_url="/docs" if enable_docs else None,
                redoc_url="/redoc" if enable_docs else None,
            )

            # Set up router
            self.router = APIRouter(prefix=prefix)

            # Add CORS middleware if enabled
            if enable_cors:
                self.app.add_middleware(
                    CORSMiddleware,
                    allow_origins=self.cors_origins,
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )

            # Set up routes
            self._setup_routes()

            # Register router with app
            self.app.include_router(self.router)

        def _setup_routes(self) -> None:
            """Set up FastAPI routes."""
            # Set up agent.json endpoint if enabled
            if self.enable_agent_json:
                self.router.add_api_route(
                    "/agent.json",
                    self._get_agent_json,
                    methods=["GET"],
                    response_model=None,
                    summary="Get agent descriptor",
                    description="Returns the agent.json descriptor for this agent.",
                )

                # Add .well-known/agent.json endpoint for A2A compatibility
                if not self.prefix:
                    self.app.add_api_route(
                        "/.well-known/agent.json",
                        self._get_agent_json,
                        methods=["GET"],
                        response_model=None,
                        summary="Get agent descriptor (A2A compatible)",
                        description=(
                            "Returns the agent.json descriptor for this agent "
                            "(A2A compatible path)."
                        ),
                    )

            # Dynamic routes for capabilities
            self.router.add_api_route(
                "/{path:path}",
                self._handle_http_request,
                methods=["GET", "POST"],
                response_model=None,
                summary="Invoke a capability",
                description="Invokes an agent capability.",
            )

            # WebSocket route for streaming
            async def websocket_wrapper(websocket: "WebSocket") -> None:
                # Extract path from the websocket path_info
                path = websocket.url.path.lstrip("/")
                await self._handle_websocket_connection(websocket, path)

            self.router.add_websocket_route(
                "/{path:path}",
                websocket_wrapper,
                name="websocket",
            )

        async def _get_agent_json(self) -> JSONResponse:
            """
            Get the agent.json descriptor.

            Returns:
                JSON response with the agent descriptor
            """
            descriptor = self.get_agent_descriptor()
            return JSONResponse(content=descriptor, media_type="application/json")

        async def _handle_http_request(
            self, request: Request, path: str
        ) -> Union[JSONResponse, StreamingResponse]:
            """
            Handle an HTTP request for a capability.

            Args:
                request: The FastAPI request
                path: The requested path

            Returns:
                JSON response with the capability result

            Raises:
                HTTPException: If the request cannot be handled
            """
            try:
                # Parse parameters from query or body
                params = {}

                # Get query parameters
                for key, value in request.query_params.items():
                    params[key] = value

                # Get body parameters for POST
                if request.method == "POST":
                    body = await request.body()
                    if body:
                        try:
                            # Try to parse as JSON
                            body_data = json.loads(body)
                            if isinstance(body_data, dict):
                                params.update(body_data)
                        except json.JSONDecodeError:
                            # If not JSON, add as raw body
                            params["body"] = body.decode("utf-8")

                # Get headers
                headers = {}
                for key, value in request.headers.items():
                    headers[key] = value

                # Get session ID from header if present and store in dedicated
                # metadata field
                # instead of using both kwargs and explicit parameter
                session_metadata = {}
                if headers.get("X-Session-ID"):
                    session_metadata["session_id"] = headers.get("X-Session-ID")

                # Handle request
                result = await self.handle_http_request(
                    path=path,
                    params=params,
                    headers=headers,
                    session_metadata=session_metadata,  # Pass as dedicated metadata
                )

                # Return JSON response
                return JSONResponse(content=result, media_type="application/json")

            except CapabilityNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except AuthenticationError as e:
                raise HTTPException(status_code=401, detail=str(e))
            except InvalidInputError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except HandlerError as e:
                raise HTTPException(status_code=500, detail=str(e))
            except Exception as e:
                logger.exception("Unexpected error handling HTTP request")
                raise HTTPException(
                    status_code=500, detail=f"Internal server error: {str(e)}"
                )

        async def _handle_websocket_connection(
            self, websocket: WebSocket, path: str
        ) -> None:
            """
            Handle a WebSocket connection.

            Args:
                websocket: The FastAPI WebSocket
                path: The requested path
            """
            await websocket.accept()

            try:
                # Get the first message (parameters)
                params_raw = await websocket.receive_text()
                params = json.loads(params_raw)

                # Get session ID from parameters if present and store in
                # dedicated metadata
                session_metadata = {}
                if params.get("session_id"):
                    session_metadata["session_id"] = params.get("session_id")

                # Extract headers
                headers: Dict[str, str] = {}
                # WebSocket doesn't give us headers directly, so use what we can

                # Handle request and stream response
                async for chunk in self.handle_websocket_request(
                    path=path,
                    params=params,
                    headers=headers,
                    session_metadata=session_metadata,
                ):
                    # Format and send chunk
                    if isinstance(chunk, (dict, list)):
                        await websocket.send_text(json.dumps(chunk))
                    elif isinstance(chunk, str):
                        await websocket.send_text(chunk)
                    elif isinstance(chunk, bytes):
                        await websocket.send_bytes(chunk)
                    else:
                        await websocket.send_text(str(chunk))

            except CapabilityNotFoundError as e:
                await websocket.send_text(
                    json.dumps({"error": "CapabilityNotFound", "message": str(e)})
                )
            except AuthenticationError as e:
                await websocket.send_text(
                    json.dumps({"error": "AuthenticationError", "message": str(e)})
                )
            except InvalidInputError as e:
                await websocket.send_text(
                    json.dumps({"error": "InvalidInput", "message": str(e)})
                )
            except HandlerError as e:
                await websocket.send_text(
                    json.dumps({"error": "HandlerError", "message": str(e)})
                )
            except Exception as e:
                logger.exception("Unexpected error handling WebSocket request")
                await websocket.send_text(
                    json.dumps({"error": "InternalServerError", "message": str(e)})
                )
            finally:
                # Close WebSocket
                await websocket.close()

        async def handle_http_request(
            self,
            path: str,
            params: Dict[str, Any],
            headers: Optional[Dict[str, str]] = None,
            **kwargs,
        ) -> Any:
            """
            Handle an HTTP request.

            Args:
                path: The request path
                params: The request parameters
                headers: Optional request headers
                **kwargs: Additional request-specific parameters

            Returns:
                The response

            Raises:
                CapabilityNotFoundError: If no capability is found for the path
                HandlerError: If there is an error handling the request
            """
            # Get HTTP handler
            handler = self._handlers.get("http")
            if not handler:
                raise ConfigurationError("No HTTP handler registered")

            # Handle request - HTTP handlers return Coroutines
            result = handler.handle_request(
                path=path, params=params, headers=headers, **kwargs
            )
            # Type check: HTTP handlers should return Coroutines
            if asyncio.iscoroutine(result):
                return await result
            else:
                raise ConfigurationError("HTTP handler returned unexpected result type")

        async def handle_websocket_request(
            self,
            path: str,
            params: Dict[str, Any],
            headers: Optional[Dict[str, str]] = None,
            **kwargs,
        ) -> Any:
            """
            Handle a WebSocket request.

            Args:
                path: The request path
                params: The request parameters
                headers: Optional request headers
                **kwargs: Additional request-specific parameters

            Returns:
                An async generator yielding response chunks

            Raises:
                CapabilityNotFoundError: If no capability is found for the path
                HandlerError: If there is an error handling the request
            """
            # Get WebSocket handler
            handler = self._handlers.get("websocket")
            if not handler:
                raise ConfigurationError("No WebSocket handler registered")

            # Handle request
            result = handler.handle_request(
                path=path, params=params, headers=headers, **kwargs
            )
            # Check if result is async iterable
            if hasattr(result, "__aiter__"):
                async for chunk in result:  # type: ignore
                    yield chunk
            else:
                # If not async iterable, treat as single result
                response = await result  # type: ignore
                yield response

else:
    # Define a placeholder if FastAPI is not available
    class FastAPIAgentServer(AgentServer):  # type: ignore[no-redef]
        """Placeholder for FastAPIAgentServer when FastAPI is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "FastAPI is not installed. Install it with: "
                "pip install fastapi uvicorn"
            )

        async def handle_http_request(self, *args, **kwargs):
            pass

        async def handle_websocket_request(self, *args, **kwargs):
            pass
