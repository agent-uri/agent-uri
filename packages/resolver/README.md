# Agent URI Resolver

A resolution framework for agent:// URIs that can discover agent endpoints by fetching and parsing `.well-known/agent.json` or `.well-known/agents.json` files.

## Overview

The Agent URI Resolver is a reference implementation of the resolution framework described in the [agent:// protocol specification](../../docs/rfc/draft.md). It provides functionality to:

- Resolve agent:// URIs to their agent descriptors
- Discover agent endpoints through well-known files
- Support HTTP caching headers for efficient resolution
- Provide fallback mechanisms when resolution fails

## Installation

### Installation from PyPI (Coming Soon)

```bash
pip install agent-resolver
```

### Development Installation

To install the package for development:

1. First install the required dependencies:

```bash
# From the agent-uri/packages/resolver directory
pip install -r requirements.txt
```

2. Install the local dependencies (if you're working within the monorepo):

```bash
# From the agent-uri/packages directory
pip install -e uri-parser
pip install -e descriptor
```

3. Install this package in development mode:

```bash
# From the agent-uri/packages/resolver directory
pip install -e .
```

## Usage

### Basic Usage

```python
from agent_resolver import AgentResolver
from agent_uri.parser import parse_agent_uri

# Create a resolver with default caching
resolver = AgentResolver()

# Resolve an agent URI
uri = "agent://planner.acme.ai/generate-itinerary"
descriptor, metadata = resolver.resolve(uri)

# Access agent information from the descriptor
print(f"Agent name: {descriptor.name}")
print(f"Agent version: {descriptor.version}")
print(f"Available capabilities: {[c.name for c in descriptor.capabilities]}")

# Access resolution metadata
print(f"Resolution method: {metadata['resolution_method']}")
print(f"Endpoint: {metadata['endpoint']}")
```

### Custom Caching

The resolver uses `requests-cache` for HTTP caching:

```python
from agent_resolver import AgentResolver, CacheProvider

# Create a custom cache with SQLite backend
cache = CacheProvider(
    cache_name="my_agent_resolver_cache",
    backend="sqlite",
    expire_after=3600  # Cache TTL in seconds
)

# Create resolver with custom cache
resolver = AgentResolver(cache_provider=cache)
```

### Resolution Process

The resolver attempts multiple methods to find an agent descriptor:

1. If the URI represents a specific subdomain agent (e.g., `agent://planner.acme.ai/`), check `/agent.json`
2. Try to find a multi-agent registry at `/.well-known/agents.json`
3. Look for a single agent descriptor at `/.well-known/agent.json`
4. If the URI has a path, try path-based resolution at `/<path>/agent.json`
5. If all else fails but transport is explicitly specified, fallback to direct endpoint construction

All HTTP requests support standard caching mechanisms including `ETag`, `Last-Modified`, and `Cache-Control` headers.

## Examples

### Resolving a Multi-Agent Domain

```python
# URI for a specific agent in a multi-agent domain
uri = "agent://acme.ai/planner/generate-itinerary"

# The resolver will:
# 1. Try to fetch https://acme.ai/.well-known/agents.json
# 2. Look for the "planner" agent in the registry
# 3. Fetch the descriptor from the URL in the registry
# 4. Return the descriptor and resolution metadata
descriptor, metadata = resolver.resolve(uri)
```

### Explicit Transport Binding

```python
# URI with explicit transport binding
uri = "agent+wss://realtime.acme.ai/chat"

# The resolver will recognize the explicit WebSocket transport
# Even if no descriptor is found, it can construct an endpoint
_, metadata = resolver.resolve(uri)
endpoint = metadata['endpoint']  # "wss://realtime.acme.ai/chat"
```

### Caching Behavior

The resolver automatically handles HTTP caching:

```python
# First request fetches from network
descriptor1, _ = resolver.resolve("agent://planner.acme.ai/")

# Subsequent requests may use cached data if not expired
descriptor2, _ = resolver.resolve("agent://planner.acme.ai/")

# Clear cache if needed
resolver.clear_cache()
```

## Error Handling

The resolver provides specific exception types for different error scenarios:

```python
from agent_resolver import AgentResolver, ResolverError, ResolverNotFoundError, ResolverTimeoutError

resolver = AgentResolver()

try:
    descriptor, metadata = resolver.resolve("agent://nonexistent.example.com/")
except ResolverNotFoundError:
    print("Agent not found")
except ResolverTimeoutError:
    print("Resolution timed out")
except ResolverError as e:
    print(f"Resolution error: {e}")
```

## License

MIT
