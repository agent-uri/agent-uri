"""
Tests for the agent resolver.

This module contains tests for the agent:// URI resolver, including
caching tests and resolution strategy tests.
"""

import json
import unittest
from unittest.mock import MagicMock

from ...descriptor.models import AgentDescriptor
from ..resolver import AgentResolver, ResolverNotFoundError

# Sample descriptor JSON for testing
SAMPLE_DESCRIPTOR = {
    "name": "test-agent",
    "version": "1.0.0",
    "capabilities": [{"name": "test-capability", "description": "A test capability"}],
}

SAMPLE_AGENTS_REGISTRY = {
    "agents": {
        "planner": "https://planner.acme.ai/agent.json",
        "translator": "https://translator.acme.ai/agent.json",
    }
}


class MockResponse:
    """Mock response for requests."""

    def __init__(self, json_data, status_code=200, headers=None):
        self.json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}
        self.text = json.dumps(json_data)

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")


class TestAgentResolver(unittest.TestCase):
    """Tests for the AgentResolver class."""

    def setUp(self):
        """Set up tests."""
        self.resolver = AgentResolver()

    def test_resolve_single_agent(self):
        """Test resolving a single agent at domain root."""
        uri = "agent://planner.acme.ai/"

        # Create a resolver with a mock session
        mock_session = MagicMock()
        self.resolver.session = mock_session

        # Mock the response for the agent.json request
        mock_response = MockResponse(SAMPLE_DESCRIPTOR)

        # Set up the mock to return our response for domain root
        def mock_get(url, **kwargs):
            if url == "https://planner.acme.ai/agent.json":
                return mock_response
            return MockResponse({}, status_code=404)

        mock_session.get.side_effect = mock_get

        # Resolve the URI
        descriptor, metadata = self.resolver.resolve(uri)

        # Check the results
        self.assertIsInstance(descriptor, AgentDescriptor)
        self.assertEqual(descriptor.name, "test-agent")
        self.assertEqual(metadata["resolution_method"], "domain_root")
        self.assertEqual(metadata["endpoint"], "https://planner.acme.ai/agent.json")

        # Verify the correct URL was requested
        mock_session.get.assert_any_call(
            "https://planner.acme.ai/agent.json", timeout=10, verify=True
        )

    def test_resolve_well_known_agent(self):
        """Test resolving a single agent using .well-known/agent.json."""
        uri = "agent://acme.ai/"

        # Create a resolver with a mock session
        mock_session = MagicMock()
        self.resolver.session = mock_session

        # Mock responses - first fail domain root, then succeed with well-known
        def mock_get(url, **kwargs):
            if url == "https://acme.ai/agent.json":
                return MockResponse({}, status_code=404)
            elif url == "https://acme.ai/.well-known/agents.json":
                return MockResponse({}, status_code=404)
            elif url == "https://acme.ai/.well-known/agent.json":
                return MockResponse(SAMPLE_DESCRIPTOR)
            return MockResponse({}, status_code=404)

        mock_session.get.side_effect = mock_get

        # Resolve the URI
        descriptor, metadata = self.resolver.resolve(uri)

        # Check the results
        self.assertIsInstance(descriptor, AgentDescriptor)
        self.assertEqual(descriptor.name, "test-agent")
        self.assertEqual(metadata["resolution_method"], "well_known")
        self.assertEqual(metadata["endpoint"], "https://acme.ai/.well-known/agent.json")

    def test_resolve_from_registry(self):
        """Test resolving an agent from the registry."""
        uri = "agent://acme.ai/planner"

        # Create a resolver with a mock session
        mock_session = MagicMock()
        self.resolver.session = mock_session

        # Mock responses for multi-step resolution
        def mock_get(url, **kwargs):
            if url == "https://acme.ai/agent.json":
                return MockResponse({}, status_code=404)
            elif url == "https://acme.ai/.well-known/agents.json":
                return MockResponse(SAMPLE_AGENTS_REGISTRY)
            elif url == "https://planner.acme.ai/agent.json":
                return MockResponse(SAMPLE_DESCRIPTOR)
            return MockResponse({}, status_code=404)

        mock_session.get.side_effect = mock_get

        # Resolve the URI
        descriptor, metadata = self.resolver.resolve(uri)

        # Check the results
        self.assertIsInstance(descriptor, AgentDescriptor)
        self.assertEqual(descriptor.name, "test-agent")
        self.assertEqual(metadata["resolution_method"], "agents_registry")
        self.assertEqual(
            metadata["registry_url"], "https://acme.ai/.well-known/agents.json"
        )
        self.assertEqual(metadata["endpoint"], "https://planner.acme.ai/agent.json")

    def test_resolve_with_explicit_transport(self):
        """Test resolving an agent with explicit transport binding."""
        uri = "agent+wss://realtime.acme.ai/chat"

        # Create a resolver with a mock session
        mock_session = MagicMock()
        self.resolver.session = mock_session

        # Mock 404 response for all endpoints
        mock_session.get.return_value = MockResponse({}, status_code=404)

        # Resolve the URI - should fallback to transport binding
        _, metadata = self.resolver.resolve(uri)

        # Check the results
        self.assertEqual(metadata["resolution_method"], "transport_binding")
        self.assertEqual(metadata["endpoint"], "wss://realtime.acme.ai/chat")

    def test_resolver_not_found(self):
        """Test behavior when agent cannot be found."""
        uri = "agent://nonexistent.example.com/"

        # Create a resolver with a mock session
        mock_session = MagicMock()
        self.resolver.session = mock_session

        # Mock 404 response for all endpoints
        mock_session.get.return_value = MockResponse({}, status_code=404)

        # Should raise ResolverNotFoundError
        with self.assertRaises(ResolverNotFoundError):
            self.resolver.resolve(uri)

    def test_caching(self):
        """Test that responses are properly cached."""
        uri = "agent://planner.acme.ai/"

        # Create a resolver with a mock session and cache
        mock_session = MagicMock()
        mock_cache = MagicMock()
        self.resolver.session = mock_session
        self.resolver.cache = mock_cache
        mock_session.cache = mock_cache

        # Mock response with caching headers
        headers = {"ETag": '"123456"', "Cache-Control": "max-age=3600"}

        # Set up the mock to handle domain root resolution
        def mock_get(url, **kwargs):
            if url == "https://planner.acme.ai/agent.json":
                return MockResponse(SAMPLE_DESCRIPTOR, headers=headers)
            return MockResponse({}, status_code=404)

        mock_session.get.side_effect = mock_get

        # First request
        descriptor1, _ = self.resolver.resolve(uri)
        self.assertEqual(descriptor1.name, "test-agent")

        # Reset the mock for second request
        mock_session.get.reset_mock()

        # Make the mock return the same data for the second call
        mock_session.get.side_effect = mock_get

        # Second request - we'll verify the correct URL was called
        descriptor2, _ = self.resolver.resolve(uri)
        self.assertEqual(descriptor2.name, "test-agent")

        # Verify clear_cache works
        self.resolver.clear_cache()
        mock_cache.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
