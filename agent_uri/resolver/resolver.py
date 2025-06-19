"""
Agent URI Resolution Framework

This module provides the core functionality for resolving agent:// URIs
to their corresponding agent descriptors and endpoints by discovering
and parsing .well-known/agent.json or .well-known/agents.json files.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple, Union

# Try importing requests, provide clear error message if missing
try:
    from requests.exceptions import RequestException, Timeout
except ImportError:
    raise ImportError(
        "The 'requests' package is required for this module. "
        "Please install it using: pip install requests requests-cache"
    )

# Try importing required modules from other packages
# Import from consolidated package
from ..descriptor.models import AgentDescriptor
from ..descriptor.parser import parse_descriptor
from ..parser import AgentUri, parse_agent_uri
from .cache import CacheProvider, default_cache

logger = logging.getLogger(__name__)


# Exception classes
class ResolverError(Exception):
    """Base exception for resolver errors."""

    pass


class ResolverTimeoutError(ResolverError):
    """Exception raised when resolver requests time out."""

    pass


class ResolverNotFoundError(ResolverError):
    """Exception raised when an agent cannot be found."""

    pass


class AgentResolver:
    """
    Resolver for agent:// URIs.

    The resolver discovers agent endpoints by attempting to fetch and parse
    .well-known/agent.json or .well-known/agents.json files. It supports HTTP
    caching mechanisms via the requests-cache library.
    """

    def __init__(
        self,
        cache_provider: Optional[CacheProvider] = None,
        timeout: int = 10,
        verify_ssl: bool = True,
        user_agent: str = "AgentURI-Resolver/1.0",
        fallback_to_https: bool = True,
    ):
        """
        Initialize an agent resolver.

        Args:
            cache_provider: Cache provider to use (defaults to in-memory cache)
            timeout: HTTP request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            user_agent: User-Agent header to send with requests
            fallback_to_https: Whether to fallback to HTTPS if explicit
                transport not specified
        """
        self.cache = cache_provider or default_cache
        self.session = self.cache.get_session()
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.user_agent = user_agent
        self.fallback_to_https = fallback_to_https

        # Set default headers
        self.session.headers.update(
            {"User-Agent": self.user_agent, "Accept": "application/json"}
        )

    def resolve(
        self, uri: Union[str, AgentUri]
    ) -> Tuple[Optional[AgentDescriptor], Dict[str, Any]]:
        """
        Resolve an agent URI to its agent descriptor and resolution metadata.

        Args:
            uri: An agent URI string or AgentUri object

        Returns:
            A tuple containing (AgentDescriptor, resolution_metadata)

        Raises:
            ResolverError: If the agent cannot be resolved
            ResolverTimeoutError: If resolution times out
            ResolverNotFoundError: If no agent descriptor is found
        """
        # Parse URI if string
        if isinstance(uri, str):
            try:
                uri = parse_agent_uri(uri)
            except Exception as e:
                raise ResolverError(f"Invalid agent URI: {e}")

        # Start with empty metadata
        metadata: Dict[str, Any] = {
            "uri": uri.to_string(),
            "resolution_path": [],
            "transport": (uri.transport or "https" if self.fallback_to_https else None),
        }

        # Try to resolve via agent.json or agents.json
        try:
            descriptor, resolution_meta = self._resolve_via_well_known(uri)
            metadata.update(resolution_meta)
            return descriptor, metadata
        except ResolverNotFoundError:
            # If we have an explicit transport binding, we should still
            # try to construct an endpoint
            if uri.transport:
                resolution_path = metadata["resolution_path"]
                if isinstance(resolution_path, list):
                    resolution_path.append("explicit_transport")
                endpoint = self._construct_endpoint_from_transport(uri)
                metadata["endpoint"] = endpoint
                metadata["resolution_method"] = "transport_binding"
                # We don't have a descriptor, but we have an endpoint
                return None, metadata
            else:
                # Re-raise if we can't resolve at all
                raise

    def _resolve_via_well_known(
        self, uri: AgentUri
    ) -> Tuple[AgentDescriptor, Dict[str, Any]]:
        """
        Resolve an agent URI via .well-known/agent.json or
        .well-known/agents.json.

        Args:
            uri: An AgentUri object

        Returns:
            A tuple containing (AgentDescriptor, resolution_metadata)

        Raises:
            ResolverNotFoundError: If no agent descriptor is found
        """
        metadata: Dict[str, Any] = {"resolution_path": [], "resolution_method": None}

        # Construct base domain URL
        if uri.transport:
            base_url = f"{uri.transport}://{uri.host}"
        else:
            base_url = f"https://{uri.host}"  # Default to HTTPS

        # Check subdomain case first - agent.json at the root
        if uri.path == "" and not ("." in uri.host.split(".")[0]):
            # This is a domain like agent://planner.acme.ai/ - try /agent.json
            agent_json_url = f"{base_url}/agent.json"
            resolution_path = metadata["resolution_path"]
            if isinstance(resolution_path, list):
                resolution_path.append(f"domain_root: {agent_json_url}")

            try:
                descriptor = self._fetch_descriptor(agent_json_url)
                metadata["resolution_method"] = "domain_root"
                metadata["endpoint"] = agent_json_url
                return descriptor, metadata
            except (ResolverError, ResolverNotFoundError):
                # Fall through to try other methods
                pass

        # Try multi-agent case (.well-known/agents.json)
        agents_json_url = f"{base_url}/.well-known/agents.json"
        resolution_path = metadata["resolution_path"]
        if isinstance(resolution_path, list):
            resolution_path.append(f"agents_json: {agents_json_url}")

        try:
            # Fetch agents.json registry
            agents_registry = self._fetch_json(agents_json_url)

            if "agents" in agents_registry and isinstance(
                agents_registry["agents"], dict
            ):
                # Get the agent name from the path
                agent_name = uri.path.split("/")[0] if uri.path else ""

                if agent_name in agents_registry["agents"]:
                    # Get descriptor URL for this agent
                    descriptor_url = agents_registry["agents"][agent_name]
                    resolution_path = metadata["resolution_path"]
                    if isinstance(resolution_path, list):
                        resolution_path.append(f"descriptor: {descriptor_url}")

                    # Fetch the descriptor
                    descriptor = self._fetch_descriptor(descriptor_url)
                    metadata["resolution_method"] = "agents_registry"
                    metadata["registry_url"] = agents_json_url
                    metadata["endpoint"] = descriptor_url
                    return descriptor, metadata
        except (ResolverError, ResolverNotFoundError, KeyError):
            # Fall through to try single agent case
            pass

        # Try single agent case (.well-known/agent.json)
        agent_json_url = f"{base_url}/.well-known/agent.json"
        resolution_path = metadata["resolution_path"]
        if isinstance(resolution_path, list):
            resolution_path.append(f"agent_json: {agent_json_url}")

        try:
            descriptor = self._fetch_descriptor(agent_json_url)
            metadata["resolution_method"] = "well_known"
            metadata["endpoint"] = agent_json_url
            return descriptor, metadata
        except (ResolverError, ResolverNotFoundError):
            # Fall through to path-based resolution
            pass

        # If path is specified, try path-based resolution
        if uri.path:
            path_base = uri.path.split("/")[0]
            path_descriptor_url = f"{base_url}/{path_base}/agent.json"
            resolution_path = metadata["resolution_path"]
            if isinstance(resolution_path, list):
                resolution_path.append(f"path: {path_descriptor_url}")

            try:
                descriptor = self._fetch_descriptor(path_descriptor_url)
                metadata["resolution_method"] = "path_based"
                metadata["endpoint"] = path_descriptor_url
                return descriptor, metadata
            except (ResolverError, ResolverNotFoundError):
                # Fall through to the final error
                pass

        # If we get here, we couldn't resolve
        raise ResolverNotFoundError(
            f"Could not resolve agent descriptor for {uri.to_string()}. "
            f"Tried: {', '.join(metadata['resolution_path'])}"
        )

    def _fetch_json(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse JSON from a URL with caching.

        Args:
            url: The URL to fetch

        Returns:
            Parsed JSON as a dictionary

        Raises:
            ResolverError: For request errors
            ResolverTimeoutError: For timeouts
            ResolverNotFoundError: If the resource is not found
        """
        try:
            response = self.session.get(
                url, timeout=self.timeout, verify=self.verify_ssl
            )

            if response.status_code == 404:
                raise ResolverNotFoundError(f"Resource not found: {url}")

            response.raise_for_status()
            return response.json()

        except Timeout:
            raise ResolverTimeoutError(f"Request timed out: {url}")
        except RequestException as e:
            if e.response and e.response.status_code == 404:
                raise ResolverNotFoundError(f"Resource not found: {url}")
            raise ResolverError(f"Error fetching {url}: {str(e)}")
        except json.JSONDecodeError:
            raise ResolverError(f"Invalid JSON returned from {url}")

    def _fetch_descriptor(self, url: str) -> AgentDescriptor:
        """
        Fetch and parse an agent descriptor from a URL.

        Args:
            url: URL of the agent descriptor

        Returns:
            An AgentDescriptor object

        Raises:
            ResolverError: For parsing errors
            ResolverTimeoutError: For timeouts
            ResolverNotFoundError: If the descriptor is not found
        """
        try:
            json_data = self._fetch_json(url)
            return parse_descriptor(json_data)
        except Exception as e:
            if isinstance(e, (ResolverTimeoutError, ResolverNotFoundError)):
                raise
            raise ResolverError(f"Error parsing descriptor from {url}: {str(e)}")

    def _construct_endpoint_from_transport(self, uri: AgentUri) -> str:
        """
        Construct an endpoint URL from an AgentUri with explicit transport.

        Args:
            uri: An AgentUri object with transport set

        Returns:
            An endpoint URL string
        """
        if not uri.transport:
            raise ValueError("URI must have explicit transport binding")

        # For local transport, handle specially
        if uri.transport == "local":
            return f"local://{uri.host}/{uri.path}"

        # For normal HTTP-based transports
        base = f"{uri.transport}://{uri.host}"

        if uri.path:
            return f"{base}/{uri.path}"

        return base

    def clear_cache(self) -> None:
        """Clear the resolver's cache."""
        self.cache.clear()
