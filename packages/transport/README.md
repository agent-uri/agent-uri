# Agent URI Transport Binding Layer

Transport binding layer for the `agent://` protocol, providing adapters for different transport protocols (HTTPS, WebSocket, Local).

## Overview

This package implements the transport binding layer for the Agent URI protocol as defined in the [RFC draft](../../docs/rfc/draft.md). It provides a pluggable architecture for supporting different transport protocols and a consistent interface for interacting with agents regardless of the underlying transport mechanism.

## Features

- Abstract transport interface for consistent agent invocation
- Support for multiple transport protocols:
  - HTTPS (`agent+https://`)
  - WebSocket (`agent+wss://`)
  - Local IPC (`agent+local://`)
- Pluggable architecture for custom transports
- Support for both synchronous and streaming interactions
- Compatible with the Agent URI resolution framework

## Installation

```bash
pip install agent-transport
```

## Basic Usage

```python
from agent_transport.registry import default_registry
from agent_transport.transports.https import HttpsTransport
from agent_transport.transports.websocket import WebSocketTransport
from agent_transport.transports.local import LocalTransport

# Register transports
default_registry.register_transport(HttpsTransport)
default_registry.register_transport(WebSocketTransport)
default_registry.register_transport(LocalTransport)

# Get the appropriate transport for a protocol
https_transport = default_registry.get_transport("https")

# Invoke an agent capability
response = https_transport.invoke(
    endpoint="https://planner.acme.ai",
    capability="generate-itinerary",
    params={"city": "Paris"},
    headers={"Authorization": "Bearer token"}
)

# Stream responses from an agent
for chunk in https_transport.stream(
    endpoint="wss://planner.acme.ai",
    capability="generate-itinerary-stream",
    params={"city": "Paris"}
):
    print(chunk)
```

## Working with Local Agents

The local transport allows communication with agents running in the same environment:

```python
from agent_transport.transports.local import LocalTransport

# Create a local transport
local_transport = LocalTransport()

# Register a local agent
def handle_capability(capability, params):
    if capability == "hello":
        return f"Hello, {params.get('name', 'World')}!"
    return {"error": "Unknown capability"}

local_transport.register_agent("my-agent", handle_capability)

# Invoke the local agent
response = local_transport.invoke(
    endpoint="agent+local://my-agent",
    capability="hello",
    params={"name": "Alice"}
)
```

## Integration with Agent URI

```python
from agent_uri.parser import parse_agent_uri
from agent_resolver.resolver import AgentResolver
from agent_transport.registry import default_registry

# Create objects
resolver = AgentResolver()
default_registry.register_transport(HttpsTransport)

# Parse an agent URI
uri = parse_agent_uri("agent://planner.acme.ai/generate-itinerary?city=Paris")

# Resolve the URI to get the endpoint
descriptor, metadata = resolver.resolve(uri)
endpoint = metadata.get("endpoint")

# Get the appropriate transport
transport = default_registry.get_transport(uri.transport or "agent")

# Invoke the agent
response = transport.invoke(
    endpoint=endpoint,
    capability=uri.path,
    params=uri.query
)
```

## Custom Transport Implementation

To implement a custom transport, extend the `AgentTransport` base class:

```python
from agent_transport.base import AgentTransport

class CustomTransport(AgentTransport):
    @property
    def protocol(self) -> str:
        return "custom"
    
    def invoke(self, endpoint, capability, params=None, headers=None, timeout=None, **kwargs):
        # Custom implementation
        pass
    
    def stream(self, endpoint, capability, params=None, headers=None, timeout=None, **kwargs):
        # Custom implementation
        yield "Streaming data..."

# Register the custom transport
default_registry.register_transport(CustomTransport)
```

## License

MIT License
