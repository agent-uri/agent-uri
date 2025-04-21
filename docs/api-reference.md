# Agent URI Reference Implementation: API Reference

This document provides a detailed reference for the primary APIs in the current Agent URI reference implementation.

## Table of Contents

- [URI Parser](#uri-parser)
- [Descriptor Handler](#descriptor-handler)
- [Resolution Framework](#resolution-framework)
- [Transport Layer](#transport-layer)
- [Client SDK](#client-sdk)
- [Server SDK](#server-sdk)
- [Error Handling](#error-handling)

## URI Parser

The URI Parser package (`packages/uri-parser`) provides functionality for parsing, validating, and manipulating agent:// URIs.

### AgentUri Class

```python
from agent_uri.agent_uri.parser import AgentUri

# Create from string
uri = AgentUri('agent://planner.example.com/generate-itinerary?city=Paris')

# Access components
print(uri.protocol)     # 'agent'
print(uri.authority)    # 'planner.example.com'
print(uri.path)         # '/generate-itinerary'
print(uri.params)       # {'city': 'Paris'}
print(uri.fragment)     # None

# Modify components
uri.params['days'] = 3
print(uri.to_string())  # 'agent://planner.example.com/generate-itinerary?city=Paris&days=3'
```

### Methods

#### `__init__(uriString: str)`
Constructor that parses a string URI into an AgentUri object.

```python
uri = AgentUri('agent://example.com/capability')
```

#### `protocol: str`
Property that returns the protocol part of the URI (e.g., 'agent', 'agent+https').

#### `authority: str`
Property that returns the authority part of the URI (e.g., 'example.com').

#### `path: str`
Property that returns the path part of the URI (e.g., '/capability').

#### `params: dict`
Property that returns the query parameters as a dictionary.

#### `fragment: str`
Property that returns the fragment part of the URI, if present.

#### `to_string(): str`
Serializes the URI object back to string form.

```python
uri_string = uri.to_string()
```

## Descriptor Handler

The Descriptor Handler package (`packages/descriptor`) provides functionality for working with agent descriptors (agent.json files).

### AgentDescriptor Class

```python
from agent_descriptor.agent_descriptor.models import AgentDescriptor, Capability
import json

# Parse descriptor from JSON
descriptor_json = '{"name": "test-agent", "version": "1.0.0", "capabilities": [...]}'
descriptor = AgentDescriptor.from_json(descriptor_json)

# Access descriptor properties
print(descriptor.name)         # 'test-agent'
print(descriptor.version)      # '1.0.0'
print(descriptor.capabilities) # List of capability objects

# Create a new descriptor
new_desc = AgentDescriptor(
    name="my-agent",
    version="1.0.0",
    description="A sample agent",
    capabilities=[
        Capability(
            name="echo",
            description="Echoes back the input"
        )
    ]
)

# Serialize to JSON
json_output = new_desc.to_json()
```

### Methods

#### `from_json(json_data: str | dict) -> AgentDescriptor`
Static method that parses a JSON string or dictionary into an AgentDescriptor.

```python
descriptor = AgentDescriptor.from_json(json_string)
```

#### `to_json() -> str`
Serializes the descriptor to a JSON string.

```python
json_output = descriptor.to_json()
```

#### `get_capability(name: str) -> Capability | None`
Gets a capability by name.

```python
capability = descriptor.get_capability('echo')
if capability:
    print(capability.description)
```

### Capability Class

```python
from agent_descriptor.agent_descriptor.models import Capability

# Create a capability
capability = Capability(
    name="echo",
    description="Echoes back the input",
    requires_auth=False
)

# Check properties
print(capability.name)          # 'echo'
print(capability.description)   # 'Echoes back the input'
print(capability.requires_auth) # False
```

## Resolution Framework

The Resolution Framework (`packages/resolver`) provides functionality for resolving agent:// URIs to concrete endpoints.

### Resolver Class

```python
from agent_resolver.agent_resolver.resolver import Resolver
from agent_uri.agent_uri.parser import AgentUri

# Create a resolver
resolver = Resolver()

# Resolve a URI to an endpoint
uri = AgentUri('agent://example.com/capability')
result = await resolver.resolve(uri)

print(result.endpoint)       # 'https://example.com/api'
print(result.transport_type) # 'https'
print(result.descriptor)     # AgentDescriptor object
```

### Methods

#### `resolve(uri: AgentUri) -> ResolutionResult`
Resolves an agent URI to an endpoint and metadata.

```python
result = await resolver.resolve(uri)
```

#### `clear_cache()`
Clears the resolution cache.

```python
resolver.clear_cache()
```

### ResolutionResult Class

```python
from agent_resolver import ResolutionResult

# Resolution result properties
print(result.endpoint)       # The endpoint URL
print(result.transport_type) # Transport type (e.g., 'https', 'wss')
print(result.descriptor)     # AgentDescriptor object if available
```

## Transport Layer

The Transport Layer (`packages/transport`) provides implementations for different transport protocols.

### TransportRegistry

```python
from agent_transport.registry import TransportRegistry
from agent_transport.transports.https import HttpsTransport
from agent_transport.transports.websocket import WebSocketTransport
from agent_transport.transports.local import LocalTransport

# Get the registry instance
registry = TransportRegistry.get_instance()

# Register built-in transports
registry.register('https', HttpsTransport)
registry.register('wss', WebSocketTransport)
registry.register('local', LocalTransport)

# Get a transport
https_transport = registry.get('https')

# Create transport instance with configuration
transport = registry.create('https', {
    'timeout': 10000
})
```

### Transport Interface

All transport implementations follow this interface:

```python
from typing import Any, Dict, AsyncIterator, Optional

class Transport:
    """Interface for all transport implementations"""
    
    async def send(self, endpoint: str, capability: str, 
                  params: Any, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a request to an agent"""
        pass
    
    async def stream(self, endpoint: str, capability: str,
                    params: Any, options: Optional[Dict[str, Any]] = None) -> AsyncIterator[Dict[str, Any]]:
        """Stream a request to an agent"""
        pass
    
    async def close(self) -> None:
        """Close the transport (e.g., WebSocket connections)"""
        pass
```

### HttpsTransport

```python
from agent_transport.transports.https import HttpsTransport

# Create an HTTPS transport
transport = HttpsTransport({
    'timeout': 30000,
    'headers': {
        'X-API-Key': 'your-api-key'
    }
})

# Send a request
response = await transport.send(
    'https://example.com',
    'capability-name',
    {'param1': 'value1'},
    {'response_type': 'json'}
)
```

### WebSocketTransport

```python
from agent_transport.transports.websocket import WebSocketTransport

# Create a WebSocket transport
transport = WebSocketTransport()

# Stream responses
stream = transport.stream(
    'wss://example.com',
    'generate-text',
    {'prompt': 'Once upon a time'}
)

async for chunk in stream:
    print('Received chunk:', chunk)

# Close when done
await transport.close()
```

### LocalTransport

```python
from agent_transport.transports.local import LocalTransport

# Create a local transport
transport = LocalTransport()

# Send a local request (no network)
response = await transport.send(
    'local://agent-id',
    'capability-name',
    {'param1': 'value1'}
)
```

## Client SDK

The Client SDK (`packages/client`) provides a high-level API for invoking agent capabilities.

### AgentClient Class

```python
from agent_client.agent_client.client import AgentClient
from agent_client.agent_client.auth import BearerTokenAuth

# Create a client with default options
client = AgentClient()

# Create a client with authentication
auth = BearerTokenAuth(token="your-api-key")
client_with_auth = AgentClient(auth=auth)

# Invoke an agent capability by URI
result = await client.invoke(
    'agent://example.com/capability?param=value'
)

# Invoke with separate parameters
result = await client.invoke(
    'agent://example.com/capability',
    {'param1': 'value1', 'param2': 'value2'}
)

# Stream responses
stream = await client.stream(
    'agent+wss://example.com/streaming-capability',
    {'prompt': 'Generate some text'}
)

async for chunk in stream:
    print(chunk)
```

### Methods

#### `__init__(auth=None, transports=None, timeout=None)`
Constructor for creating an AgentClient.

```python
client = AgentClient(
    auth=auth_provider,
    transports={
        "https": {"timeout": 10000},
        "wss": {"reconnect": True}
    },
    timeout=30000
)
```

#### `invoke(uri: str | AgentUri, params=None, options=None) -> dict`
Invokes an agent capability and returns the result.

```python
result = await client.invoke(uri, params, options)
```

#### `stream(uri: str | AgentUri, params=None, options=None) -> AsyncIterator`
Streams responses from an agent capability.

```python
stream = await client.stream(uri, params, options)
async for chunk in stream:
    # Process chunk
    pass
```

### Authentication

```python
from agent_client.agent_client.auth import BearerTokenAuth

# Create a bearer token auth provider
auth = BearerTokenAuth(
    token='your-token-here'
)

# Use with client
client = AgentClient(auth=auth)
```

## Server SDK

The Server SDK (`packages/server`) provides a framework for implementing agent:// compatible services.

### AgentServer Class

```python
from agent_server.agent_server.server import AgentServer
import asyncio

# Create a new agent server
server = AgentServer(
    name='example-agent',
    version='1.0.0',
    description='An example agent server'
)

# Register a capability
async def echo_handler(params):
    return {'message': params.get('message', 'No message provided')}

server.capability(
    'echo',
    description='Echoes back the input',
    handler=echo_handler
)

# Register a streaming capability
async def generate_text_handler(params):
    prompt = params.get('prompt', '')
    for word in prompt.split():
        yield {'text': word + ' '}
        await asyncio.sleep(0.1)

server.capability(
    'generate-text',
    description='Generates text from a prompt',
    streaming=True,
    handler=generate_text_handler
)

# Start the server with HTTP and WebSocket transports
await server.listen({
    'http': {'port': 3000},
    'websocket': {'port': 3001}
})
```

### Methods

#### `__init__(name, version, description=None, auth=None)`
Constructor for creating an AgentServer.

```python
server = AgentServer(
    name='example-agent',
    version='1.0.0',
    description='An example agent server'
)
```

#### `capability(name, description=None, handler=None, streaming=False, requires_auth=False)`
Registers a capability with the server.

```python
server.capability(
    'capability-name',
    description='Capability description',
    handler=async_handler_function,
    streaming=False,
    requires_auth=False
)
```

#### `listen(options) -> None`
Starts the server with the specified transport bindings.

```python
await server.listen({
    'http': {'port': 3000},
    'websocket': {'port': 3001}
})
```

## Error Handling

The Common package (`packages/common`) provides error handling utilities.

### AgentError Class

```python
from agent_common.error.models import AgentError

# Create an error
error = AgentError(
    code="RESOLVER_ERROR",
    message="Failed to resolve agent",
    details={"uri": "agent://example.com"}
)

# Access error properties
print(error.code)     # "RESOLVER_ERROR"
print(error.message)  # "Failed to resolve agent"
print(error.details)  # {"uri": "agent://example.com"}
```

### Exception Handling

```python
from agent_client import AgentClient
from agent_common.error.models import AgentError

client = AgentClient()

try:
    result = await client.invoke('agent://example.com/capability')
except AgentError as error:
    print(f"Error code: {error.code}")
    print(f"Error message: {error.message}")
    print(f"Error details: {error.details}")
except Exception as error:
    print(f"Unexpected error: {error}")
```

## Future Enhancements

For information on planned enhancements and features not yet implemented, see the [TODO.md](../TODO.md) file.
