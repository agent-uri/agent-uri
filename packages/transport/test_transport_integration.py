#!/usr/bin/env python3
"""
Integration test for the agent-transport package.

This script tests the integration between different transport protocols
and other components of the agent:// ecosystem such as URI parsing
and agent descriptor resolution.
"""

import json
import logging
import argparse
import sys
import pytest
from typing import Dict, Any, List

# Import the transport packages - these should always be available
from agent_transport.registry import TransportRegistry
from agent_transport.transports.https import HttpsTransport
from agent_transport.transports.websocket import WebSocketTransport
from agent_transport.transports.local import LocalTransport

# Try to import the optional integration packages
HAVE_FULL_STACK = True
try:
    from agent_uri.parser import parse_agent_uri
    from agent_descriptor.models import AgentDescriptor, Capability
    from agent_resolver.resolver import AgentResolver
except ImportError as e:
    print(f"Note: Some components are not available ({e})")
    print("Only testing standalone transport functionality.")
    HAVE_FULL_STACK = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_test_environment() -> TransportRegistry:
    """
    Set up the test environment by registering all transport protocols.
    
    Returns:
        The configured transport registry
    """
    registry = TransportRegistry()
    
    # Register all transport protocols
    registry.register_transport(HttpsTransport)
    registry.register_transport(WebSocketTransport)
    registry.register_transport(LocalTransport)
    
    print(f"Registered transports: {', '.join(registry.list_supported_protocols())}")
    return registry


def setup_local_agent(local_transport: LocalTransport) -> str:
    """
    Set up a local agent for testing.
    
    Args:
        local_transport: The local transport to register the agent with
        
    Returns:
        The agent name
    """
    def test_agent_handler(capability: str, params: Dict[str, Any]):
        """Handler for the test agent."""
        if capability == "echo":
            return {
                "status": "success",
                "message": f"Echo: {params.get('message', 'No message')}",
                "params": params
            }
        elif capability == "stream":
            # For streaming capability, yield multiple results
            if params.get('_streaming', False):
                for i in range(1, 4):
                    yield {
                        "chunk": i,
                        "message": f"Chunk {i}: {params.get('message', 'No message')}"
                    }
            else:
                # For direct invoke, return a JSON-serializable object
                return [
                    {
                        "chunk": i,
                        "message": f"Chunk {i}: {params.get('message', 'No message')}"
                    }
                    for i in range(1, 4)
                ]
        else:
            return {
                "status": "error",
                "message": f"Unknown capability: {capability}"
            }
    
    agent_name = "test-agent"
    socket_path = local_transport.register_agent(agent_name, test_agent_handler)
    print(f"Registered local agent '{agent_name}' at {socket_path}")
    
    return agent_name


@pytest.fixture
def test_registry():
    """Create a registry for testing."""
    return setup_test_environment()


@pytest.fixture
def test_agent(test_registry):
    """
    Create a test agent for testing.
    
    This fixture sets up a local agent and cleans it up
    after the test is complete.
    """
    local_transport = test_registry.get_transport("local")
    agent_name = setup_local_agent(local_transport)
    
    yield agent_name
    
    # Clean up after test
    local_transport.unregister_agent(agent_name)


def test_uri_parsing_and_resolution():
    """Test URI parsing and resolution with different transport protocols."""
    print("\n=== Testing URI Parsing and Resolution ===\n")
    
    if not HAVE_FULL_STACK:
        print("Skipping URI parsing test (agent_uri package not available)")
        return
    
    test_uris = [
        "agent://example.com/echo?message=Hello",
        "agent+https://example.com/echo?message=Hello",
        "agent+wss://example.com/stream?message=Hello",
        "agent+local://test-agent/echo?message=Hello"
    ]
    
    for uri_str in test_uris:
        print(f"\nParsing URI: {uri_str}")
        uri = parse_agent_uri(uri_str)
        
        print(f"  Scheme: {uri.scheme}")
        print(f"  Transport: {uri.transport or 'default (https)'}")
        print(f"  Authority: {uri.authority}")
        print(f"  Path: {uri.path}")
        print(f"  Query: {uri.query}")
        
        # Determine appropriate transport
        if uri.transport:
            print(f"  Transport protocol: {uri.transport}")
        else:
            print("  Transport protocol: https (default fallback)")


