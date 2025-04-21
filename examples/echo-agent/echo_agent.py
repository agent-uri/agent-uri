#!/usr/bin/env python3
"""
Echo Agent - Example implementation of an agent using the agent:// protocol.

This agent demonstrates basic capability invocation with an 'echo' capability
that responds with the same message sent to it, appended with a timestamp.
"""

import datetime
import json
import logging
import os
from typing import Dict, Any

import uvicorn
from agent_server import (
    capability,
    FastAPIAgentServer,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define echo capability using the decorator


@capability(
    name="echo",
    description="Echoes back the input message appended with the timestamp",
    version="1.0.0",
    tags=["utility", "demo"],
    input_schema={
        "type": "object",
        "properties": {
            "message": {"type": "string"}
        },
        "required": ["message"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "original_message": {"type": "string"}
        }
    },
    is_deterministic=False  # Not deterministic due to changing timestamp
)
async def echo(*, params: Dict[str, Any] = None, session_id: str = None, message: str = None, **kwargs) -> Dict[str, Any]:
    """
    Echo back the input message with a timestamp.
    
    Args:
        params: Dictionary containing the message in the 'message' field
        session_id: Optional session identifier
        message: The message to echo (may be passed directly or in params)
        **kwargs: Any additional parameters from the server
        
    Returns:
        A dictionary containing the echoed message with timestamp
    """
    # Handle case when params is None (which would cause the error we're seeing)
    if params is None:
        params = {}
    
    # Extract the message either from direct parameter or from params dictionary
    # Our client tests are passing message in the params dictionary, but the server
    # is extracting it and passing it as a direct kwarg
    if message is None:
        message = params.get("message", "")
    
    # Ensure we have a message, even if empty
    if not isinstance(message, str):
        message = str(message) if message is not None else ""
    
    # Log the session info if available
    if session_id:
        logger.info(f"Request from session: {session_id}")
        
    # Add verbose logging to help with debugging
    logger.info(f"Echo capability called with params: {params}, session_id: {session_id}")
    if kwargs:
        logger.info(f"Additional kwargs: {list(kwargs.keys())}")
    
    current_time = datetime.datetime.now().isoformat()
    result = f"{message} [{current_time}]"
    
    logger.info(f"Echo capability called with message: {message}")
    
    return {
        "result": result,
        "timestamp": current_time,
        "original_message": message
    }


def create_echo_agent_server(host: str = "0.0.0.0", port: int = 8765):
    """
    Create and configure the Echo Agent server.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        
    Returns:
        Configured FastAPIAgentServer instance
    """
    # Create the server
    server = FastAPIAgentServer(
        name="echo-agent",
        version="1.0.0",
        description="An example agent that echoes messages with timestamps",
        provider={
            "organization": "Agent URI Project"
        },
        documentation_url="https://github.com/username/agent-uri/examples/echo-agent",
        interaction_model="request-response",
        server_url=f"http://{host}:{port}",
        enable_cors=True,
        enable_docs=True,
        enable_agent_json=True
    )
    
    # Register the echo capability
    server.register_capability("echo", echo._capability)
    
    # Ensure output directory exists
    os.makedirs("./output", exist_ok=True)
    
    # Save the agent descriptor
    server.save_agent_descriptor("./output/agent.json")
    
    return server


def main():
    """Run the Echo Agent server."""
    # Configure host and port
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8765"))  # Changed default port to avoid conflicts
    
    # Create the server
    server = create_echo_agent_server(host, port)
    
    # Print out the agent descriptor
    descriptor = server.get_agent_descriptor()
    print("\nEcho Agent Descriptor:")
    print(json.dumps(descriptor, indent=2))
    
    # Run the server
    print(f"\nStarting Echo Agent server on http://{host}:{port}")
    print(f"- API docs: http://{host}:{port}/docs")
    print(f"- Agent descriptor: http://{host}:{port}/agent.json")
    
    uvicorn.run(server.app, host=host, port=port)


if __name__ == "__main__":
    main()
