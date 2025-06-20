"""
Agent URI Parser

Implementation of the agent:// URI parser according to the ABNF specification
in Section 4 of the RFC draft.
"""

import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse


class AgentUriError(Exception):
    """Exception raised for errors in the Agent URI parsing."""

    pass


@dataclass
class AgentUri:
    """
    Represents a parsed agent:// URI according to the protocol specification.

    The AgentUri class provides a structured representation of an agent URI,
    with properties for each component including explicit transport bindings.
    """

    # Core components
    scheme: str = "agent"
    transport: Optional[str] = None
    authority: str = ""
    path: str = ""
    query: Dict[str, Union[str, List[str]]] = field(default_factory=dict)
    fragment: Optional[str] = None

    # Parsed authority components
    userinfo: Optional[str] = None
    host: str = ""
    port: Optional[int] = None

    def __post_init__(self):
        """Initialize default values and handle empty fields."""
        # Ensure query is always a dict
        if not isinstance(self.query, dict):
            object.__setattr__(self, "query", {})

    @property
    def full_scheme(self) -> str:
        """Return the full scheme including optional transport binding."""
        if self.transport:
            return f"agent+{self.transport}"
        return "agent"

    def to_string(self) -> str:
        """Convert the AgentUri object back to a string representation."""
        # Build the authority part
        authority = self.authority
        if not authority and self.host:
            authority = self.host
            if self.port:
                authority = f"{authority}:{self.port}"
            if self.userinfo:
                authority = f"{self.userinfo}@{authority}"

        # Build query string
        query_str = ""
        if self.query:
            params = []
            for key, value in self.query.items():
                if isinstance(value, list):
                    for v in value:
                        # Special handling for '+' character preservation
                        encoded_value = urllib.parse.quote(str(v))
                        if "+" in str(v):
                            encoded_value = encoded_value.replace("%2B", "+")
                        params.append(f"{urllib.parse.quote(key)}={encoded_value}")
                else:
                    # Special handling for '+' character preservation
                    encoded_value = urllib.parse.quote(str(value))
                    if "+" in str(value):
                        encoded_value = encoded_value.replace("%2B", "+")
                    params.append(f"{urllib.parse.quote(key)}={encoded_value}")
            if params:
                query_str = "&".join(params)

        # Build the full URI
        uri = f"{self.full_scheme}://{authority}"

        if self.path:
            # Make sure path starts with a slash if not empty
            if not self.path.startswith("/"):
                uri += f"/{self.path}"
            else:
                uri += self.path

        if query_str:
            uri += f"?{query_str}"

        if self.fragment:
            uri += f"#{self.fragment}"

        return uri

    def __str__(self) -> str:
        """String representation is the full URI."""
        return self.to_string()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the AgentUri to a dictionary representation."""
        return {
            "scheme": self.scheme,
            "transport": self.transport,
            "authority": self.authority,
            "userinfo": self.userinfo,
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "query": self.query,
            "fragment": self.fragment,
            "full_uri": self.to_string(),
        }

    @classmethod
    def parse(cls, uri: str) -> "AgentUri":
        """Parse an agent:// URI string into an AgentUri object.

        This is a convenience class method that calls the parse_agent_uri function.

        Args:
            uri: The agent URI string to parse

        Returns:
            AgentUri: Object representing the parsed URI

        Raises:
            AgentUriError: If the URI doesn't follow the agent:// scheme format
        """
        return parse_agent_uri(uri)


def parse_agent_uri(uri: str) -> AgentUri:
    """
    Parse an agent:// URI according to the protocol specification.

    This function parses URIs with the agent:// scheme and optional transport
    bindings (agent+<protocol>://). It extracts all components according to
    the ABNF specification in Section 4 of the RFC draft.

    Args:
        uri: The agent URI string to parse

    Returns:
        AgentUri: Object representing the parsed URI

    Raises:
        AgentUriError: If the URI doesn't follow the agent:// scheme format
    """
    # Check if the URI has the agent scheme
    if not uri.startswith("agent"):
        raise AgentUriError(f"URI must start with 'agent': {uri}")

    # Extract transport binding if present
    transport = None
    scheme_regex = r"^agent(\+([a-zA-Z0-9\-]+))?://"
    match = re.match(scheme_regex, uri)

    if not match:
        raise AgentUriError(f"Invalid agent URI format: {uri}")

    # Extract the transport protocol if it exists
    if match.group(1):  # This captures the "+transport" part
        transport = match.group(2)  # This captures just the "transport" part
        # Validate transport protocol - only allow certain protocols
        valid_protocols = ["https", "http", "wss", "ws", "local", "unix", "matrix"]
        if transport not in valid_protocols:
            raise AgentUriError(f"Invalid transport protocol: {transport}")

    # Replace the scheme with 'http' temporarily to use urllib.parse
    # This is because urllib.parse doesn't support custom schemes as well
    normalized_uri = re.sub(r"^agent(\+[a-zA-Z0-9\-]+)?://", "http://", uri)

    # Parse the normalized URI
    parsed = urlparse(normalized_uri)

    # Special handling for agent:///planning case (missing authority)
    if not parsed.netloc and parsed.path:
        raise AgentUriError("Missing authority in agent URI")

    # Extract query parameters
    query_params: Dict[str, Union[str, List[str]]] = {}
    if parsed.query:
        # Split the query string manually to preserve '+' characters
        # which parse_qs would decode to spaces
        for param in parsed.query.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                key = urllib.parse.unquote(key)
                # Don't decode '+' to space for 'q=hello+world' case
                if "+" in value and "%2B" not in param:
                    value = urllib.parse.unquote(value.replace("+", "%2B"))
                else:
                    value = urllib.parse.unquote(value)

                if key in query_params:
                    existing_value = query_params[key]
                    if isinstance(existing_value, list):
                        existing_value.append(value)
                    else:
                        query_params[key] = [str(existing_value), value]
                else:
                    query_params[key] = value

    # Extract userinfo, host, and port from netloc
    userinfo = None
    host = ""
    port = None

    # Special handling for DID URIs which have multiple colons
    if parsed.netloc.startswith("did:"):
        # For DID URIs, keep the entire netloc as the host
        host = parsed.netloc
    else:
        # Normal handling for standard netloc format
        host = parsed.hostname or ""
        port = parsed.port

    if "@" in parsed.netloc:
        userinfo_part, _ = parsed.netloc.split("@", 1)
        userinfo = userinfo_part

    # Create and return AgentUri object
    return AgentUri(
        scheme="agent",
        transport=transport,
        authority=parsed.netloc,
        path=parsed.path.lstrip("/"),  # Remove leading slash for consistency
        query=query_params if query_params else {},
        fragment=parsed.fragment or None,
        userinfo=userinfo,
        host=host,
        port=port,
    )


def is_valid_agent_uri(uri: str) -> bool:
    """
    Check if a string is a valid agent:// URI.

    Args:
        uri: The URI string to validate

    Returns:
        bool: True if the URI is a valid agent URI, False otherwise
    """
    try:
        parse_agent_uri(uri)
        return True
    except AgentUriError:
        return False
