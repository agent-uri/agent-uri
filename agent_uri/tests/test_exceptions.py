"""
Tests for exception classes and error codes.
"""

from agent_uri.exceptions import (
    AgentClientError,
    AgentError,
    AgentServerError,
    AuthenticationError,
    CapabilityError,
    CapabilityNotFoundError,
    ConfigurationError,
    DescriptorError,
    ErrorCode,
    HandlerError,
    InvalidInputError,
    InvocationError,
    ResolutionError,
    ResolverError,
    SessionError,
    StreamingError,
    TransportError,
    TransportTimeoutError,
)


class TestErrorCode:
    """Test error code constants."""

    def test_error_codes_are_strings(self):
        """Test that all error codes are string values."""
        assert isinstance(ErrorCode.INVALID_URI_FORMAT, str)
        assert isinstance(ErrorCode.CAPABILITY_NOT_FOUND, str)
        assert isinstance(ErrorCode.TRANSPORT_ERROR, str)

    def test_client_error_codes(self):
        """Test client error codes start with 4."""
        assert ErrorCode.INVALID_URI_FORMAT.startswith("4")
        assert ErrorCode.AUTHENTICATION_ERROR.startswith("4")
        assert ErrorCode.CAPABILITY_NOT_FOUND.startswith("4")
        assert ErrorCode.TRANSPORT_TIMEOUT.startswith("4")

    def test_server_error_codes(self):
        """Test server error codes start with 5."""
        assert ErrorCode.CAPABILITY_ERROR.startswith("5")
        assert ErrorCode.HANDLER_ERROR.startswith("5")
        assert ErrorCode.TRANSPORT_ERROR.startswith("5")
        assert ErrorCode.UNKNOWN_ERROR.startswith("5")


