"""
Agent URI Parser module

This module provides functionality for parsing and manipulating agent:// URIs
as defined in the protocol specification.
"""

from .parser import AgentUri, parse_agent_uri, AgentUriError

__all__ = ["AgentUri", "parse_agent_uri", "AgentUriError"]
