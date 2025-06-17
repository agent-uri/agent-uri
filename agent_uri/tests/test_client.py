"""
Tests for the client module.

This module contains tests for the AgentClient and AgentSession classes.
"""

from unittest.mock import Mock, patch

import pytest

from ..auth import AuthProvider
from ..client import AgentClient, AgentSession
from ..exceptions import InvocationError, ResolutionError, SessionError


# Mock classes for testing
class MockAgentUri:
    """Mock AgentUri for testing."""

    def __init__(
        self,
        scheme="agent",
        transport=None,
        authority="test.com",
        path="capability",
        query=None,
        fragment=None,
    ):
        self.scheme = scheme
        self.transport = transport
        self.authority = authority
        self.host = authority
        self.path = path
        self.query = query or {}
        self.fragment = fragment

    def to_string(self):
        """Return string representation."""
        if self.transport:
            return f"agent+{self.transport}://{self.authority}/{self.path}"
        return f"agent://{self.authority}/{self.path}"


class MockDescriptor:
    """Mock AgentDescriptor for testing."""

    def __init__(self, name="test-agent", version="1.0.0", interaction_model=None):
        self.name = name
        self.version = version
        self.interaction_model = interaction_model
        self.capabilities = []


class MockTransport:
    """Mock transport for testing."""

    def __init__(self, protocol="https"):
        self.protocol = protocol
        self.invoke_calls = []
        self.stream_calls = []

    def invoke(
        self, endpoint, capability, params=None, headers=None, timeout=None, **kwargs
    ):
        """Mock invoke method."""
        call = {
            "endpoint": endpoint,
            "capability": capability,
            "params": params,
            "headers": headers,
            "timeout": timeout,
            "kwargs": kwargs,
        }
        self.invoke_calls.append(call)
        return {"result": "test-response"}

    def stream(
        self, endpoint, capability, params=None, headers=None, timeout=None, **kwargs
    ):
        """Mock stream method."""
        call = {
            "endpoint": endpoint,
            "capability": capability,
            "params": params,
            "headers": headers,
            "timeout": timeout,
            "kwargs": kwargs,
        }
        self.stream_calls.append(call)
        # Return a generator that yields a few chunks
        for i in range(3):
            yield {"chunk": i, "content": f"Test chunk {i}"}


