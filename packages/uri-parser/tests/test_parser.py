"""
Tests for the agent:// URI parser.

This module contains comprehensive tests for the AgentUri parser,
ensuring it correctly handles all components as defined in the RFC draft.
"""

import unittest
from agent_uri.parser import (
    AgentUri,
    parse_agent_uri,
    is_valid_agent_uri,
    AgentUriError
)


class TestAgentUriParser(unittest.TestCase):
    """Test case for the AgentUri parser implementation."""

    def test_basic_agent_uri(self):
        """Test parsing a basic agent URI."""
        uri = "agent://acme.ai/planning/generate-itinerary"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.scheme, "agent")
        self.assertIsNone(agent_uri.transport)
        self.assertEqual(agent_uri.authority, "acme.ai")
        self.assertEqual(agent_uri.host, "acme.ai")
        self.assertEqual(agent_uri.path, "planning/generate-itinerary")
        self.assertEqual(agent_uri.query, {})
        self.assertIsNone(agent_uri.fragment)
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_agent_uri_with_query(self):
        """Test parsing an agent URI with query parameters."""
        uri = "agent://acme.ai/planning/generate-itinerary?city=Paris&days=3"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.scheme, "agent")
        self.assertEqual(agent_uri.authority, "acme.ai")
        self.assertEqual(agent_uri.path, "planning/generate-itinerary")
        self.assertEqual(agent_uri.query, {"city": "Paris", "days": "3"})
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_agent_uri_with_fragment(self):
        """Test parsing an agent URI with a fragment."""
        uri = "agent://acme.ai/planning/generate-itinerary#details"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.scheme, "agent")
        self.assertEqual(agent_uri.authority, "acme.ai")
        self.assertEqual(agent_uri.path, "planning/generate-itinerary")
        self.assertEqual(agent_uri.fragment, "details")
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_agent_uri_with_transport(self):
        """Test parsing an agent URI with explicit transport binding."""
        uri = "agent+https://acme.com/assistants/chatgpt?query=hello"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.scheme, "agent")
        self.assertEqual(agent_uri.transport, "https")
        self.assertEqual(agent_uri.authority, "acme.com")
        self.assertEqual(agent_uri.path, "assistants/chatgpt")
        self.assertEqual(agent_uri.query, {"query": "hello"})
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_agent_uri_with_userinfo(self):
        """Test parsing an agent URI with userinfo in authority."""
        uri = "agent://user:password@acme.ai/planning"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.authority, "user:password@acme.ai")
        self.assertEqual(agent_uri.userinfo, "user:password")
        self.assertEqual(agent_uri.host, "acme.ai")
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_agent_uri_with_port(self):
        """Test parsing an agent URI with port in authority."""
        uri = "agent://acme.ai:8080/planning"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.authority, "acme.ai:8080")
        self.assertEqual(agent_uri.host, "acme.ai")
        self.assertEqual(agent_uri.port, 8080)
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_agent_uri_with_duplicate_query_params(self):
        """Test parsing an agent URI with duplicate query parameters."""
        uri = "agent://acme.ai/planning?tag=travel&tag=vacation"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.query, {"tag": ["travel", "vacation"]})
        
        # Round-trip may reorder params but should contain both values
        self.assertIn("tag=travel", str(agent_uri))
        self.assertIn("tag=vacation", str(agent_uri))

    def test_agent_uri_with_complex_components(self):
        """Test parsing an agent URI with all components."""
        uri = ("agent+wss://user@example.com:8080/path/to/agent"
               "?param1=value1&param2=value2#section")
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.scheme, "agent")
        self.assertEqual(agent_uri.transport, "wss")
        self.assertEqual(agent_uri.authority, "user@example.com:8080")
        self.assertEqual(agent_uri.userinfo, "user")
        self.assertEqual(agent_uri.host, "example.com")
        self.assertEqual(agent_uri.port, 8080)
        self.assertEqual(agent_uri.path, "path/to/agent")
        self.assertEqual(agent_uri.query, {"param1": "value1", "param2": "value2"})
        self.assertEqual(agent_uri.fragment, "section")

    def test_local_agent_uri(self):
        """Test parsing a local agent URI."""
        uri = "agent+local://claude"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.scheme, "agent")
        self.assertEqual(agent_uri.transport, "local")
        self.assertEqual(agent_uri.authority, "claude")
        self.assertEqual(agent_uri.host, "claude")
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_did_agent_uri(self):
        """Test parsing an agent URI with DID-based authority."""
        uri = "agent://did:web:acme.com:agent:researcher/get-article?doi=10.1234"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.scheme, "agent")
        self.assertEqual(agent_uri.authority, "did:web:acme.com:agent:researcher")
        self.assertEqual(agent_uri.host, "did:web:acme.com:agent:researcher")
        self.assertEqual(agent_uri.path, "get-article")
        self.assertEqual(agent_uri.query, {"doi": "10.1234"})
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_empty_path(self):
        """Test parsing an agent URI with empty path."""
        uri = "agent://acme.ai"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.scheme, "agent")
        self.assertEqual(agent_uri.authority, "acme.ai")
        self.assertEqual(agent_uri.path, "")
        
        # Test round-trip
        self.assertEqual(str(agent_uri), uri)

    def test_invalid_agent_uri(self):
        """Test that invalid agent URIs raise appropriate exceptions."""
        invalid_uris = [
            "http://acme.ai/agent",       # Wrong scheme
            "agent:",                      # Missing //
            "agent:///planning",           # Missing authority
            "agent+invalidprotocol://example.com",  # Invalid transport binding
        ]
        
        for uri in invalid_uris:
            with self.subTest(uri=uri):
                self.assertFalse(is_valid_agent_uri(uri))
                with self.assertRaises(AgentUriError):
                    parse_agent_uri(uri)

    def test_query_params_with_special_chars(self):
        """Test handling of query parameters with special characters."""
        uri = "agent://acme.ai/planning?q=hello+world&filter=a%3Db"
        agent_uri = parse_agent_uri(uri)
        
        self.assertEqual(agent_uri.query, {"q": "hello+world", "filter": "a=b"})
        
        # Test round-trip with encoding
        self.assertEqual(str(agent_uri), uri)

    def test_create_from_components(self):
        """Test creating an AgentUri from components."""
        agent_uri = AgentUri(
            scheme="agent",
            transport="https",
            authority="example.com:8080",
            path="path/to/resource",
            query={"param": "value"},
            fragment="section",
            host="example.com",
            port=8080
        )
        
        expected_uri = "agent+https://example.com:8080/path/to/resource?param=value#section"
        self.assertEqual(str(agent_uri), expected_uri)

    def test_to_dict(self):
        """Test converting an AgentUri to a dictionary."""
        uri = "agent+https://example.com/path?query=value#fragment"
        agent_uri = parse_agent_uri(uri)
        
        uri_dict = agent_uri.to_dict()
        
        self.assertEqual(uri_dict["scheme"], "agent")
        self.assertEqual(uri_dict["transport"], "https")
        self.assertEqual(uri_dict["authority"], "example.com")
        self.assertEqual(uri_dict["path"], "path")
        self.assertEqual(uri_dict["query"], {"query": "value"})
        self.assertEqual(uri_dict["fragment"], "fragment")
        self.assertEqual(uri_dict["full_uri"], uri)


if __name__ == "__main__":
    unittest.main()
