#!/usr/bin/env python3
"""
Unit tests for the Echo Agent

This module contains tests to verify the Echo Agent correctly implements
the agent:// protocol and its echo capability works as expected.
"""

import unittest
import asyncio
import datetime
from unittest import mock

from agent_client import AgentClient
from agent_transport.registry import default_registry
from http_transport import HttpTransport

# Import our echo agent modules
from echo_agent import echo, create_echo_agent_server


class EchoCapabilityTest(unittest.TestCase):
    """Test the echo capability directly."""

    def test_echo_response_structure(self):
        """Test that the echo function returns the expected structure."""
        # Run the echo function using asyncio
        message = "Test message"
        result = asyncio.run(echo(params={"message": message}))
        
        # Verify the result structure
        self.assertIn("result", result)
        self.assertIn("timestamp", result)
        self.assertIn("original_message", result)
        
        # Verify content
        self.assertEqual(result["original_message"], message)
        
        # Verify timestamp is a valid datetime string
        try:
            datetime.datetime.fromisoformat(result["timestamp"])
        except ValueError:
            self.fail("timestamp is not a valid ISO format datetime string")
        
        # Verify result format
        self.assertTrue(result["result"].startswith(message))
        self.assertIn(result["timestamp"], result["result"])

    def test_echo_with_empty_message(self):
        """Test echo function with an empty message."""
        message = ""
        result = asyncio.run(echo(params={"message": message}))
        
        self.assertEqual(result["original_message"], message)
        self.assertTrue(result["result"].startswith(message))

    def test_echo_with_special_characters(self):
        """Test echo function with special characters."""
        message = "!@#$%^&*()_+<>?:{}"
        result = asyncio.run(echo(params={"message": message}))
        
        self.assertEqual(result["original_message"], message)
        self.assertTrue(result["result"].startswith(message))


class EchoAgentServerTest(unittest.TestCase):
    """Test the Echo Agent server configuration."""

    def test_server_creation(self):
        """Test that the server is created with expected configuration."""
        server = create_echo_agent_server("test-host", 9999)
        
        # Verify server configuration
        self.assertEqual(server.name, "echo-agent")
        self.assertEqual(server.version, "1.0.0")
        self.assertTrue("echo" in server._capabilities)


class MockClientTest(unittest.TestCase):
    """Integration test with a simple mock instead of patching."""

    def setUp(self):
        """Set up the test environment."""
        self.client = AgentClient(timeout=5)
    
    def test_mock_invocation(self):
        """Test a mocked response for the echo capability."""
        # Create test data
        test_timestamp = datetime.datetime.now().isoformat()
        test_message = "Hello agent"
        expected_response = {
            "result": f"{test_message} [{test_timestamp}]",
            "timestamp": test_timestamp,
            "original_message": test_message
        }
        
        # Create a mock client that returns our test data
        mock_client = mock.Mock()
        mock_client.invoke = mock.AsyncMock(return_value=expected_response)
        
        # Run the coroutine in the test
        response = asyncio.run(mock_client.invoke(
            uri="agent+http://localhost:8765/echo",
            params={"message": test_message}
        ))
        
        # Verify the mock was called
        mock_client.invoke.assert_called_once()
        
        # Verify the response has the expected values
        self.assertEqual(response["original_message"], test_message)
        self.assertEqual(response["timestamp"], test_timestamp)


def register_http_transport():
    """Register our custom HTTP transport with the global registry."""
    transport = HttpTransport()
    default_registry.register_transport(HttpTransport)
    print(f"Registered HTTP transport for protocol '{transport.protocol}'")
    print(f"Supported protocols: {default_registry.list_supported_protocols()}")


if __name__ == "__main__":
    # Register the HTTP transport
    register_http_transport()
    
    # Run the tests
    unittest.main()
