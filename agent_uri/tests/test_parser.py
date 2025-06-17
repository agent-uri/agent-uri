"""
Tests for the parser module.

This module contains comprehensive tests for the agent:// URI parser.
"""

import pytest

from ..parser import AgentUri, AgentUriError, parse_agent_uri


class TestAgentUriError:
    """Test the AgentUriError exception class."""

    def test_agent_uri_error_message(self):
        """Test AgentUriError with custom message."""
        error_msg = "Test error message"
        error = AgentUriError(error_msg)
        assert str(error) == error_msg

    def test_agent_uri_error_inheritance(self):
        """Test AgentUriError inherits from Exception."""
        error = AgentUriError("test")
        assert isinstance(error, Exception)


class TestAgentUriDataclass:
    """Test the AgentUri dataclass functionality."""

    def test_agent_uri_default_values(self):
        """Test AgentUri with default values."""
        uri = AgentUri()
        assert uri.scheme == "agent"
        assert uri.transport is None
        assert uri.authority == ""
        assert uri.path == ""
        assert uri.query == {}
        assert uri.fragment is None
        assert uri.userinfo is None
        assert uri.host == ""
        assert uri.port is None

    def test_agent_uri_custom_values(self):
        """Test AgentUri with custom values."""
        uri = AgentUri(
            scheme="agent",
            transport="https",
            authority="example.com:8080",
            path="/my-agent",
            query={"param": "value"},
            fragment="section",
            userinfo="user",
            host="example.com",
            port=8080,
        )
        assert uri.scheme == "agent"
        assert uri.transport == "https"
        assert uri.authority == "example.com:8080"
        assert uri.path == "/my-agent"
        assert uri.query == {"param": "value"}
        assert uri.fragment == "section"
        assert uri.userinfo == "user"
        assert uri.host == "example.com"
        assert uri.port == 8080

    def test_agent_uri_post_init_query_none(self):
        """Test AgentUri post_init with None query."""
        uri = AgentUri(query=None)
        assert uri.query == {}

    def test_agent_uri_post_init_query_dict(self):
        """Test AgentUri post_init with existing query dict."""
        query = {"key": "value"}
        uri = AgentUri(query=query)
        assert uri.query == query


