"""
Agent URI Protocol Implementation

A complete suite for addressing and interacting with AI agents using
the agent:// protocol.

Basic usage:
    from agent_uri import AgentUri
    # Parse an agent URI
    uri = AgentUri.parse("agent://example.com/my-agent")
    print(uri.authority)  # "example.com"
    print(uri.path)       # "/my-agent"
"""

__version__ = "0.3.0"
__author__ = "Yaswanth Narvaneni"
__email__ = "yaswanth@gmail.com"

from .client import AgentClient

# Import available exceptions
from .exceptions import AgentServerError, AuthenticationError, CapabilityError

# Import core functionality
from .parser import AgentUri, parse_agent_uri
from .server import FastAPIAgentServer

__all__ = [
    "AgentUri",
    "parse_agent_uri",
    "AgentClient",
    "FastAPIAgentServer",
    "AgentServerError",
    "CapabilityError",
    "AuthenticationError",
]


def get_version():
    """Get the version of the agent-uri package."""
    return __version__
