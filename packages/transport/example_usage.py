#!/usr/bin/env python3
"""
Example usage of the agent-transport package.

This script demonstrates how to use the transport binding layer
to invoke agent capabilities using different transport protocols.
"""

import json
import logging
from agent_uri.parser import parse_agent_uri
from agent_transport.registry import default_registry
from agent_transport.transports.https import HttpsTransport
from agent_transport.transports.websocket import WebSocketTransport
from agent_transport.transports.local import LocalTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def example_https_transport():
    """Demonstrate using HTTPS transport."""
    print("\n=== HTTPS Transport Example ===\n")
    
    # Register the HTTPS transport
    default_registry.register_transport(HttpsTransport)
    
    # Get the registered transport
    https_transport = default_registry.get_transport("https")
    
    try:
        # Invoke a capability (using HTTPBin as an example)
        print("Invoking echo capability via HTTPS:")
        response = https_transport.invoke(
            endpoint="https://httpbin.org",
            capability="get",
            params={"message": "Hello from agent-transport!"},
            method="GET"  # Explicitly use GET method for httpbin
        )
        print(f"Response: {json.dumps(response, indent=2)}\n")
    except Exception as e:
        print(f"Error: {e}")


def example_local_transport():
    """Demonstrate using Local transport."""
    print("\n=== Local Transport Example ===\n")
    
    # Create a local transport
    local_transport = LocalTransport()
    
    # Define a simple agent handler
    def echo_agent(capability, params):
        """Simple echo agent for demonstration."""
        if capability == "echo":
            return {
                "message": f"Echo: {params.get('message', 'Hello!')}",
                "capability": capability,
                "params": params
            }
        elif capability == "stream":
            # For streaming example, return a list for direct invocation
            # but yield for streaming to allow proper handling
            if params.get('_streaming', False):
                for i in range(3):
                    yield {
                        "chunk": i,
                        "message": f"Stream chunk {i}: {params.get('message', 'Hello!')}"
                    }
            else:
                # For direct invoke, return a JSON-serializable object
                return [
                    {
                        "chunk": i,
                        "message": f"Stream chunk {i}: {params.get('message', 'Hello!')}"
                    }
                    for i in range(3)
                ]
        else:
            return {"error": f"Unknown capability: {capability}"}
    
    # Register the agent
    socket_path = local_transport.register_agent("echo-agent", echo_agent)
    print(f"Registered local agent at: {socket_path}")
    
    try:
        # Invoke the agent with echo capability
        print("\nInvoking echo capability:")
        response = local_transport.invoke(
            endpoint="agent+local://echo-agent",
            capability="echo",
            params={"message": "Hello from local transport!"}
        )
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Stream from the agent
        print("\nStreaming from agent:")
        for chunk in local_transport.stream(
            endpoint="agent+local://echo-agent",
            capability="stream",
            params={"message": "Hello streaming!", "_streaming": True}
        ):
            print(f"Received chunk: {json.dumps(chunk, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Unregister the agent
        local_transport.unregister_agent("echo-agent")
        print("\nUnregistered local agent")


def example_uri_integration():
    """Demonstrate integration with agent URI parser."""
    print("\n=== Agent URI Integration Example ===\n")
    
    # Register transports
    default_registry.register_transport(HttpsTransport)
    default_registry.register_transport(WebSocketTransport)
    default_registry.register_transport(LocalTransport)
    
    # Parse an agent URI
    uri_str = "agent+https://httpbin.org/get?message=Hello+from+Agent+URI!"
    uri = parse_agent_uri(uri_str)
    print(f"Parsed URI: {uri}")
    
    try:
        # Get appropriate transport based on URI transport protocol
        transport = default_registry.get_transport(uri.transport)
        print(f"Selected transport: {transport.protocol}")
        
        # Invoke the agent
        response = transport.invoke(
            endpoint=f"{uri.transport}://{uri.host}",
            capability=uri.path,
            params=uri.query,
            method="GET"  # Explicitly use GET method for httpbin
        )
        print(f"Response: {json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")


def example_transport_registry():
    """Demonstrate transport registry features."""
    print("\n=== Transport Registry Example ===\n")
    
    # Create a new registry
    registry = default_registry
    
    # Register multiple transports
    registry.register_transport(HttpsTransport)
    registry.register_transport(WebSocketTransport)
    registry.register_transport(LocalTransport)
    
    # List supported protocols
    protocols = registry.list_supported_protocols()
    print(f"Supported protocols: {', '.join(protocols)}")
    
    # Check if protocols are supported
    print(f"HTTPS supported: {registry.is_protocol_supported('https')}")
    print(f"WSS supported: {registry.is_protocol_supported('wss')}")
    print(f"Local supported: {registry.is_protocol_supported('local')}")
    print(f"Unknown supported: {registry.is_protocol_supported('unknown')}")
    
    # Agent protocol (no explicit transport) defaults to HTTPS
    print(f"Agent protocol supported: {registry.is_protocol_supported('agent')}")


if __name__ == "__main__":
    # Run the examples
    example_https_transport()
    example_local_transport()
    example_uri_integration()
    example_transport_registry()