class TestAgentUriProperties:
    """Test AgentUri properties and methods."""

    def test_full_scheme_no_transport(self):
        """Test full_scheme property without transport."""
        uri = AgentUri()
        assert uri.full_scheme == "agent"

    def test_full_scheme_with_transport(self):
        """Test full_scheme property with transport."""
        uri = AgentUri(transport="https")
        assert uri.full_scheme == "agent+https"

    def test_to_string_minimal(self):
        """Test to_string with minimal URI."""
        uri = AgentUri(host="example.com")
        result = uri.to_string()
        assert result == "agent://example.com"

    def test_to_string_with_transport(self):
        """Test to_string with transport."""
        uri = AgentUri(transport="https", host="example.com")
        result = uri.to_string()
        assert result == "agent+https://example.com"

    def test_to_string_with_port(self):
        """Test to_string with port."""
        uri = AgentUri(host="example.com", port=8080)
        result = uri.to_string()
        assert result == "agent://example.com:8080"

    def test_to_string_with_userinfo(self):
        """Test to_string with userinfo."""
        uri = AgentUri(userinfo="user", host="example.com")
        result = uri.to_string()
        assert result == "agent://user@example.com"

    def test_to_string_with_path(self):
        """Test to_string with path."""
        uri = AgentUri(host="example.com", path="/my-agent")
        result = uri.to_string()
        assert result == "agent://example.com/my-agent"

    def test_to_string_with_path_no_slash(self):
        """Test to_string with path not starting with slash."""
        uri = AgentUri(host="example.com", path="my-agent")
        result = uri.to_string()
        assert result == "agent://example.com/my-agent"

    def test_to_string_with_query(self):
        """Test to_string with query parameters."""
        uri = AgentUri(host="example.com", query={"param": "value"})
        result = uri.to_string()
        assert result == "agent://example.com?param=value"

    def test_to_string_with_query_list(self):
        """Test to_string with query parameter list."""
        uri = AgentUri(host="example.com", query={"param": ["value1", "value2"]})
        result = uri.to_string()
        assert "param=value1" in result
        assert "param=value2" in result

    def test_to_string_with_fragment(self):
        """Test to_string with fragment."""
        uri = AgentUri(host="example.com", fragment="section")
        result = uri.to_string()
        assert result == "agent://example.com#section"

    def test_to_string_complex(self):
        """Test to_string with complex URI."""
        uri = AgentUri(
            transport="wss",
            userinfo="user",
            host="example.com",
            port=9000,
            path="/my-agent/echo",
            query={"token": "abc123"},
            fragment="chat",
        )
        result = uri.to_string()
        expected = "agent+wss://user@example.com:9000/my-agent/echo?token=abc123#chat"
        assert result == expected

    def test_to_string_with_authority(self):
        """Test to_string using authority instead of host/port."""
        uri = AgentUri(authority="example.com:8080")
        result = uri.to_string()
        assert result == "agent://example.com:8080"

    def test_str_method(self):
        """Test __str__ method."""
        uri = AgentUri(host="example.com", path="/agent")
        assert str(uri) == "agent://example.com/agent"

    def test_to_dict(self):
        """Test to_dict method."""
        uri = AgentUri(
            scheme="agent",
            transport="https",
            authority="example.com:8080",
            userinfo="user",
            host="example.com",
            port=8080,
            path="/agent",
            query={"param": "value"},
            fragment="section",
        )
        result = uri.to_dict()
        expected = {
            "scheme": "agent",
            "transport": "https",
            "authority": "example.com:8080",
            "userinfo": "user",
            "host": "example.com",
            "port": 8080,
            "path": "/agent",
            "query": {"param": "value"},
            "fragment": "section",
            "full_uri": "agent+https://example.com:8080/agent?param=value#section",
        }
        assert result == expected


class TestAgentUriClassMethod:
    """Test the AgentUri.parse() class method."""

    def test_agent_uri_parse_method(self):
        """Test AgentUri.parse() class method."""
        uri_string = "agent://example.com/my-agent"
        uri = AgentUri.parse(uri_string)
        assert isinstance(uri, AgentUri)
        assert uri.host == "example.com"
        assert uri.path == "my-agent"

    def test_agent_uri_parse_with_transport(self):
        """Test AgentUri.parse() with transport."""
        uri_string = "agent+https://example.com/my-agent"
        uri = AgentUri.parse(uri_string)
        assert uri.transport == "https"
        assert uri.host == "example.com"

    def test_agent_uri_parse_invalid_uri(self):
        """Test AgentUri.parse() with invalid URI."""
        with pytest.raises(AgentUriError):
            AgentUri.parse("http://example.com")


