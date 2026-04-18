"""
Client SDK for the agent:// protocol.

Aligned with draft-narvaneni-agent-uri-03.

Correlation uses W3C Trace Context (``traceparent``, ``tracestate``) and
W3C Baggage (``baggage: session.id=...``) instead of custom headers.
Version negotiation uses RFC 6906 profile in the ``Accept`` header.
Idempotency: an ``Idempotency-Key`` is sent for skills flagged as
``idempotent: true`` in the descriptor. ``Retry-After`` and structured
``RateLimit`` / ``RateLimit-Policy`` headers are read off the response
and exposed on errors.
"""

import logging
import urllib.parse
import uuid
from typing import Any, Dict, Iterator, NoReturn, Optional, Tuple

from .auth import AuthProvider
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

#: Spec-registered media type for agent descriptors.
AGENT_DESCRIPTOR_MEDIA_TYPE = "application/agent+json"

#: Default Accept header with the v1 profile (RFC 6906).
DEFAULT_ACCEPT = (
    f'{AGENT_DESCRIPTOR_MEDIA_TYPE}; profile="urn:ietf:params:agent:v1", '
    "application/json;q=0.9"
)


class AgentClient:
    """High-level client for invoking skills via ``agent://`` URIs."""

    def __init__(
        self,
        resolver: Optional[AgentResolver] = None,
        auth_provider: Optional[AuthProvider] = None,
        timeout: int = 60,
        verify_ssl: bool = True,
        user_agent: str = "agent-uri/1.0",
    ):
        self.resolver = resolver or AgentResolver(
            timeout=timeout, verify_ssl=verify_ssl, user_agent=user_agent
        )
        self.auth_provider = auth_provider
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.user_agent = user_agent
        self.registry = default_registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(
        self,
        uri: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Invoke a skill.

        Raises:
            ResolutionError: If the agent URI cannot be resolved.
            InvocationError: If invocation fails.
            AuthenticationError: If authentication fails.
        """
        try:
            parsed = self._parse_uri(uri)
            skill_path = self._skill_path(parsed)
            merged_params = self._merge_params(parsed, params)
            endpoint, protocol, descriptor = self._resolve_uri(parsed)

            request_headers = self._prepare_headers(
                headers,
                descriptor=descriptor,
                skill_path=skill_path,
                idempotency_key=idempotency_key,
            )

            transport = self._get_transport(protocol)
            request_timeout = timeout or self.timeout

            return transport.invoke(
                endpoint=endpoint,
                capability=skill_path,
                params=merged_params,
                headers=request_headers,
                timeout=request_timeout,
                **kwargs,
            )

        except Exception as e:
            self._handle_exception(e)

    def stream(
        self,
        uri: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """Stream responses from a skill."""
        try:
            parsed = self._parse_uri(uri)
            skill_path = self._skill_path(parsed)
            merged_params = self._merge_params(parsed, params)
            endpoint, protocol, descriptor = self._resolve_uri(parsed)

            request_headers = self._prepare_headers(
                headers, descriptor=descriptor, skill_path=skill_path
            )
            transport = self._get_transport(protocol)
            request_timeout = timeout or self.timeout

            stream_format = kwargs.get("stream_format") or self._pick_stream_format(
                descriptor, skill_path
            )
            kwargs["stream_format"] = stream_format

            for chunk in transport.stream(
                endpoint=endpoint,
                capability=skill_path,
                params=merged_params,
                headers=request_headers,
                timeout=request_timeout,
                **kwargs,
            ):
                yield chunk

        except Exception as e:
            self._handle_exception(e)

    def get_descriptor(self, uri: str) -> AgentDescriptor:
        """Fetch and return the descriptor for an agent URI."""
        try:
            parsed = self._parse_uri(uri)
            _, _, descriptor = self._resolve_uri(parsed)
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
        """Create a session for per-interaction correlation."""
        return AgentSession(
            client=self,
            uri=uri,
            session_id=session_id or str(uuid.uuid4()),
            auth_provider=auth_provider or self.auth_provider,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _parse_uri(self, uri: str) -> AgentUri:
        try:
            return parse_agent_uri(uri)
        except Exception as e:
            raise ResolutionError(f"Invalid agent URI: {e}")

    def _skill_path(self, uri: AgentUri) -> str:
        return uri.path.strip("/")

    def _merge_params(
        self, uri: AgentUri, params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = dict(uri.query or {})
        if self.auth_provider:
            merged.update(self.auth_provider.get_auth_params() or {})
        if params:
            merged.update(params)
        return merged

    def _prepare_headers(
        self,
        headers: Optional[Dict[str, str]],
        descriptor: Optional[AgentDescriptor] = None,
        skill_path: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, str]:
        prepared: Dict[str, str] = {
            "User-Agent": self.user_agent,
            "Accept": DEFAULT_ACCEPT,
        }

        if self.auth_provider:
            if self.auth_provider.is_expired:
                self.auth_provider.refresh()
            auth_headers = self.auth_provider.get_auth_headers() or {}
            prepared.update(auth_headers)

        # Idempotency-Key: auto-generated when the descriptor marks the
        # target skill as idempotent. Caller override wins.
        if idempotency_key is None and descriptor is not None and skill_path:
            if _skill_is_idempotent(descriptor, skill_path):
                idempotency_key = str(uuid.uuid4())
        if idempotency_key:
            prepared["Idempotency-Key"] = idempotency_key

        if headers:
            prepared.update(headers)

        return prepared

    def _pick_stream_format(
        self, descriptor: Optional[AgentDescriptor], skill_path: str
    ) -> str:
        """Choose a streaming format preferring the skill's declared format."""
        if descriptor is not None:
            for s in descriptor.skills:
                if s.id == skill_path and getattr(s, "streaming_format", None):
                    return s.streaming_format  # type: ignore[return-value]
            if "agent2agent" in (descriptor.interaction_model or []):
                return "sse"
        return "ndjson"

    def _resolve_uri(self, uri: AgentUri) -> Tuple[str, str, Optional[AgentDescriptor]]:
        try:
            if uri.transport:
                return self._construct_endpoint(uri), uri.transport, None

            descriptor, metadata = self.resolver.resolve(uri)
            endpoint_raw = metadata.get("endpoint")
            if not endpoint_raw or not isinstance(endpoint_raw, str):
                raise ResolutionError(
                    f"No endpoint found for agent URI: {uri.to_string()}"
                )
            transport = metadata.get("transport", "https")
            return endpoint_raw, transport, descriptor

        except ResolverError as e:
            raise ResolutionError(f"Failed to resolve agent URI: {e}")

    def _construct_endpoint(self, uri: AgentUri) -> str:
        if uri.transport == "local":
            return f"local://{uri.host}/{uri.path}"
        if uri.transport == "unix":
            return f"unix://{uri.host}{uri.path}"
        return f"{uri.transport}://{uri.host}"

    def _get_transport(self, protocol: str) -> Any:
        try:
            return self.registry.get_transport(protocol)
        except Exception as e:
            raise InvocationError(
                f"No transport available for protocol '{protocol}': {e}"
            )

    def _handle_exception(self, exception: Exception) -> NoReturn:
        if isinstance(exception, AgentClientError):
            raise exception
        if isinstance(exception, ResolverError):
            raise ResolutionError(str(exception))
        if isinstance(exception, TransportTimeoutError):
            raise InvocationError(f"Request timed out: {exception}")
        if isinstance(exception, TransportError):
            raise InvocationError(str(exception))
        raise AgentClientError(
            f"Unexpected error: {exception.__class__.__name__}: {exception}"
        )


def _skill_is_idempotent(descriptor: AgentDescriptor, skill_path: str) -> bool:
    """Look up whether the skill at ``skill_path`` is marked idempotent."""
    for s in descriptor.skills:
        if s.id == skill_path:
            return bool(getattr(s, "idempotent", False))
    return False


class AgentSession:
    """A session for a sequence of interactions with one agent.

    The session id propagates via W3C Baggage (``baggage: session.id=...``)
    — there is no custom ``X-Session-ID`` header anymore.
    """

    def __init__(
        self,
        client: AgentClient,
        uri: str,
        session_id: str,
        auth_provider: Optional[AuthProvider] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.client = client
        self.base_uri = uri
        self.session_id = session_id
        self.auth_provider = auth_provider
        self.context = context or {}
        self._descriptor: Optional[AgentDescriptor] = None

    def invoke(
        self,
        capability: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        try:
            uri = self._build_skill_uri(capability)
            session_headers = self._build_session_headers(headers)
            session_params = self._build_session_params(params)

            original = self.client.auth_provider
            if self.auth_provider:
                self.client.auth_provider = self.auth_provider
            try:
                response = self.client.invoke(
                    uri=uri,
                    params=session_params,
                    headers=session_headers,
                    **kwargs,
                )
            finally:
                if self.auth_provider:
                    self.client.auth_provider = original

            self._update_context(response)
            return response

        except AgentClientError as e:
            if isinstance(e, ResolutionError):
                raise SessionError(f"Invalid session: {e}")
            raise

    def stream(
        self,
        capability: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        try:
            uri = self._build_skill_uri(capability)
            session_headers = self._build_session_headers(headers)
            session_params = self._build_session_params(params)

            original = self.client.auth_provider
            if self.auth_provider:
                self.client.auth_provider = self.auth_provider
            try:
                for chunk in self.client.stream(
                    uri=uri,
                    params=session_params,
                    headers=session_headers,
                    **kwargs,
                ):
                    yield chunk
            finally:
                if self.auth_provider:
                    self.client.auth_provider = original

        except AgentClientError as e:
            if isinstance(e, ResolutionError):
                raise SessionError(f"Invalid session: {e}")
            raise

    def get_descriptor(self) -> AgentDescriptor:
        if not self._descriptor:
            try:
                self._descriptor = self.client.get_descriptor(self.base_uri)
            except AgentClientError as e:
                raise SessionError(f"Failed to get agent descriptor: {e}")
        if self._descriptor is None:
            raise SessionError("Failed to retrieve agent descriptor")
        return self._descriptor

    # ------------------------------------------------------------------

    def _build_skill_uri(self, capability: str) -> str:
        try:
            base = parse_agent_uri(self.base_uri)
        except Exception as e:
            raise SessionError(f"Invalid base URI: {e}")

        base_path = base.path.strip("/")
        cap_path = capability.strip("/")
        if base_path and cap_path:
            full_path = f"{base_path}/{cap_path}"
        else:
            full_path = cap_path or base_path

        parts = urllib.parse.urlparse(self.base_uri)
        return urllib.parse.urlunparse(
            (
                parts.scheme,
                parts.netloc,
                full_path,
                parts.params,
                parts.query,
                parts.fragment,
            )
        )

    def _build_session_headers(
        self, headers: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        prepared: Dict[str, str] = {
            "baggage": f"session.id={self.session_id}",
        }
        if headers:
            prepared.update(headers)
        return prepared

    def _build_session_params(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        session_params: Dict[str, Any] = {"session_id": self.session_id}
        if self.context.get("include_context", False):
            session_params["context"] = self.context
        if params:
            session_params.update(params)
        return session_params

    def _update_context(self, response: Any) -> None:
        if isinstance(response, dict):
            if "context" in response:
                self.context.update(response["context"])
            if "session_context" in response:
                self.context.update(response["session_context"])
