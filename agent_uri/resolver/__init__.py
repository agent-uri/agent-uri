"""
Agent Resolver Package

A package for resolving agent:// URIs to agent descriptors and endpoints.
"""

from .cache import CacheProvider
from .resolver import (
    AgentResolver,
    ResolverError,
    ResolverNotFoundError,
    ResolverTimeoutError,
)

__all__ = [
    "AgentResolver",
    "ResolverError",
    "ResolverTimeoutError",
    "ResolverNotFoundError",
    "CacheProvider",
]