def test_transport_invocation(test_registry, test_agent):
    """
    Test invoking capabilities via different transports.
    
    Args:
        test_registry: The transport registry to use
        test_agent: The name of the local test agent
    """
    print("\n=== Testing Transport Invocation ===\n")
    
    # Test local transport
    local_transport = test_registry.get_transport("local")
    print("\nTesting Local Transport:")
    try:
        response = local_transport.invoke(
            endpoint=f"agent+local://{test_agent}",
            capability="echo",
            params={"message": "Hello from local transport!"}
        )
        print(f"Response: {json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"Error invoking local agent: {e}")
    
    # Test HTTPS transport with a public API
    https_transport = test_registry.get_transport("https")
    print("\nTesting HTTPS Transport (with httpbin.org):")
    try:
        response = https_transport.invoke(
            endpoint="https://httpbin.org",
            capability="get",
            params={"message": "Hello from HTTPS transport!"},
            method="GET"  # Explicitly use GET method for httpbin
        )
        print(f"Response args: {json.dumps(response.get('args', {}), indent=2)}")
    except Exception as e:
        print(f"Error invoking HTTPS endpoint: {e}")


def test_streaming(test_registry, test_agent):
    """
    Test streaming capabilities via different transports.
    
    Args:
        test_registry: The transport registry to use
        test_agent: The name of the local test agent
    """
    print("\n=== Testing Streaming ===\n")
    
    # Test local transport streaming
    local_transport = test_registry.get_transport("local")
    print("\nTesting Local Transport Streaming:")
    try:
        print("Streaming from local agent...")
        for chunk in local_transport.stream(
            endpoint=f"agent+local://{test_agent}",
            capability="stream",
            params={"message": "Hello from streaming!", "_streaming": True}
        ):
            print(f"Received chunk: {json.dumps(chunk, indent=2)}")
    except Exception as e:
        print(f"Error streaming from local agent: {e}")


def test_integrated_flow(test_registry):
    """
    Test an integrated flow with URI parsing, resolution, and invocation.
    
    Args:
        test_registry: The transport registry to use
    """
    print("\n=== Testing Integrated Flow ===\n")
    
    if not HAVE_FULL_STACK:
        print("Skipping integrated flow test (agent_uri package not available)")
        return
    
    # This is a more realistic flow that would be used in a real application
    uri_str = "agent+https://httpbin.org/get?message=Hello+World"
    
    try:
        # Parse the URI
        print(f"Parsing URI: {uri_str}")
        uri = parse_agent_uri(uri_str)
        
        # Get the appropriate transport
        transport = test_registry.get_transport(uri.transport or "agent")
        print(f"Selected transport: {transport.protocol}")
        
        # Invoke the capability
        print("Invoking capability...")
        response = transport.invoke(
            endpoint=f"{uri.transport}://{uri.host}",
            capability=uri.path,
            params=uri.query,
            method="GET"  # Explicitly use GET method for httpbin
        )
        
        # Print response
        if isinstance(response, dict) and 'args' in response:
            print(f"Response args: {json.dumps(response['args'], indent=2)}")
        else:
            print(f"Response: {json.dumps(response, indent=2)}")
            
    except Exception as e:
        print(f"Error in integrated flow: {e}")


def main():
    """Run the integration tests."""
    parser = argparse.ArgumentParser(description="Integration test for agent-transport")
    parser.add_argument("--test", choices=["all", "uri", "invoke", "stream", "flow"],
                         default="all", help="Which test to run")
    args = parser.parse_args()
    
    # Set up test environment
    registry = setup_test_environment()
    
    # Set up a local agent for testing
    local_transport = registry.get_transport("local")
    agent_name = setup_local_agent(local_transport)
    
    try:
        # Run selected tests
        if args.test in ["all", "uri"]:
            test_uri_parsing_and_resolution()
            
        if args.test in ["all", "invoke"]:
            test_transport_invocation(registry, agent_name)
            
        if args.test in ["all", "stream"]:
            test_streaming(registry, agent_name)
            
        if args.test in ["all", "flow"]:
            test_integrated_flow(registry)
            
    finally:
        # Clean up local agent
        if local_transport.unregister_agent(agent_name):
            print(f"\nUnregistered local agent '{agent_name}'")
        else:
            print(f"\nWarning: Failed to unregister local agent '{agent_name}'")


if __name__ == "__main__":
    main()