class TestParseAgentUri:
    """Test the parse_agent_uri function."""

    def test_parse_basic_agent_uri(self):
        """Test parsing basic agent:// URI."""
        uri = parse_agent_uri("agent://example.com")
        assert uri.scheme == "agent"
        assert uri.transport is None
        assert uri.host == "example.com"
        assert uri.path == ""

    def test_parse_agent_uri_with_transport(self):
        """Test parsing agent URI with transport binding."""
        uri = parse_agent_uri("agent+https://example.com")
        assert uri.scheme == "agent"
        assert uri.transport == "https"
        assert uri.host == "example.com"

    def test_parse_agent_uri_with_port(self):
        """Test parsing agent URI with port."""
        uri = parse_agent_uri("agent://example.com:8080")
        assert uri.host == "example.com"
        assert uri.port == 8080

    def test_parse_agent_uri_with_path(self):
        """Test parsing agent URI with path."""
        uri = parse_agent_uri("agent://example.com/my-agent/echo")
        assert uri.host == "example.com"
        assert uri.path == "my-agent/echo"

    def test_parse_agent_uri_with_query(self):
        """Test parsing agent URI with query parameters."""
        uri = parse_agent_uri("agent://example.com?param=value&other=test")
        assert uri.host == "example.com"
        assert "param" in uri.query
        assert "other" in uri.query

    def test_parse_agent_uri_with_fragment(self):
        """Test parsing agent URI with fragment."""
        uri = parse_agent_uri("agent://example.com#section")
        assert uri.host == "example.com"
        assert uri.fragment == "section"

    def test_parse_agent_uri_with_userinfo(self):
        """Test parsing agent URI with userinfo."""
        uri = parse_agent_uri("agent://user:pass@example.com")
        assert uri.host == "example.com"
        assert uri.userinfo == "user:pass"

    def test_parse_complex_agent_uri(self):
        """Test parsing complex agent URI with all components."""
        uri_string = (
            "agent+wss://user:pass@example.com:9000/my-agent/echo"
            "?token=abc123&mode=chat#section"
        )
        uri = parse_agent_uri(uri_string)
        assert uri.scheme == "agent"
        assert uri.transport == "wss"
        assert uri.userinfo == "user:pass"
        assert uri.host == "example.com"
        assert uri.port == 9000
        assert uri.path == "my-agent/echo"
        assert "token" in uri.query
        assert "mode" in uri.query
        assert uri.fragment == "section"

    def test_parse_agent_uri_case_insensitive_transport(self):
        """Test parsing agent URI with case variations in transport."""
        # Transport validation is case-sensitive and only allows lowercase
        with pytest.raises(AgentUriError, match="Invalid transport protocol"):
            parse_agent_uri("agent+HTTPS://example.com")

    def test_parse_agent_uri_with_special_chars_in_query(self):
        """Test parsing agent URI with special characters in query."""
        uri = parse_agent_uri(
            "agent://example.com?message=hello%20world&symbols=%21%40%23"
        )
        assert uri.host == "example.com"
        assert "message" in uri.query
        assert "symbols" in uri.query


class TestParseAgentUriErrors:
    """Test error handling in parse_agent_uri function."""

    def test_parse_non_agent_scheme(self):
        """Test parsing URI without agent scheme."""
        with pytest.raises(AgentUriError, match="URI must start with 'agent'"):
            parse_agent_uri("http://example.com")

    def test_parse_invalid_scheme(self):
        """Test parsing URI with invalid scheme."""
        with pytest.raises(AgentUriError, match="URI must start with 'agent'"):
            parse_agent_uri("ftp://example.com")

    def test_parse_empty_uri(self):
        """Test parsing empty URI."""
        with pytest.raises(AgentUriError, match="URI must start with 'agent'"):
            parse_agent_uri("")

    def test_parse_malformed_uri(self):
        """Test parsing malformed URI."""
        with pytest.raises(AgentUriError, match="Invalid agent URI format"):
            parse_agent_uri("agent")  # Missing ://


class TestParseAgentUriEdgeCases:
    """Test edge cases in URI parsing."""

    def test_parse_agent_uri_minimal(self):
        """Test parsing minimal valid agent URI."""
        uri = parse_agent_uri("agent://")
        assert uri.scheme == "agent"
        assert uri.host == ""

    def test_parse_agent_uri_localhost(self):
        """Test parsing agent URI with localhost."""
        uri = parse_agent_uri("agent://localhost:8765")
        assert uri.host == "localhost"
        assert uri.port == 8765

    def test_parse_agent_uri_ip_address(self):
        """Test parsing agent URI with IP address."""
        uri = parse_agent_uri("agent://192.168.1.1:8080")
        assert uri.host == "192.168.1.1"
        assert uri.port == 8080

    def test_parse_agent_uri_multiple_slashes_in_path(self):
        """Test parsing agent URI with multiple slashes in path."""
        uri = parse_agent_uri("agent://example.com/path/to/agent")
        assert uri.path == "path/to/agent"

    def test_parse_agent_uri_query_with_multiple_values(self):
        """Test parsing agent URI with multiple values for same query parameter."""
        uri = parse_agent_uri("agent://example.com?param=value1&param=value2")
        assert uri.host == "example.com"
        # The behavior for duplicate parameters depends on implementation
        assert "param" in uri.query

    def test_parse_agent_uri_with_encoded_characters(self):
        """Test parsing agent URI with URL-encoded characters."""
        uri = parse_agent_uri("agent://example.com/path%20with%20spaces")
        assert uri.host == "example.com"
        assert "path" in uri.path

    def test_parse_agent_uri_fragment_only(self):
        """Test parsing agent URI with only fragment."""
        uri = parse_agent_uri("agent://example.com#fragment")
        assert uri.host == "example.com"
        assert uri.fragment == "fragment"
        assert uri.path == ""

    def test_parse_agent_uri_query_only(self):
        """Test parsing agent URI with only query."""
        uri = parse_agent_uri("agent://example.com?param=value")
        assert uri.host == "example.com"
        assert uri.path == ""
        assert "param" in uri.query


