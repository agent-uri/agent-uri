# Agent URI Reference Implementation: Examples

This document provides practical examples of using the current Agent URI reference implementation.

## Table of Contents

1. [Basic Examples](#basic-examples)
2. [Transport Examples](#transport-examples)
3. [Echo Agent Example](#echo-agent-example)

## Basic Examples

### Invoking an Agent with HTTP Transport

```python
from agent_client.agent_client.client import AgentClient
import asyncio

async def main():
    # Create a new client
    client = AgentClient()
    
    try:
        # Invoke an agent with query parameters
        result = await client.invoke(
            'agent://echo.example.com/echo?message=Hello%20World'
        )
        
        print('Response:', result)
    except Exception as error:
        print('Error invoking agent:', error)

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
```

### Creating a Simple Agent Server

```python
from agent_server.agent_server.server import AgentServer
import asyncio

async def main():
    # Create a new agent server
    server = AgentServer(
        name="simple-agent",
        version="1.0.0",
        description="A simple example agent"
    )
    
    # Register an echo capability
    async def echo_handler(params):
        return {"message": params.get("message") or "No message provided"}
    
    server.capability(
        "echo",
        description="Echoes back the input",
        handler=echo_handler
    )
    
    # Start the server on port 3000
    await server.listen(
        http={"port": 3000}
    )
    
    print("Agent server running at http://localhost:3000")
    print("Agent URI: agent+https://localhost:3000/echo")

if __name__ == "__main__":
    asyncio.run(main())
```

### Parsing Agent URIs

```python
from agent_uri.agent_uri.parser import AgentUri

# Parse an existing URI
uri = AgentUri('agent://translator.example.com/translate?text=Hello')

# Access components
print(uri.protocol)  # 'agent'
print(uri.authority)  # 'translator.example.com'
print(uri.path)       # '/translate'
print(uri.params)     # {'text': 'Hello'}
print(uri.fragment)   # None

# Modify parameters
uri.params['targetLang'] = 'fr'
print(uri.to_string())  # 'agent://translator.example.com/translate?text=Hello&targetLang=fr'
```

### Basic Agent Resolution

```python
from agent_resolver.agent_resolver.resolver import Resolver
from agent_uri.agent_uri.parser import AgentUri
import asyncio

async def resolve_agent(uri_string: str):
    resolver = Resolver()
    uri = AgentUri(uri_string)
    
    try:
        result = await resolver.resolve(uri)
        
        print('Endpoint:', result.endpoint)
        print('Transport Type:', result.transport_type)
        if result.descriptor:
            print('Agent Name:', result.descriptor.name)
            print('Agent Version:', result.descriptor.version)
            print('Capabilities:', ', '.join(c.name for c in result.descriptor.capabilities))
        
        return result
    except Exception as error:
        print('Resolution failed:', error)
        raise

if __name__ == "__main__":
    asyncio.run(resolve_agent('agent://echo.example.com'))
```

## Transport Examples

### Streaming Responses with WebSockets

```python
from agent_client.agent_client.client import AgentClient
import asyncio
import sys

async def stream_from_agent():
    client = AgentClient()
    
    try:
        # Stream content from an agent using WebSockets
        stream = await client.stream(
            'agent+wss://stream.example.com/generate',
            {'prompt': 'Write a short story about a robot learning to paint'}
        )
        
        # Process the stream chunks as they arrive
        async for chunk in stream:
            # For WebSockets, chunks typically come as partial text fragments
            if 'text' in chunk:
                sys.stdout.write(chunk['text'])
                sys.stdout.flush()
        
        print('\nStream complete')
    except Exception as error:
        print('Stream failed:', error)

if __name__ == "__main__":
    asyncio.run(stream_from_agent())
```

### Creating a Streaming Agent with WebSockets

```python
from agent_server.agent_server.server import AgentServer
import asyncio
import time

async def main():
    server = AgentServer(
        name="streaming-agent",
        version="1.0.0",
        description="An agent that streams responses"
    )
    
    # Register a streaming capability
    async def generate_text_handler(params):
        prompt = params.get('prompt', 'Default story')
        words = prompt.split(' ')
        
        # Simulate generating text word by word
        for word in words:
            yield {"text": word + " "}
            # Simulate thinking time
            await asyncio.sleep(0.2)
        
        yield {"text": "\nGeneration complete!"}
    
    server.capability(
        "generate-text",
        description="Generates text from a prompt",
        streaming=True,
        handler=generate_text_handler
    )
    
    # Start server with both HTTP and WebSocket transports
    await server.listen(
        http={"port": 3000},
        websocket={"port": 3001}
    )
    
    print('Agent server running:')
    print('- HTTP: http://localhost:3000')
    print('- WebSocket: ws://localhost:3001')
    print('Agent URI: agent+wss://localhost:3001/generate-text')

if __name__ == "__main__":
    asyncio.run(main())
```

### Authentication with Bearer Tokens

```python
from agent_client.agent_client.client import AgentClient
from agent_client.agent_client.auth import BearerTokenAuth
import asyncio

async def invoke_secure_agent():
    # Create an authentication provider
    auth = BearerTokenAuth(
        token="your-api-key-or-token"
    )
    
    # Create a client with authentication
    client = AgentClient(
        auth=auth
    )
    
    try:
        # Invoke a secure agent endpoint
        result = await client.invoke(
            'agent://secure-api.example.com/protected-capability',
            {'param1': 'value1'}
        )
        
        print('Result:', result)
    except Exception as error:
        print('Secure invocation failed:', error)

if __name__ == "__main__":
    asyncio.run(invoke_secure_agent())
```

### Implementing a Secure Agent Server

```python
from agent_server.agent_server.server import AgentServer
import asyncio
from datetime import datetime

async def main():
    # Create a server that requires authentication
    server = AgentServer(
        name="secure-agent",
        version="1.0.0",
        description="A secure agent example"
    )
    
    # Register a protected capability
    async def protected_data_handler(params, context):
        # Context includes authentication info when provided
        auth_info = getattr(context, 'auth', None)
        user_id = auth_info.subject if auth_info else 'anonymous'
        
        return {
            "message": f"Protected data for {user_id}",
            "timestamp": datetime.now().isoformat()
        }
    
    server.capability(
        "protected-data",
        description="Returns protected data",
        requires_auth=True,  # This capability requires authentication
        handler=protected_data_handler
    )
    
    # Start the server
    await server.listen(
        http={"port": 3000}
    )
    
    print('Secure agent server running at http://localhost:3000')

if __name__ == "__main__":
    asyncio.run(main())
```

### Using Local Transport

```python
from agent_client.agent_client.client import AgentClient
from agent_transport.agent_transport.transports.local import LocalTransport
import asyncio

async def use_local_transport():
    # Create a client with local transport configured
    client = AgentClient(
        transports={
            "local": {}  # Local transport options
        }
    )
    
    # Invoke a local agent (no network communication)
    result = await client.invoke(
        'agent+local://my-local-agent/capability',
        {"param": "value"}
    )
    
    print('Local result:', result)

if __name__ == "__main__":
    asyncio.run(use_local_transport())
```

## Echo Agent Example

The echo agent example demonstrates a simple implementation of the Agent URI protocol. You can find the full implementation in the `examples/echo-agent` directory.

### Running the Echo Agent

```bash
# Start the echo agent server
python echo_agent.py

# In another terminal, run a client to test it
python simple_client.py
```

### Echo Agent Server Code

```python
from agent_server.agent_server.server import AgentServer
import asyncio

async def main():
    # Create the echo agent server
    server = AgentServer(
        name="echo-agent",
        version="1.0.0",
        description="A simple agent that echoes back messages"
    )
    
    # Register echo capability
    async def echo_handler(params):
        message = params.get('message', 'No message provided')
        return {
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    server.capability(
        "echo",
        description="Echoes back the message sent to it",
        handler=echo_handler
    )
    
    # Start server with HTTP
    await server.listen(
        http={"port": 3000}
    )
    
    print('Echo agent running:')
    print('- HTTP: http://localhost:3000')
    print('Agent URI: agent://localhost:3000/echo')

if __name__ == "__main__":
    asyncio.run(main())
```

### Echo Agent Client Code

```python
from agent_client.agent_client.client import AgentClient
import asyncio
import sys

async def main():
    # Get message from command line or use default
    message = sys.argv[1] if len(sys.argv) > 1 else "Hello, Agent!"
    
    client = AgentClient()
    
    try:
        result = await client.invoke(
            'agent://localhost:3000/echo',
            {"message": message}
        )
        
        print("Echo agent responded:", result["message"])
    except Exception as error:
        print("Error:", error)

if __name__ == "__main__":
    asyncio.run(main())
```

This document provides examples of the current functionality implemented in the Agent URI reference implementation. For information on planned future enhancements, see the [TODO.md](../TODO.md) file.
