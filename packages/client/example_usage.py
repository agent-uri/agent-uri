#!/usr/bin/env python3
"""
Example usage of the agent-client SDK.

This script demonstrates how to use the client SDK to interact with agents
using the agent:// protocol.
"""

import json
import logging
from pprint import pprint

from agent_client import (
    AgentClient, 
    AgentSession, 
    BearerTokenAuth, 
    ApiKeyAuth, 
    InvocationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def example_basic_invocation():
    """Demonstrate basic invocation of an agent capability."""
    print("\n=== Basic Invocation Example ===\n")
    
    # Create a client
    client = AgentClient(timeout=30)
    
    try:
        # Invoke a capability (using HTTPBin as an example)
        print("Invoking echo capability via HTTPS:")
        response = client.invoke(
            uri="agent+https://httpbin.org/get",
            params={"message": "Hello from agent-client!"}
        )
        print(f"Response: {json.dumps(response, indent=2)}\n")
    except InvocationError as e:
        print(f"Error: {e}")


def example_explicit_transport():
    """Demonstrate invocation with explicit transport binding."""
    print("\n=== Explicit Transport Example ===\n")
    
    # Create a client
    client = AgentClient()
    
    try:
        # Invoke a capability with explicit transport binding
        print("Invoking capability with explicit transport:")
        response = client.invoke(
            uri="agent+https://httpbin.org/post",
            params={"message": "Hello with explicit transport!"},
            headers={"Custom-Header": "CustomValue"}
        )
        print(f"Response: {json.dumps(response, indent=2)}\n")
    except InvocationError as e:
        print(f"Error: {e}")


def example_authentication():
    """Demonstrate authentication with an agent."""
    print("\n=== Authentication Example ===\n")
    
    # Create an API key authentication provider
    api_key_auth = ApiKeyAuth(
        api_key="test-api-key-12345",
        header_name="X-API-Key"
    )
    
    # Create a bearer token authentication provider
    bearer_auth = BearerTokenAuth(
        token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.Et9HFtf9R3GEMA0IICOfFMVXY7kkTX1wr4qCyhIf58U",
        token_type="Bearer"
    )
    
    # Create a client with the API key authentication
    client = AgentClient(auth_provider=api_key_auth)
    
    try:
        # Invoke a capability with API key authentication
        print("Invoking capability with API key authentication:")
        response = client.invoke(
            uri="agent+https://httpbin.org/post",
            params={"message": "Hello with API key!"}
        )
        print(f"Response headers: {json.dumps(response.get('headers', {}), indent=2)}\n")
        
        # Switch to bearer token authentication
        client.auth_provider = bearer_auth
        
        # Invoke a capability with bearer token authentication
        print("Invoking capability with bearer token authentication:")
        response = client.invoke(
            uri="agent+https://httpbin.org/post",
            params={"message": "Hello with bearer token!"}
        )
        print(f"Response headers: {json.dumps(response.get('headers', {}), indent=2)}\n")
    except InvocationError as e:
        print(f"Error: {e}")


def example_streaming():
    """Demonstrate streaming from an agent capability."""
    print("\n=== Streaming Example ===\n")
    
    # Create a client
    client = AgentClient()
    
    try:
        # Stream from a capability (using HTTPBin as an example)
        print("Streaming from agent:")
        
        # For demonstration, we'll use a normal HTTP endpoint and process it as chunks
        # In a real scenario, use a proper streaming endpoint
        chunks = []
        for i, chunk in enumerate(client.stream(
            uri="agent+https://httpbin.org/get",
            params={"stream": "true"},
            stream_format="raw"  # Process as raw chunks
        )):
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8")
            print(f"Received chunk {i}: {chunk[:50]}...")
            chunks.append(chunk)
        
        # In a real streaming scenario, you'd process each chunk as it arrives
        print(f"\nReceived {len(chunks)} chunks\n")
    except InvocationError as e:
        print(f"Error: {e}")


def example_session():
    """Demonstrate using a session for stateful interactions."""
    print("\n=== Session Example ===\n")
    
    # Create a client
    client = AgentClient()
    
    # Create a session
    session = client.create_session(
        uri="agent+https://httpbin.org",
        session_id="test-session-12345"
    )
    
    try:
        # First interaction in the session
        print("First session interaction:")
        response1 = session.invoke(
            capability="get",
            params={"message": "Hello in session!"}
        )
        print(f"Response headers: {json.dumps(response1.get('headers', {}), indent=2)}\n")
        
        # Second interaction in the same session
        print("Second session interaction:")
        response2 = session.invoke(
            capability="get",
            params={"message": "Hello again in the same session!"}
        )
        print(f"Response headers: {json.dumps(response2.get('headers', {}), indent=2)}\n")
        
        # Session maintains the session ID across requests
        print(f"Session ID used in both requests: {session.session_id}\n")
    except InvocationError as e:
        print(f"Error: {e}")


def example_error_handling():
    """Demonstrate error handling with the client SDK."""
    print("\n=== Error Handling Example ===\n")
    
    # Create a client
    client = AgentClient()
    
    # Test with an invalid URI
    try:
        print("Testing with invalid URI:")
        client.invoke(uri="invalid://uri")
    except Exception as e:
        print(f"Error (invalid URI): {e.__class__.__name__}: {e}\n")
    
    # Test with non-existent endpoint
    try:
        print("Testing with non-existent endpoint:")
        client.invoke(uri="agent+https://non-existent-domain-12345.example")
    except Exception as e:
        print(f"Error (non-existent endpoint): {e.__class__.__name__}: {e}\n")
    
    # Test with invalid capability
    try:
        print("Testing with invalid capability:")
        client.invoke(uri="agent+https://httpbin.org/non-existent-path")
    except Exception as e:
        print(f"Error (invalid capability): {e.__class__.__name__}: {e}\n")


if __name__ == "__main__":
    # Run the examples
    try:
        example_basic_invocation()
        example_explicit_transport()
        example_authentication()
        example_streaming()
        example_session()
        example_error_handling()
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