class TestParseAgentUriTransportBindings:
    """Test different transport binding formats."""

    def test_parse_agent_uri_https_transport(self):
        """Test parsing agent URI with HTTPS transport."""
        uri = parse_agent_uri("agent+https://example.com")
        assert uri.transport == "https"

    def test_parse_agent_uri_wss_transport(self):
        """Test parsing agent URI with WebSocket Secure transport."""
        uri = parse_agent_uri("agent+wss://example.com")
        assert uri.transport == "wss"

    def test_parse_agent_uri_http_transport(self):
        """Test parsing agent URI with HTTP transport."""
        uri = parse_agent_uri("agent+http://example.com")
        assert uri.transport == "http"

    def test_parse_agent_uri_ws_transport(self):
        """Test parsing agent URI with WebSocket transport."""
        uri = parse_agent_uri("agent+ws://example.com")
        assert uri.transport == "ws"

    def test_parse_agent_uri_custom_transport(self):
        """Test parsing agent URI with custom transport."""
        # Custom transport is not in the valid protocols list
        with pytest.raises(AgentUriError, match="Invalid transport protocol: custom"):
            parse_agent_uri("agent+custom://example.com")

    def test_parse_agent_uri_transport_with_numbers(self):
        """Test parsing agent URI with transport containing numbers."""
        # http2 is not in the valid protocols list
        with pytest.raises(AgentUriError, match="Invalid transport protocol: http2"):
            parse_agent_uri("agent+http2://example.com")

    def test_parse_agent_uri_transport_with_hyphens(self):
        """Test parsing agent URI with transport containing hyphens."""
        # my-transport is not in the valid protocols list
        with pytest.raises(
            AgentUriError, match="Invalid transport protocol: my-transport"
        ):
            parse_agent_uri("agent+my-transport://example.com")


class TestAgentUriRoundTrip:
    """Test round-trip parsing and serialization."""

    @pytest.mark.parametrize(
        "uri_string",
        [
            "agent://example.com",
            "agent+https://example.com:8080",
            "agent://user@example.com/path",
            "agent://example.com?param=value",
            "agent://example.com#fragment",
            "agent+wss://user:pass@example.com:9000/path?param=value#fragment",
        ],
    )
    def test_parse_and_serialize_roundtrip(self, uri_string):
        """Test that parsing and serializing returns equivalent URIs."""
        # Parse the URI
        parsed = parse_agent_uri(uri_string)

        # Serialize it back
        serialized = parsed.to_string()

        # Parse the serialized version
        reparsed = parse_agent_uri(serialized)

        # Compare key components (exact string match may differ due to encoding)
        assert parsed.scheme == reparsed.scheme
        assert parsed.transport == reparsed.transport
        assert parsed.host == reparsed.host
        assert parsed.port == reparsed.port
        assert parsed.userinfo == reparsed.userinfo
        assert parsed.fragment == reparsed.fragment

    def test_parse_serialize_preserves_components(self):
        """Test that parsing and serializing preserves all components."""
        original = "agent+https://user@example.com:8080/my-agent?param=value#section"
        parsed = parse_agent_uri(original)

        assert parsed.scheme == "agent"
        assert parsed.transport == "https"
        assert parsed.userinfo == "user"
        assert parsed.host == "example.com"
        assert parsed.port == 8080
        assert parsed.path == "my-agent"
        assert "param" in parsed.query
        assert parsed.fragment == "section"
