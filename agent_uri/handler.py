"""
Request handlers for different transport protocols.

This module provides handlers for processing agent capability requests
over different transport protocols (HTTP, WebSocket, etc.)
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

from .capability import Capability
from .exceptions import (
    AuthenticationError,
    CapabilityNotFoundError,
    HandlerError,
    InvalidInputError,
)

logger = logging.getLogger(__name__)


class BaseHandler(abc.ABC):
    """
    Abstract base class for request handlers.

    This class defines the interface for handlers that process capability
    requests over different transport protocols.
    """

    def __init__(self) -> None:
        """Initialize the handler."""
        self._capabilities: Dict[str, Capability] = {}
        self._authenticator: Optional[Callable] = None

    def register_capability(self, name: str, capability: Capability) -> None:
        """
        Register a capability with this handler.

        Args:
            name: The name/path to register the capability under
            capability: The capability to register
        """
        self._capabilities[name] = capability
        logger.debug(f"Registered capability at path '{name}'")

    def register_authenticator(
        self,
        authenticator: Callable[
            [Dict[str, Any]], Union[bool, Dict[str, Any], Awaitable[Any]]
        ],
    ) -> None:
        """
        Register an authenticator function.

        The authenticator is called to validate incoming requests. It may
        return a boolean (auth succeeded/failed) or a dictionary of
        authentication metadata to include with the capability.

        Args:
            authenticator: The authenticator function
        """
        self._authenticator = authenticator
        logger.debug("Registered authenticator")

    def get_capability(self, path: str) -> Capability:
        """
        Get a registered capability by path.

        Args:
            path: The path to the capability

        Returns:
            The capability

        Raises:
            CapabilityNotFoundError: If no capability is registered at the path
        """
        # Normalize path
        normalized_path = path.strip("/")

        # Try exact match first
        if normalized_path in self._capabilities:
            return self._capabilities[normalized_path]

        # Try partial match (e.g., 'a/b/c' -> 'a/b' -> 'a')
        parts = normalized_path.split("/")
        while parts:
            parts.pop()
            candidate = "/".join(parts)
            if candidate in self._capabilities:
                return self._capabilities[candidate]

        # No capability found
        raise CapabilityNotFoundError(f"No capability found for path '{path}'")

    async def authenticate(
        self, request_data: Dict[str, Any]
    ) -> Union[bool, Dict[str, Any]]:
        """
        Authenticate a request.

        Args:
            request_data: The request data containing auth information

        Returns:
            True if authenticated, False if not, or a dict of auth metadata

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self._authenticator:
            # No authenticator registered, authentication succeeds by default
            return True

        try:
            # Call the authenticator
            result = self._authenticator(request_data)

            # Handle async authenticator
            if asyncio.iscoroutine(result):
                result = await result

            return result
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    @abc.abstractmethod
    def handle_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Union[Coroutine[Any, Any, Any], AsyncGenerator[Any, None]]:
        """
        Handle a capability request.

        Args:
            path: The path to the capability
            params: The parameters for the capability
            headers: Optional request headers
            **kwargs: Additional transport-specific parameters

        Returns:
            The capability result

        Raises:
            CapabilityNotFoundError: If no capability is registered at the path
            HandlerError: If the request cannot be handled
        """
        pass


class HTTPHandler(BaseHandler):
    """
    Handler for HTTP requests.

    This handler processes capability requests over HTTP, including
    support for authentication, content negotiation, and error handling.
    """

    def __init__(self) -> None:
        """Initialize the HTTP handler."""
        super().__init__()

    def handle_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Coroutine[Any, Any, Any]:
        """
        Handle an HTTP capability request.

        Args:
            path: The path to the capability
            params: The parameters for the capability
            headers: Optional request headers
            **kwargs: Additional HTTP-specific parameters
                - session_id: Optional session identifier
                - context: Optional session context
                - auth: Optional authentication data

        Returns:
            A coroutine that yields the capability result

        Raises:
            CapabilityNotFoundError: If no capability is registered at the path
            AuthenticationError: If authentication fails
            HandlerError: If the request cannot be handled
        """
        return self._handle_http_request(path, params, headers, **kwargs)

    async def _handle_http_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Any:
        """
        Internal async method to handle HTTP requests.
        """
        try:
            # Get the capability
            capability = self.get_capability(path)

            # Check if authentication is required
            if capability.metadata.auth_required:
                # Get auth data from request
                auth_data = kwargs.get("auth", {})

                # Authenticate the request
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

                # Add auth metadata to kwargs if provided
                if isinstance(auth_result, dict):
                    kwargs["auth_metadata"] = auth_result

            # Cleanly separate session information from other kwargs
            session_metadata = kwargs.pop("session_metadata", {})
            session_id = session_metadata.get("session_id")
            context = kwargs.pop("context", None)

            # Invoke the capability with session info kept separate from kwargs
            result = await capability.invoke(
                params=params, session_id=session_id, context=context, **kwargs
            )

            return result

        except CapabilityNotFoundError:
            # Re-raise capability not found errors
            raise
        except AuthenticationError:
            # Re-raise authentication errors
            raise
        except InvalidInputError:
            # Re-raise input validation errors
            raise
        except Exception as e:
            # Wrap other exceptions in HandlerError
            raise HandlerError(f"Error handling HTTP request: {str(e)}")


