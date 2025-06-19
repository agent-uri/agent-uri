"""
Client SDK for the agent:// protocol.

This module provides the main client interface for interacting with agents
using the agent:// protocol.
"""

import logging
import urllib.parse
import uuid
from typing import Any, Dict, Iterator, NoReturn, Optional, Tuple

from .auth import AuthProvider

# Import from consolidated package
from .descriptor.models import AgentDescriptor
from .exceptions import (
    AgentClientError,
    InvocationError,
    ResolutionError,
    ResolverError,
    SessionError,
)
from .parser import AgentUri, parse_agent_uri
from .resolver.resolver import AgentResolver
from .transport.base import TransportError, TransportTimeoutError
from .transport.registry import default_registry

logger = logging.getLogger(__name__)


class AgentClient:
    """
    Client for interacting with agents via the agent:// protocol.

    This client handles URI parsing, resolution, and transport binding
    to provide a simple interface for invoking agent capabilities.
    """

    def __init__(
        self,
        resolver: Optional[AgentResolver] = None,
        auth_provider: Optional[AuthProvider] = None,
        timeout: int = 60,
        verify_ssl: bool = True,
        user_agent: str = "Agent-Client/0.1.0",
    ):
        """
        Initialize an agent client.

        Args:
            resolver: Optional custom resolver for agent URIs
            auth_provider: Optional authentication provider
            timeout: Default timeout in seconds for requests
            verify_ssl: Whether to verify SSL certificates
            user_agent: User-Agent header to include in requests
        """
        self.resolver = resolver or AgentResolver(
            timeout=timeout, verify_ssl=verify_ssl, user_agent=user_agent
        )
        self.auth_provider = auth_provider
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.user_agent = user_agent

        # Registry for transport protocol implementations
        self.registry = default_registry

    def invoke(
        self,
        uri: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke an agent capability via agent:// URI.

        This method handles parsing the URI, resolving it to an endpoint,
        selecting the appropriate transport, and invoking the capability.

        Args:
            uri: The agent URI to invoke (e.g., agent://planner.acme.ai/generate)
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the request
            timeout: Optional timeout in seconds (overrides default)
            **kwargs: Additional transport-specific parameters

        Returns:
            The response from the agent

        Raises:
            ResolutionError: If the agent URI cannot be resolved
            InvocationError: If the capability invocation fails
            AuthenticationError: If authentication fails
        """
        try:
            # Parse the URI
            parsed_uri = self._parse_uri(uri)

            # Extract capability path
            capability = self._get_capability_path(parsed_uri)

            # Merge parameters from URI query and params argument
            merged_params = self._merge_params(parsed_uri, params)

            # Prepare headers
            request_headers = self._prepare_headers(headers)

            # Resolve the URI to endpoint and descriptor
            endpoint, transport_protocol, descriptor = self._resolve_uri(parsed_uri)

            # Get the transport
            transport = self._get_transport(transport_protocol)

            # Set timeout
            request_timeout = timeout or self.timeout

            # Invoke the capability using the appropriate transport
            response = transport.invoke(
                endpoint=endpoint,
                capability=capability,
                params=merged_params,
                headers=request_headers,
                timeout=request_timeout,
                **kwargs,
            )

            return response

        except Exception as e:
            self._handle_exception(e)

    def stream(
        self,
        uri: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Iterator[Any]:
        """
        Stream responses from an agent capability via agent:// URI.

        Similar to invoke(), but returns an iterator that yields
        response chunks as they become available.

        Args:
            uri: The agent URI to invoke (e.g., agent://planner.acme.ai/generate)
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the request
            timeout: Optional timeout in seconds (overrides default)
            **kwargs: Additional transport-specific parameters

        Returns:
            An iterator that yields response chunks

        Raises:
            ResolutionError: If the agent URI cannot be resolved
            StreamingError: If streaming from the agent fails
            AuthenticationError: If authentication fails
        """
        try:
            # Parse the URI
            parsed_uri = self._parse_uri(uri)

            # Extract capability path
            capability = self._get_capability_path(parsed_uri)

            # Merge parameters from URI query and params argument
            merged_params = self._merge_params(parsed_uri, params)

            # Prepare headers
            request_headers = self._prepare_headers(headers)

            # Resolve the URI to endpoint and descriptor
            endpoint, transport_protocol, descriptor = self._resolve_uri(parsed_uri)

            # Get the transport
            transport = self._get_transport(transport_protocol)

            # Set timeout
            request_timeout = timeout or self.timeout

            # Determine stream format based on transport or descriptor
            stream_format = kwargs.get("stream_format")
            if stream_format is None:
                if descriptor and hasattr(descriptor, "interaction_model"):
                    # Base stream format on interaction model if available
                    if descriptor.interaction_model == "agent2agent":
                        stream_format = "sse"  # Agent2Agent uses SSE
                    else:
                        stream_format = "ndjson"  # Default to NDJSON
                else:
                    stream_format = "ndjson"  # Default

            kwargs["stream_format"] = stream_format

            # Stream from the capability using the appropriate transport
            for chunk in transport.stream(
                endpoint=endpoint,
                capability=capability,
                params=merged_params,
                headers=request_headers,
                timeout=request_timeout,
                **kwargs,
            ):
                yield chunk

        except Exception as e:
            self._handle_exception(e)

    def get_descriptor(self, uri: str) -> AgentDescriptor:
        """
        Get the descriptor for an agent URI.

        Args:
            uri: The agent URI

        Returns:
            The agent descriptor

        Raises:
            ResolutionError: If the agent URI cannot be resolved
        """
        try:
            # Parse the URI
            parsed_uri = self._parse_uri(uri)

            # Resolve the URI to get the descriptor
            _, _, descriptor = self._resolve_uri(parsed_uri)

            if not descriptor:
                raise ResolutionError(f"No descriptor found for agent URI: {uri}")

            return descriptor

        except Exception as e:
            self._handle_exception(e)

    def create_session(
        self,
        uri: str,
        session_id: Optional[str] = None,
        auth_provider: Optional[AuthProvider] = None,
    ) -> "AgentSession":
        """
        Create a session for interacting with an agent.

        A session maintains context between requests to the same agent,
        such as authentication and session identifiers.

        Args:
            uri: The agent URI
            session_id: Optional session identifier (UUID generated if not provided)
            auth_provider: Optional authentication provider for this session

        Returns:
            An AgentSession object
        """
        session_id = session_id or str(uuid.uuid4())
        auth = auth_provider or self.auth_provider

        return AgentSession(
            client=self, uri=uri, session_id=session_id, auth_provider=auth
        )

    def _parse_uri(self, uri: str) -> AgentUri:
        """
        Parse an agent URI string into an AgentUri object.

        Args:
            uri: The agent URI string

        Returns:
            Parsed AgentUri object

        Raises:
            ResolutionError: If the URI is invalid
        """
        try:
            return parse_agent_uri(uri)
        except Exception as e:
            raise ResolutionError(f"Invalid agent URI: {str(e)}")

    def _get_capability_path(self, uri: AgentUri) -> str:
        """
        Extract the capability path from an AgentUri.

        Args:
            uri: The parsed agent URI

        Returns:
            The capability path
        """
        # Remove leading/trailing slashes for consistency
        return uri.path.strip("/")

    def _merge_params(
        self, uri: AgentUri, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Merge parameters from URI query and params argument.

        Args:
            uri: The parsed agent URI
            params: Additional parameters to include

        Returns:
            Merged parameters dictionary
        """
        # Start with query parameters from URI
        merged = uri.query.copy() if uri.query else {}

        # Add auth parameters if available
        if self.auth_provider:
            auth_params = self.auth_provider.get_auth_params()
            if auth_params:
                merged.update(auth_params)

        # Add additional parameters
        if params:
            merged.update(params)

        return merged

    def _prepare_headers(
        self, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Prepare headers for a request, including authentication.

        Args:
            headers: Additional headers to include

        Returns:
            Complete headers dictionary
        """
        # Start with default headers
        prepared_headers = {"User-Agent": self.user_agent, "Accept": "application/json"}

        # Add authentication headers if available
        if self.auth_provider:
            # Refresh credentials if needed
            if self.auth_provider.is_expired:
                self.auth_provider.refresh()

            auth_headers = self.auth_provider.get_auth_headers()
            if auth_headers:
                prepared_headers.update(auth_headers)

        # Add additional headers
        if headers:
            prepared_headers.update(headers)

        return prepared_headers

    def _resolve_uri(self, uri: AgentUri) -> Tuple[str, str, Optional[AgentDescriptor]]:
        """
        Resolve an agent URI to an endpoint URL and descriptor.

        Args:
            uri: The parsed agent URI

        Returns:
            Tuple of (endpoint_url, transport_protocol, descriptor)

        Raises:
            ResolutionError: If the URI cannot be resolved
        """
        try:
            # Check if URI has explicit transport binding
            if uri.transport:
                # No need to resolve, construct endpoint directly
                endpoint = self._construct_endpoint(uri)
                return endpoint, uri.transport, None

            # Otherwise, resolve via the resolver
            descriptor, metadata = self.resolver.resolve(uri)

            # Get endpoint from metadata
            endpoint_raw = metadata.get("endpoint")
            if not endpoint_raw or not isinstance(endpoint_raw, str):
                raise ResolutionError(
                    f"No endpoint found for agent URI: {uri.to_string()}"
                )
            endpoint = endpoint_raw

            # Get transport protocol from metadata
            transport = metadata.get("transport", "https")

            return endpoint, transport, descriptor

        except ResolverError as e:
            raise ResolutionError(f"Failed to resolve agent URI: {str(e)}")

    def _construct_endpoint(self, uri: AgentUri) -> str:
        """
        Construct an endpoint URL from an agent URI with explicit transport.

        Args:
            uri: The parsed agent URI with transport

        Returns:
            The endpoint URL
        """
        # For local transport, handle specially
        if uri.transport == "local":
            return f"local://{uri.host}/{uri.path}"

        # For normal HTTP-based transports
        return f"{uri.transport}://{uri.host}"

    def _get_transport(self, protocol: str) -> Any:
        """
        Get a transport implementation for a protocol.

        Args:
            protocol: The transport protocol identifier

        Returns:
            A transport implementation

        Raises:
            InvocationError: If no transport is available for the protocol
        """
        try:
            return self.registry.get_transport(protocol)
        except Exception as e:
            raise InvocationError(
                f"No transport available for protocol '{protocol}': {str(e)}"
            )

    def _handle_exception(self, exception: Exception) -> NoReturn:
        """
        Handle exceptions by raising appropriate client exceptions.

        Args:
            exception: The original exception

        Raises:
            Appropriate AgentClientError subclass
        """
        # Propagate client exceptions unchanged
        if isinstance(exception, AgentClientError):
            raise exception

        # Map resolver exceptions to client exceptions
        elif isinstance(exception, ResolverError):
            raise ResolutionError(str(exception))

        # Special case for resolution errors raised during _resolve_uri
        elif "Resolution failed" in str(exception):
            raise ResolutionError(str(exception))

        # Special case for invocation errors raised during transport.invoke
        elif "Invocation failed" in str(exception):
            raise InvocationError(str(exception))

        # Map transport exceptions to client exceptions
        elif isinstance(exception, TransportTimeoutError):
            raise InvocationError(f"Request timed out: {str(exception)}")
        elif isinstance(exception, TransportError):
            raise InvocationError(str(exception))

        # Handle other exceptions
        else:
            raise AgentClientError(
                f"Unexpected error: {exception.__class__.__name__}: {str(exception)}"
            )


class AgentSession:
    """
    Session for maintaining context with an agent across multiple interactions.

    An AgentSession maintains state such as session identifiers, authentication,
    and context between interactions with the same agent.
    """

    def __init__(
        self,
        client: AgentClient,
        uri: str,
        session_id: str,
        auth_provider: Optional[AuthProvider] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize an agent session.

        Args:
            client: The agent client to use for requests
            uri: The base agent URI for this session
            session_id: Session identifier
            auth_provider: Optional authentication provider for this session
            context: Optional initial context dictionary
        """
        self.client = client
        self.base_uri = uri
        self.session_id = session_id
        self.auth_provider = auth_provider
        self.context = context or {}

        # Descriptor cache
        self._descriptor: Optional[AgentDescriptor] = None

    def invoke(
        self,
        capability: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke a capability on the agent associated with this session.

        Args:
            capability: The capability to invoke
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the request
            **kwargs: Additional transport-specific parameters

        Returns:
            The response from the agent

        Raises:
            SessionError: If the session is invalid
            InvocationError: If the capability invocation fails
        """
        try:
            # Build the URI for this capability
            uri = self._build_capability_uri(capability)

            # Build session headers
            session_headers = self._build_session_headers(headers)

            # Build session parameters
            session_params = self._build_session_params(params)

            # Invoke the capability with the client
            # Set the auth provider temporarily if needed
            original_auth = self.client.auth_provider
            if self.auth_provider:
                self.client.auth_provider = self.auth_provider

            try:
                response = self.client.invoke(
                    uri=uri, params=session_params, headers=session_headers, **kwargs
                )
            finally:
                # Restore the original auth provider
                if self.auth_provider:
                    self.client.auth_provider = original_auth

            # Update context with relevant response data
            self._update_context(response)

            return response

        except AgentClientError as e:
            if isinstance(e, ResolutionError):
                raise SessionError(f"Invalid session: {str(e)}")
            raise

    def stream(
        self,
        capability: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Iterator[Any]:
        """
        Stream responses from a capability on the agent associated with this session.

        Args:
            capability: The capability to invoke
            params: Optional parameters to pass to the capability
            headers: Optional headers to include in the request
            **kwargs: Additional transport-specific parameters

        Returns:
            An iterator that yields response chunks

        Raises:
            SessionError: If the session is invalid
            StreamingError: If streaming from the agent fails
        """
        try:
            # Build the URI for this capability
            uri = self._build_capability_uri(capability)

            # Build session headers
            session_headers = self._build_session_headers(headers)

            # Build session parameters
            session_params = self._build_session_params(params)

            # Stream from the capability
            # Set the auth provider temporarily if needed
            original_auth = self.client.auth_provider
            if self.auth_provider:
                self.client.auth_provider = self.auth_provider

            try:
                for chunk in self.client.stream(
                    uri=uri, params=session_params, headers=session_headers, **kwargs
                ):
                    yield chunk
            finally:
                # Restore the original auth provider
                if self.auth_provider:
                    self.client.auth_provider = original_auth

        except AgentClientError as e:
            if isinstance(e, ResolutionError):
                raise SessionError(f"Invalid session: {str(e)}")
            raise

    def get_descriptor(self) -> AgentDescriptor:
        """
        Get the descriptor for the agent associated with this session.

        Returns:
            The agent descriptor

        Raises:
            SessionError: If the descriptor cannot be retrieved
        """
        if not self._descriptor:
            try:
                self._descriptor = self.client.get_descriptor(self.base_uri)
            except AgentClientError as e:
                raise SessionError(f"Failed to get agent descriptor: {str(e)}")

        if self._descriptor is None:
            raise SessionError("Failed to retrieve agent descriptor")

        return self._descriptor

    def _build_capability_uri(self, capability: str) -> str:
        """
        Build a URI for a capability using the session's base URI.

        Args:
            capability: The capability to invoke

        Returns:
            The complete capability URI
        """
        # Parse the base URI
        try:
            base_uri = parse_agent_uri(self.base_uri)
        except Exception as e:
            raise SessionError(f"Invalid base URI: {str(e)}")

        # Build a path that combines the base URI path and the capability
        base_path = base_uri.path.strip("/")
        capability_path = capability.strip("/")

        if base_path and capability_path:
            # Combine base path and capability
            full_path = f"{base_path}/{capability_path}"
        elif capability_path:
            # Use capability if base path is empty
            full_path = capability_path
        else:
            # Use base path if capability is empty
            full_path = base_path

        # Reconstruct the URI with the new path
        parts = urllib.parse.urlparse(self.base_uri)
        new_uri = urllib.parse.urlunparse(
            (
                parts.scheme,
                parts.netloc,
                full_path,
                parts.params,
                parts.query,
                parts.fragment,
            )
        )

        return new_uri

    def _build_session_headers(
        self, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Build headers for a session request.

        Args:
            headers: Additional headers to include

        Returns:
            Complete headers dictionary
        """
        # Start with session headers
        session_headers = {"X-Session-ID": self.session_id}

        # Add additional headers
        if headers:
            session_headers.update(headers)

        return session_headers

    def _build_session_params(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build parameters for a session request.

        Args:
            params: Additional parameters to include

        Returns:
            Complete parameters dictionary
        """
        # Start with context parameters relevant to this request
        session_params: Dict[str, Any] = {"session_id": self.session_id}

        # Add context parameters if needed
        if self.context.get("include_context", False):
            session_params["context"] = self.context

        # Add additional parameters
        if params:
            session_params.update(params)

        return session_params

    def _update_context(self, response: Any) -> None:
        """
        Update the session context based on the response.

        Args:
            response: The response from the agent
        """
        # Extract context from response if it's a dictionary
        if isinstance(response, dict):
            if "context" in response:
                self.context.update(response["context"])
            if "session_context" in response:
                self.context.update(response["session_context"])
