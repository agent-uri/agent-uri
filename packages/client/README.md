# Agent Client SDK

A Python client SDK for interacting with agents using the `agent://` protocol.

## Overview

The Agent Client SDK provides a simple interface for invoking agent capabilities using the agent:// protocol. It integrates URI parsing, descriptor handling, resolution, and transport binding into a unified API.

Key features:

- Simple client interface for invoking agent capabilities
- Support for multiple transport protocols (HTTPS, WebSocket, local)
- Session management for stateful interactions
- Authentication support (API keys, bearer tokens, etc.)
- Automatic resolution of agent URIs to endpoints
- Streaming support for real-time data

## Installation

```bash
# From PyPI (once published)
pip install agent-client

# From source
cd agent-uri/packages/client
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

## Usage

### Basic Invocation

```python
from agent_client import AgentClient

# Create a client
client = AgentClient()

# Invoke a capability
response = client.invoke(
    uri="agent://planner.acme.ai/generate-itinerary",
    params={"city": "Paris"}
)

print(response)
```

### Authentication

```python
from agent_client import AgentClient, BearerTokenAuth, ApiKeyAuth

# API key authentication
api_key_auth = ApiKeyAuth(
    api_key="your-api-key",
    header_name="X-API-Key"  # Optional, defaults to "X-API-Key"
)

# Bearer token authentication
bearer_auth = BearerTokenAuth(
    token="your-token",
    token_type="Bearer",  # Optional, defaults to "Bearer"
    # For JWT tokens, expiration is automatically extracted if possible
    expires_at=1682456789,  # Optional UNIX timestamp
    refresh_callback=lambda: get_new_token()  # Optional refresh callback
)

# Create client with authentication
client = AgentClient(auth_provider=api_key_auth)

# Invoke a capability that requires authentication
response = client.invoke(
    uri="agent://secure.acme.ai/protected-capability",
    params={"param": "value"}
)
```

### Streaming

```python
from agent_client import AgentClient

client = AgentClient()

# Stream from a capability
for chunk in client.stream(
    uri="agent+wss://realtime.acme.ai/streaming-capability",
    params={"param": "value"},
    stream_format="ndjson"  # Optional format: "ndjson", "sse", or "raw"
):
    print(f"Received chunk: {chunk}")
```

### Sessions

```python
from agent_client import AgentClient

client = AgentClient()

# Create a session for stateful interactions
session = client.create_session(
    uri="agent://chat.acme.ai",
    session_id="user-123"  # Optional, generated if not provided
)

# First interaction
response1 = session.invoke(
    capability="ask",
    params={"message": "Hello, who are you?"}
)

# Second interaction (maintains session context)
response2 = session.invoke(
    capability="ask",
    params={"message": "What did I just ask you?"}
)
```

### Explicit Transport Binding

```python
from agent_client import AgentClient

client = AgentClient()

# HTTPS transport
https_response = client.invoke(
    uri="agent+https://example.com/capability"
)

# WebSocket transport
for chunk in client.stream(
    uri="agent+wss://example.com/streaming-capability"
):
    print(chunk)

# Local transport (for agents running in the same process)
local_response = client.invoke(
    uri="agent+local://local-agent/capability"
)
```

## Error Handling

```python
from agent_client import AgentClient
from agent_client.exceptions import (
    ResolutionError, InvocationError, StreamingError, AuthenticationError
)

client = AgentClient()

try:
    response = client.invoke(uri="agent://example.com/capability")
except ResolutionError as e:
    print(f"Could not resolve the agent URI: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except InvocationError as e:
    print(f"Capability invocation failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run tests: `pytest agent_client/tests/`
5. Submit a pull request

## License

This project is licensed under the MIT License.