class TestAgentError:
    """Test base AgentError class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = AgentError("Test message")
        assert str(error) == "[5999] Test message"
        assert error.error_code == ErrorCode.UNKNOWN_ERROR
        assert error.details == {}

    def test_error_with_code(self):
        """Test error with specific code."""
        error = AgentError("Test message", ErrorCode.INVALID_URI_FORMAT)
        assert str(error) == "[4001] Test message"
        assert error.error_code == ErrorCode.INVALID_URI_FORMAT

    def test_error_with_details(self):
        """Test error with details."""
        details = {"key": "value", "number": 42}
        error = AgentError("Test message", ErrorCode.INVALID_INPUT, details)
        assert error.details == details
        assert error.error_code == ErrorCode.INVALID_INPUT


class TestServerExceptions:
    """Test server-side exceptions."""

    def test_capability_not_found_error(self):
        """Test CapabilityNotFoundError."""
        error = CapabilityNotFoundError("test_capability")
        assert "test_capability" in str(error)
        assert error.error_code == ErrorCode.CAPABILITY_NOT_FOUND
        assert error.details["capability_name"] == "test_capability"

    def test_capability_not_found_with_available(self):
        """Test CapabilityNotFoundError with available capabilities."""
        available = ["cap1", "cap2", "cap3"]
        error = CapabilityNotFoundError("missing", available)
        assert "missing" in str(error)
        assert "cap1, cap2, cap3" in str(error)
        assert error.details["available_capabilities"] == available

    def test_capability_error(self):
        """Test CapabilityError."""
        error = CapabilityError("Execution failed", "test_capability")
        assert error.error_code == ErrorCode.CAPABILITY_ERROR
        assert error.details["capability_name"] == "test_capability"

    def test_handler_error(self):
        """Test HandlerError."""
        error = HandlerError("Handler failed", "http")
        assert error.error_code == ErrorCode.HANDLER_ERROR
        assert error.details["handler_type"] == "http"

    def test_descriptor_error(self):
        """Test DescriptorError."""
        error = DescriptorError("Invalid descriptor", "/path/to/agent.json")
        assert error.error_code == ErrorCode.DESCRIPTOR_ERROR
        assert error.details["descriptor_path"] == "/path/to/agent.json"

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Missing config", "database_url")
        assert error.error_code == ErrorCode.CONFIGURATION_ERROR
        assert error.details["config_key"] == "database_url"

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Auth failed", "bearer")
        assert error.error_code == ErrorCode.AUTHENTICATION_ERROR
        assert error.details["auth_scheme"] == "bearer"

    def test_invalid_input_error(self):
        """Test InvalidInputError."""
        validation_errors = ["Field is required", "Invalid format"]
        error = InvalidInputError("Validation failed", "email", validation_errors)
        assert error.error_code == ErrorCode.INVALID_INPUT
        assert error.details["field_name"] == "email"
        assert error.details["validation_errors"] == validation_errors


class TestClientExceptions:
    """Test client-side exceptions."""

    def test_invocation_error(self):
        """Test InvocationError."""
        error = InvocationError("Invocation failed", "agent://test.com", "echo")
        assert error.error_code == ErrorCode.INVOCATION_ERROR
        assert error.details["agent_uri"] == "agent://test.com"
        assert error.details["capability_name"] == "echo"

    def test_resolution_error(self):
        """Test ResolutionError."""
        error = ResolutionError("Resolution failed", "agent://unknown.com")
        assert error.error_code == ErrorCode.RESOLUTION_ERROR
        assert error.details["agent_uri"] == "agent://unknown.com"

    def test_session_error(self):
        """Test SessionError."""
        error = SessionError("Session expired", "session-123")
        assert error.error_code == ErrorCode.SESSION_ERROR
        assert error.details["session_id"] == "session-123"

    def test_transport_error(self):
        """Test TransportError."""
        error = TransportError("Transport failed", "https", "https://example.com")
        assert error.error_code == ErrorCode.TRANSPORT_ERROR
        assert error.details["transport_type"] == "https"
        assert error.details["endpoint"] == "https://example.com"

    def test_transport_timeout_error(self):
        """Test TransportTimeoutError."""
        error = TransportTimeoutError("Timeout", "wss", "wss://example.com", 30.0)
        assert error.error_code == ErrorCode.TRANSPORT_TIMEOUT
        assert error.details["transport_type"] == "wss"
        assert error.details["endpoint"] == "wss://example.com"
        assert error.details["timeout_seconds"] == 30.0

    def test_resolver_error(self):
        """Test ResolverError."""
        error = ResolverError("Resolver failed", "agent://test.com")
        assert error.error_code == ErrorCode.RESOLVER_ERROR
        assert error.details["agent_uri"] == "agent://test.com"

    def test_streaming_error(self):
        """Test StreamingError."""
        error = StreamingError("Stream failed", "stream-456")
        assert error.error_code == ErrorCode.STREAMING_ERROR
        assert error.details["stream_id"] == "stream-456"


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_server_error_inheritance(self):
        """Test server errors inherit from AgentError."""
        error = CapabilityNotFoundError("test")
        assert isinstance(error, AgentServerError)
        assert isinstance(error, AgentError)
        assert isinstance(error, Exception)

    def test_client_error_inheritance(self):
        """Test client errors inherit from AgentError."""
        error = InvocationError("test")
        assert isinstance(error, AgentClientError)
        assert isinstance(error, AgentError)
        assert isinstance(error, Exception)

    def test_transport_timeout_inheritance(self):
        """Test TransportTimeoutError inherits correctly."""
        error = TransportTimeoutError("test")
        assert isinstance(error, TransportTimeoutError)
        assert isinstance(error, AgentClientError)
        assert isinstance(error, AgentError)
        assert isinstance(error, Exception)


class TestExceptionWithoutOptionalParams:
    """Test exceptions work without optional parameters."""

    def test_capability_error_no_params(self):
        """Test CapabilityError without optional params."""
        error = CapabilityError("Basic error")
        assert error.error_code == ErrorCode.CAPABILITY_ERROR
        assert error.details == {}

    def test_handler_error_no_params(self):
        """Test HandlerError without optional params."""
        error = HandlerError("Basic error")
        assert error.details == {}

    def test_resolution_error_no_params(self):
        """Test ResolutionError without optional params."""
        error = ResolutionError("Basic error")
        assert error.details == {}

    def test_invalid_input_error_minimal(self):
        """Test InvalidInputError with minimal params."""
        error = InvalidInputError("Validation failed")
        assert error.details["field_name"] is None
        assert error.details["validation_errors"] == []