class WebSocketHandler(BaseHandler):
    """
    Handler for WebSocket requests.

    This handler processes capability requests over WebSocket, including
    support for authentication, streaming responses, and error handling.
    """

    def __init__(self) -> None:
        """Initialize the WebSocket handler."""
        super().__init__()

    def handle_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> AsyncGenerator[Any, None]:
        """
        Handle a WebSocket capability request.

        Args:
            path: The path to the capability
            params: The parameters for the capability
            headers: Optional request headers
            **kwargs: Additional WebSocket-specific parameters
                - session_id: Optional session identifier
                - context: Optional session context
                - auth: Optional authentication data
                - format: Stream format (ndjson, sse, etc.)

        Returns:
            An async generator that yields response chunks

        Raises:
            CapabilityNotFoundError: If no capability is registered at the path
            AuthenticationError: If authentication fails
            HandlerError: If the request cannot be handled
        """
        return self._handle_websocket_request(path, params, headers, **kwargs)

    async def _handle_websocket_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> AsyncGenerator[Any, None]:
        """
        Internal async generator method to handle WebSocket requests.
        """
        try:
            # Get the capability
            capability = self.get_capability(path)

            # Check if streaming is supported
            if not capability.metadata.streaming:
                # If not streaming, return a single result
                result = await self.handle_non_streaming_request(
                    path, params, headers, **kwargs
                )
                yield result
                return

            # Check if authentication is required
            if capability.metadata.auth_required:
                # Get auth data from request
                auth_data = kwargs.get("auth", {})

                # Authenticate the request
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

                # Add auth metadata to kwargs if provided
                if isinstance(auth_result, dict):
                    kwargs["auth_metadata"] = auth_result

            # Cleanly separate session information from other kwargs
            session_metadata = kwargs.pop("session_metadata", {})
            session_id = session_metadata.get("session_id")
            context = kwargs.pop("context", None)

            # Invoke the capability with streaming
            result = await capability.invoke(
                params=params,
                session_id=session_id,
                context=context,
                streaming=True,
                **kwargs,
            )

            # Handle different result types
            if asyncio.iscoroutine(result):
                # Single awaitable result
                result = await result
                yield result
            elif hasattr(result, "__aiter__"):
                # Async iterator (streaming)
                async for chunk in result:
                    yield chunk
            elif hasattr(result, "__iter__"):
                # Regular iterator
                for chunk in result:
                    yield chunk
            else:
                # Single result
                yield result

        except CapabilityNotFoundError:
            # Re-raise capability not found errors
            raise
        except AuthenticationError:
            # Re-raise authentication errors
            raise
        except InvalidInputError:
            # Re-raise input validation errors
            raise
        except Exception as e:
            # Wrap other exceptions in HandlerError
            raise HandlerError(f"Error handling WebSocket request: {str(e)}")

    async def handle_non_streaming_request(
        self,
        path: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Any:
        """
        Handle a non-streaming WebSocket request.

        This is called when a streaming request is made to a non-streaming
        capability. It invokes the capability normally and returns a single
        result.

        Args:
            path: The path to the capability
            params: The parameters for the capability
            headers: Optional request headers
            **kwargs: Additional WebSocket-specific parameters

        Returns:
            The capability result

        Raises:
            CapabilityNotFoundError: If no capability is registered at the path
            AuthenticationError: If authentication fails
            HandlerError: If the request cannot be handled
        """
        # Create an HTTP handler for non-streaming requests
        http_handler = HTTPHandler()

        # Copy capabilities and authenticator
        http_handler._capabilities = self._capabilities
        http_handler._authenticator = self._authenticator

        # Handle request using HTTP handler
        return await http_handler.handle_request(path, params, headers, **kwargs)
