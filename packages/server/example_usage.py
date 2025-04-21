"""
Example usage of the agent-server package.

This file demonstrates how to create and run an agent server using the
agent-server SDK for the agent:// protocol.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List

import uvicorn

from agent_server import (
    capability,
    FastAPIAgentServer,
    AgentDescriptorGenerator
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define capabilities using the decorator
@capability(
    name="echo",
    description="Echoes back the input text",
    version="1.0.0",
    tags=["utility", "text"],
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"}
        },
        "required": ["text"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"}
        }
    }
)
async def echo(text: str) -> Dict[str, Any]:
    """Echo back the input text."""
    return {"text": text}


@capability(
    name="generate-greeting",
    description="Generates a greeting for a given name",
    version="1.0.0",
    tags=["utility", "text", "greeting"],
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "language": {"type": "string", "default": "en"}
        },
        "required": ["name"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "greeting": {"type": "string"}
        }
    }
)
async def generate_greeting(name: str, language: str = "en") -> Dict[str, Any]:
    """Generate a greeting in the specified language."""
    greetings = {
        "en": f"Hello, {name}!",
        "es": f"¡Hola, {name}!",
        "fr": f"Bonjour, {name}!",
        "de": f"Hallo, {name}!",
        "it": f"Ciao, {name}!",
        "ja": f"こんにちは, {name}!"
    }
    
    # Default to English if language not supported
    greeting = greetings.get(language, greetings["en"])
    
    return {"greeting": greeting}


@capability(
    name="calculate",
    description="Performs basic arithmetic calculations",
    version="1.0.0",
    tags=["math", "utility"],
    input_schema={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
            "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]}
        },
        "required": ["a", "b", "operation"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "result": {"type": "number"}
        }
    },
    is_deterministic=True,
    expected_output_variability="none"
)
async def calculate(
    a: float,
    b: float,
    operation: str
) -> Dict[str, Any]:
    """Perform a basic arithmetic calculation."""
    result = None
    
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")
    
    return {"result": result}


@capability(
    name="stream-countdown",
    description="Streams a countdown from the given number",
    version="1.0.0",
    tags=["utility", "streaming"],
    input_schema={
        "type": "object",
        "properties": {
            "start": {"type": "integer", "minimum": 1, "maximum": 100},
            "delay": {"type": "number", "minimum": 0.1, "maximum": 2.0, "default": 0.5}
        },
        "required": ["start"]
    },
    streaming=True
)
async def stream_countdown(start: int, delay: float = 0.5):
    """Stream a countdown from the given number."""
    for i in range(start, 0, -1):
        yield {"count": i}
        await asyncio.sleep(delay)
    
    yield {"count": 0, "message": "Countdown complete!"}


# Example authenticator function
def authenticate_request(request_data: Dict[str, Any]) -> bool:
    """
    Simple authenticator that checks for an API key.
    
    In a real application, you would validate against a database or auth service.
    """
    headers = request_data.get("headers", {})
    api_key = headers.get("X-API-Key")
    
    # Very simple check - in a real app, use secure comparison
    return api_key == "test-api-key"


def create_agent_server():
    """Create and configure an agent server."""
    # Create the server
    server = FastAPIAgentServer(
        name="example-agent",
        version="1.0.0",
        description="Example agent server demonstrating the agent-server SDK",
        provider={
            "organization": "Agent URI Team"
        },
        documentation_url="https://example.com/docs",
        interaction_model="request-response",
        auth_schemes=["ApiKey"],
        skills=[
            {"id": "math", "name": "Basic Arithmetic"},
            {"id": "text", "name": "Text Processing"}
        ],
        server_url="https://example.com/agent",
        enable_cors=True,
        enable_docs=True,
        enable_agent_json=True
    )
    
    # Register capabilities
    server.register_capability("echo", echo._capability)
    server.register_capability("generate-greeting", generate_greeting._capability)
    server.register_capability("calculate", calculate._capability)
    server.register_capability("stream-countdown", stream_countdown._capability)
    
    # Register the authenticator
    server.register_authenticator(authenticate_request)
    
    # Save the agent descriptor
    os.makedirs("./output", exist_ok=True)
    server.save_agent_descriptor("./output/agent.json")
    
    return server


def main():
    """Run the agent server."""
    # Create the server
    server = create_agent_server()
    
    # Print out the agent descriptor
    descriptor = server.get_agent_descriptor()
    print("\nAgent Descriptor:")
    print(json.dumps(descriptor, indent=2))
    
    # Run the server
    print("\nStarting server on http://localhost:8000")
    print("- API docs: http://localhost:8000/docs")
    print("- Agent descriptor: http://localhost:8000/agent.json")
    uvicorn.run(server.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