# Tests for AgentClient
class TestAgentClient:
    """Tests for the AgentClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mocks
        self.mock_resolver = Mock()
        self.mock_auth = Mock(spec=AuthProvider)
        self.mock_registry = Mock()
        self.mock_transport = MockTransport()

        # Configure mocks
        self.mock_resolver.resolve.return_value = (
            MockDescriptor(),
            {"endpoint": "https://test.com/agent", "transport": "https"},
        )
        self.mock_auth.get_auth_headers.return_value = {"Authorization": "Bearer test"}
        self.mock_auth.get_auth_params.return_value = {}
        self.mock_auth.is_expired = False
        self.mock_registry.get_transport.return_value = self.mock_transport

        # Create client with mocks
        self.client = AgentClient(
            resolver=self.mock_resolver, auth_provider=self.mock_auth
        )
        # Replace registry with mock
        self.client.registry = self.mock_registry

    @patch("agent_uri.client.parse_agent_uri")
    def test_invoke(self, mock_parse_uri):
        """Test invoking an agent capability."""
        # Configure mock parser
        mock_uri = MockAgentUri()
        mock_parse_uri.return_value = mock_uri

        # Invoke capability
        response = self.client.invoke(
            uri="agent://test.com/capability",
            params={"param": "value"},
            headers={"Custom-Header": "Value"},
        )

        # Verify parser was called
        mock_parse_uri.assert_called_once_with("agent://test.com/capability")

        # Verify resolver was called
        self.mock_resolver.resolve.assert_called_once_with(mock_uri)

        # Verify auth provider was used
        self.mock_auth.get_auth_headers.assert_called_once()
        self.mock_auth.get_auth_params.assert_called_once()

        # Verify transport was used
        self.mock_registry.get_transport.assert_called_once_with("https")
        assert len(self.mock_transport.invoke_calls) == 1

        # Verify invoke parameters
        call = self.mock_transport.invoke_calls[0]
        assert call["endpoint"] == "https://test.com/agent"
        assert call["capability"] == "capability"
        assert call["params"] == {"param": "value"}
        assert "Authorization" in call["headers"]
        assert "Custom-Header" in call["headers"]

        # Verify response
        assert response == {"result": "test-response"}

    @patch("agent_uri.client.parse_agent_uri")
    def test_explicit_transport(self, mock_parse_uri):
        """Test invoking with explicit transport binding."""
        # Configure mock parser
        mock_uri = MockAgentUri(transport="https")
        mock_parse_uri.return_value = mock_uri

        # Invoke capability
        self.client.invoke(uri="agent+https://test.com/capability")

        # Verify resolver was not called (since transport is explicit)
        self.mock_resolver.resolve.assert_not_called()

        # Verify transport was used directly
        self.mock_registry.get_transport.assert_called_once_with("https")
        assert len(self.mock_transport.invoke_calls) == 1

    @patch("agent_uri.client.parse_agent_uri")
    def test_stream(self, mock_parse_uri):
        """Test streaming from an agent capability."""
        # Configure mock parser
        mock_uri = MockAgentUri()
        mock_parse_uri.return_value = mock_uri

        # Stream from capability
        chunks = list(
            self.client.stream(
                uri="agent://test.com/capability",
                params={"param": "value"},
                stream_format="ndjson",
            )
        )

        # Verify parser was called
        mock_parse_uri.assert_called_once_with("agent://test.com/capability")

        # Verify transport was used
        assert len(self.mock_transport.stream_calls) == 1

        # Verify stream parameters
        call = self.mock_transport.stream_calls[0]
        assert call["endpoint"] == "https://test.com/agent"
        assert call["capability"] == "capability"
        assert call["params"] == {"param": "value"}
        assert call["kwargs"]["stream_format"] == "ndjson"

        # Verify chunks received
        assert len(chunks) == 3
        assert chunks[0]["chunk"] == 0
        assert chunks[1]["chunk"] == 1
        assert chunks[2]["chunk"] == 2

    @patch("agent_uri.client.parse_agent_uri")
    def test_get_descriptor(self, mock_parse_uri):
        """Test getting an agent descriptor."""
        # Configure mock parser
        mock_uri = MockAgentUri()
        mock_parse_uri.return_value = mock_uri

        # Get descriptor
        descriptor = self.client.get_descriptor("agent://test.com/capability")

        # Verify parser was called
        mock_parse_uri.assert_called_once_with("agent://test.com/capability")

        # Verify resolver was called
        self.mock_resolver.resolve.assert_called_once_with(mock_uri)

        # Verify descriptor returned
        assert descriptor is not None
        assert descriptor.name == "test-agent"
        assert descriptor.version == "1.0.0"

    @patch("agent_uri.client.parse_agent_uri")
    def test_create_session(self, mock_parse_uri):
        """Test creating a session."""
        # Create session
        session = self.client.create_session(
            uri="agent://test.com/capability", session_id="test-session"
        )

        # Verify session created
        assert isinstance(session, AgentSession)
        assert session.client == self.client
        assert session.base_uri == "agent://test.com/capability"
        assert session.session_id == "test-session"
        assert session.auth_provider == self.mock_auth

    @patch("agent_uri.client.parse_agent_uri")
    def test_error_handling(self, mock_parse_uri):
        """Test error handling in client."""
        # Configure mock to raise exception
        mock_parse_uri.side_effect = ValueError("Invalid URI")

        # Verify ResolutionError is raised
        with pytest.raises(ResolutionError):
            self.client.invoke(uri="invalid:uri")

        # Reset mock
        mock_parse_uri.side_effect = None
        mock_parse_uri.return_value = MockAgentUri()

        # Configure resolver to raise exception
        self.mock_resolver.resolve.side_effect = Exception("Resolution failed")

        # Verify ResolutionError is raised
        with pytest.raises(ResolutionError):
            self.client.invoke(uri="agent://test.com/capability")

        # Reset resolver
        self.mock_resolver.resolve.side_effect = None

        # Configure transport to raise exception
        self.mock_transport.invoke = Mock(side_effect=Exception("Invocation failed"))

        # Verify InvocationError is raised
        with pytest.raises(InvocationError):
            self.client.invoke(uri="agent://test.com/capability")


# Tests for AgentSession
class TestAgentSession:
    """Tests for the AgentSession class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mocks
        self.mock_client = Mock(spec=AgentClient)
        self.mock_auth = Mock(spec=AuthProvider)

        # Configure mock client with auth_provider
        # This is needed because our session implementation accesses it
        self.mock_client.auth_provider = None

        # Create session
        self.session = AgentSession(
            client=self.mock_client,
            uri="agent://test.com/base",
            session_id="test-session",
            auth_provider=self.mock_auth,
        )

        # Configure client mock for invoke
        self.mock_client.invoke.return_value = {"result": "test-response"}

    def test_invoke(self):
        """Test invoking a capability via session."""
        # Invoke capability
        response = self.session.invoke(
            capability="capability",
            params={"param": "value"},
            headers={"Custom-Header": "Value"},
        )

        # Verify client invoke was called
        self.mock_client.invoke.assert_called_once()

        # Get call arguments
        args, kwargs = self.mock_client.invoke.call_args

        # Verify URI construction
        assert kwargs["uri"] == "agent://test.com/base/capability"

        # Verify session headers
        assert "X-Session-ID" in kwargs["headers"]
        assert kwargs["headers"]["X-Session-ID"] == "test-session"
        assert "Custom-Header" in kwargs["headers"]

        # Verify session parameters
        assert "session_id" in kwargs["params"]
        assert kwargs["params"]["session_id"] == "test-session"
        assert "param" in kwargs["params"]
        assert kwargs["params"]["param"] == "value"

        # Verify response
        assert response == {"result": "test-response"}

    def test_stream(self):
        """Test streaming from a capability via session."""
        # Configure client mock for stream
        self.mock_client.stream.return_value = [
            {"chunk": 0, "content": "Test chunk 0"},
            {"chunk": 1, "content": "Test chunk 1"},
            {"chunk": 2, "content": "Test chunk 2"},
        ]

        # Stream from capability
        chunks = list(
            self.session.stream(
                capability="capability",
                params={"param": "value"},
                stream_format="ndjson",
            )
        )

        # Verify client stream was called
        self.mock_client.stream.assert_called_once()

        # Get call arguments
        args, kwargs = self.mock_client.stream.call_args

        # Verify URI construction
        assert kwargs["uri"] == "agent://test.com/base/capability"

        # Verify session headers
        assert "X-Session-ID" in kwargs["headers"]
        assert kwargs["headers"]["X-Session-ID"] == "test-session"

        # Verify session parameters
        assert "session_id" in kwargs["params"]
        assert kwargs["params"]["session_id"] == "test-session"
        assert "param" in kwargs["params"]
        assert kwargs["params"]["param"] == "value"

        # Verify stream_format
        assert kwargs["stream_format"] == "ndjson"

        # Verify chunks received
        assert len(chunks) == 3
        assert chunks[0]["chunk"] == 0
        assert chunks[1]["chunk"] == 1
        assert chunks[2]["chunk"] == 2

    def test_get_descriptor(self):
        """Test getting descriptor via session."""
        # Configure client mock
        mock_descriptor = MockDescriptor()
        self.mock_client.get_descriptor.return_value = mock_descriptor

        # Get descriptor
        descriptor = self.session.get_descriptor()

        # Verify client get_descriptor was called
        self.mock_client.get_descriptor.assert_called_once_with("agent://test.com/base")

        # Verify descriptor returned
        assert descriptor == mock_descriptor

        # Verify descriptor cached
        assert self.session._descriptor == mock_descriptor

        # Reset mock
        self.mock_client.get_descriptor.reset_mock()

        # Get descriptor again (should use cache)
        descriptor2 = self.session.get_descriptor()

        # Verify client get_descriptor was not called again
        self.mock_client.get_descriptor.assert_not_called()

        # Verify descriptor returned from cache
        assert descriptor2 == mock_descriptor

    def test_context_update(self):
        """Test context updating from responses."""
        # Invoke with response that includes context
        self.mock_client.invoke.return_value = {
            "result": "test",
            "context": {"key1": "value1"},
        }
        self.session.invoke("capability")

        # Verify context updated
        assert self.session.context == {"key1": "value1"}

        # Invoke with response that includes session_context
        self.mock_client.invoke.return_value = {
            "result": "test",
            "session_context": {"key2": "value2"},
        }
        self.session.invoke("capability")

        # Verify context updated
        assert self.session.context == {"key1": "value1", "key2": "value2"}

    def test_error_handling(self):
        """Test error handling in session."""
        # Configure client to raise ResolutionError
        self.mock_client.invoke.side_effect = ResolutionError("Resolution failed")

        # Verify SessionError is raised
        with pytest.raises(SessionError):
            self.session.invoke("capability")

        # Configure client to raise InvocationError
        self.mock_client.invoke.side_effect = InvocationError("Invocation failed")

        # Verify InvocationError is propagated
        with pytest.raises(InvocationError):
            self.session.invoke("capability")
