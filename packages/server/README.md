# Agent Server SDK for the `agent://` Protocol

A server-side SDK for implementing agents that conform to the `agent://` protocol.

## Overview

This package provides utilities and framework components for creating server-side agent implementations that conform to the `agent://` protocol. It includes tools for:

- Creating and registering agent capabilities
- Generating agent.json descriptors
- Handling requests across different transports (HTTP, WebSocket)
- Managing capability registrations
- Validating input/output schemas
- Supporting stateful interactions

## Installation

```bash
pip install agent-server
```

Or install from source:

```bash
git clone https://github.com/username/agent-uri.git
cd agent-uri/packages/server
pip install -e .
```

## Dependencies

The SDK has the following core dependencies:

- Python 3.8+
- agent-uri-parser
- agent-descriptor
- agent-resolver
- agent-transport

For the FastAPI implementation, additional dependencies are required:

- fastapi
- uvicorn
- pydantic

## Quick Start

Here's a minimal example of creating an agent server:

```python
import asyncio
from agent_server import capability, FastAPIAgentServer

# Define a capability using the decorator
@capability(
    name="echo",
    description="Echoes back the input text",
    version="1.0.0",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"}
        },
        "required": ["text"]
    }
)
async def echo(text: str):
    return {"text": text}

# Create and configure the server
server = FastAPIAgentServer(
    name="example-agent",
    version="1.0.0",
    description="An example agent server"
)

# Register the capability
server.register_capability("echo", echo._capability)

# Run the server
import uvicorn
uvicorn.run(server.app, host="0.0.0.0", port=8000)
```

## Core Components

### Capability

The `Capability` class represents a function or method that can be invoked via the `agent://` protocol. It includes metadata for discovery and documentation.

```python
from agent_server import Capability

# Create a capability manually
capability = Capability(
    func=my_function,
    name="my-capability",
    description="Description of what it does",
    version="1.0.0",
    tags=["category1", "category2"],
    input_schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "number"}
        },
        "required": ["param1"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "result": {"type": "string"}
        }
    },
    is_deterministic=False,
    memory_enabled=True,
    streaming=False
)
```

### Capability Decorator

The `capability` decorator provides a convenient way to define capabilities:

```python
from agent_server import capability

@capability(
    name="generate-text",
    description="Generates text based on a prompt",
    version="1.0.0",
    tags=["text", "generation"],
    input_schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "max_tokens": {"type": "integer", "default": 100}
        },
        "required": ["prompt"]
    },
    streaming=True
)
async def generate_text(prompt: str, max_tokens: int = 100):
    # Implementation
    yield {"text": "Generated text..."}
```

### Agent Server

The package provides two main server implementations:

1. `AgentServer` (abstract base class)
2. `FastAPIAgentServer` (concrete implementation using FastAPI)

```python
from agent_server import FastAPIAgentServer

# Create a server
server = FastAPIAgentServer(
    name="my-agent",
    version="1.0.0",
    description="My agent description",
    provider={"organization": "My Company"},
    documentation_url="https://docs.example.com",
    interaction_model="request-response",
    auth_schemes=["ApiKey"],
    server_url="https://agent.example.com",
    enable_cors=True,
    enable_docs=True
)

# Register capabilities
server.register_capability("echo", echo_capability)
server.register_capability("generate", generate_capability)

# Register all capabilities from a module
server.register_capabilities_from_module(my_module)

# Register an authenticator
server.register_authenticator(my_auth_function)

# Get or save the agent descriptor
descriptor = server.get_agent_descriptor()
server.save_agent_descriptor("./agent.json")
```

## Handlers

The SDK includes handlers for different transport protocols:

- `HTTPHandler`: Handles HTTP requests
- `WebSocketHandler`: Handles WebSocket connections

These are automatically configured when using `FastAPIAgentServer`.

## Authentication

You can implement custom authentication by registering an authenticator function:

```python
def authenticate_request(request_data):
    # Check headers, API key, JWT, etc.
    headers = request_data.get("headers", {})
    api_key = headers.get("X-API-Key")
    
    # Return True if authenticated, False otherwise
    return api_key == "valid-api-key"

# Register the authenticator
server.register_authenticator(authenticate_request)
```

## Streaming Responses

To support streaming responses, set `streaming=True` in the capability decorator and return an async generator:

```python
@capability(
    name="stream-countdown",
    description="Streams a countdown from the given number",
    streaming=True
)
async def stream_countdown(start: int, delay: float = 0.5):
    for i in range(start, 0, -1):
        yield {"count": i}
        await asyncio.sleep(delay)
    
    yield {"count": 0, "message": "Countdown complete!"}
```

## Stateful Interactions

To enable stateful interactions, set `memory_enabled=True` in the capability:

```python
@capability(
    name="chat",
    description="Chat with the agent",
    memory_enabled=True
)
async def chat(message: str, context=None, session_id=None):
    # Access previous context if available
    history = context.get("history", []) if context else []
    
    # Add current message to history
    history.append({"role": "user", "content": message})
    
    # Agent response
    response = "This is a response based on your message: " + message
    history.append({"role": "agent", "content": response})
    
    # Return response with updated context
    return {
        "response": response,
        "context": {
            "history": history
        }
    }
```

## Complete Example

See `example_usage.py` for a complete example of using the agent-server SDK.

## License

[License details]
