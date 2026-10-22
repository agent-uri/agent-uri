"""
Tests for exception classes and error codes.

Aligned with draft-narvaneni-agent-uri-03 error-code extensions.
"""

from agent_uri.exceptions import (
    AgentClientError,
    AgentError,
    AgentGoneError,
    AgentServerError,
    AuthenticationError,
    ConfigurationError,
    ContentNegotiationError,
    DelegationError,
    DescriptorError,
    DIDResolutionError,
    ErrorCode,
    HandlerError,
    InvalidInputError,
    InvocationError,
    KeyDiscoveryError,
    RedirectViolationError,
    ResolutionError,
    ResolverError,
    ScopeNarrowingViolationError,
    SessionError,
    SignatureVerificationError,
    SkillError,
    SkillNotFoundError,
    SSRFViolationError,
    StreamingError,
    TransportError,
    TransportNotSupportedError,
    TransportTimeoutError,
)


class TestErrorCode:
    def test_error_codes_are_strings(self):
        assert isinstance(ErrorCode.INVALID_URI_FORMAT, str)
        assert isinstance(ErrorCode.SKILL_NOT_FOUND, str)
        assert isinstance(ErrorCode.TRANSPORT_ERROR, str)

    def test_client_error_codes_start_with_4(self):
        assert ErrorCode.INVALID_URI_FORMAT.startswith("4")
        assert ErrorCode.AUTHENTICATION_ERROR.startswith("4")
        assert ErrorCode.SKILL_NOT_FOUND.startswith("4")
        assert ErrorCode.TRANSPORT_TIMEOUT.startswith("4")
        assert ErrorCode.CONTENT_NOT_ACCEPTABLE.startswith("4")
        assert ErrorCode.AGENT_GONE.startswith("4")

    def test_server_error_codes_start_with_5(self):
        assert ErrorCode.SKILL_ERROR.startswith("5")
        assert ErrorCode.HANDLER_ERROR.startswith("5")
        assert ErrorCode.TRANSPORT_ERROR.startswith("5")
        assert ErrorCode.SSRF_VIOLATION.startswith("5")
        assert ErrorCode.SIGNATURE_VERIFICATION_ERROR.startswith("5")
        assert ErrorCode.DELEGATION_ERROR.startswith("5")
        assert ErrorCode.UNKNOWN_ERROR.startswith("5")


class TestAgentError:
    def test_basic_error(self):
        e = AgentError("Test message")
        assert str(e) == "[5999] Test message"
        assert e.error_code == ErrorCode.UNKNOWN_ERROR
        assert e.details == {}

    def test_error_with_code(self):
        e = AgentError("Msg", ErrorCode.INVALID_URI_FORMAT)
        assert str(e) == "[4001] Msg"
        assert e.error_code == ErrorCode.INVALID_URI_FORMAT

    def test_error_with_details(self):
        details = {"k": "v", "n": 42}
        e = AgentError("Msg", ErrorCode.INVALID_INPUT, details)
        assert e.details == details


class TestServerExceptions:
    def test_skill_not_found_error(self):
        e = SkillNotFoundError("echo")
        assert "echo" in str(e)
        assert e.error_code == ErrorCode.SKILL_NOT_FOUND
        assert e.details["skill_id"] == "echo"

    def test_skill_not_found_with_available(self):
        available = ["s1", "s2", "s3"]
        e = SkillNotFoundError("missing", available)
        assert "missing" in str(e)
        assert "s1, s2, s3" in str(e)
        assert e.details["available_skills"] == available

    def test_skill_error(self):
        e = SkillError("Execution failed", "echo")
        assert e.error_code == ErrorCode.SKILL_ERROR
        assert e.details["skill_id"] == "echo"

    def test_handler_error(self):
        e = HandlerError("Handler failed", "http")
        assert e.error_code == ErrorCode.HANDLER_ERROR
        assert e.details["handler_type"] == "http"

    def test_descriptor_error(self):
        e = DescriptorError("bad", "/path/to/agent.json")
        assert e.error_code == ErrorCode.DESCRIPTOR_ERROR
        assert e.details["descriptor_path"] == "/path/to/agent.json"

    def test_configuration_error(self):
        e = ConfigurationError("Missing", "database_url")
        assert e.error_code == ErrorCode.CONFIGURATION_ERROR
        assert e.details["config_key"] == "database_url"

    def test_authentication_error(self):
        e = AuthenticationError("Auth failed", "bearer")
        assert e.error_code == ErrorCode.AUTHENTICATION_ERROR
        assert e.details["auth_scheme"] == "bearer"

    def test_invalid_input_error(self):
        validation = ["Field is required", "Invalid format"]
        e = InvalidInputError("Validation failed", "email", validation)
        assert e.error_code == ErrorCode.INVALID_INPUT
        assert e.details["field_name"] == "email"
        assert e.details["validation_errors"] == validation

    def test_content_negotiation_error(self):
        e = ContentNegotiationError(
            "Can't produce", requested="text/plain", supported=["application/json"]
        )
        assert e.error_code == ErrorCode.CONTENT_NOT_ACCEPTABLE
        assert e.details["requested"] == "text/plain"
        assert e.details["supported"] == ["application/json"]

    def test_agent_gone_error(self):
        e = AgentGoneError("Gone", agent_uri="agent://x.test/")
        assert e.error_code == ErrorCode.AGENT_GONE
        assert e.details["agent_uri"] == "agent://x.test/"


class TestResolverExceptions:
    def test_ssrf_violation(self):
        e = SSRFViolationError("blocked", target="127.0.0.1")
        assert e.error_code == ErrorCode.SSRF_VIOLATION
        assert e.details["target"] == "127.0.0.1"

    def test_redirect_violation(self):
        e = RedirectViolationError("no", target="http://169.254.169.254/")
        assert e.error_code == ErrorCode.REDIRECT_VIOLATION

    def test_did_resolution_error(self):
        e = DIDResolutionError("did fail", did="did:web:x.test")
        assert e.error_code == ErrorCode.DID_RESOLUTION_ERROR
        assert e.details["did"] == "did:web:x.test"


class TestClientExceptions:
    def test_invocation_error(self):
        e = InvocationError("fail", "agent://test.com", "echo")
        assert e.error_code == ErrorCode.INVOCATION_ERROR
        assert e.details["agent_uri"] == "agent://test.com"
        assert e.details["skill_id"] == "echo"

    def test_resolution_error(self):
        e = ResolutionError("fail", "agent://unknown.com")
        assert e.error_code == ErrorCode.RESOLUTION_ERROR
        assert e.details["agent_uri"] == "agent://unknown.com"

    def test_session_error(self):
        e = SessionError("expired", "session-123")
        assert e.error_code == ErrorCode.SESSION_ERROR
        assert e.details["session_id"] == "session-123"

    def test_transport_error(self):
        e = TransportError("fail", "https", "https://example.com")
        assert e.error_code == ErrorCode.TRANSPORT_ERROR
        assert e.details["transport_type"] == "https"
        assert e.details["endpoint"] == "https://example.com"

    def test_transport_timeout_error(self):
        e = TransportTimeoutError("Timeout", "wss", "wss://example.com", 30.0)
        assert e.error_code == ErrorCode.TRANSPORT_TIMEOUT
        assert e.details["timeout_seconds"] == 30.0

    def test_transport_not_supported_error(self):
        e = TransportNotSupportedError("no grpc yet", transport_type="grpc")
        assert e.error_code == ErrorCode.TRANSPORT_UNAVAILABLE
        assert e.details["transport_type"] == "grpc"

    def test_resolver_error(self):
        e = ResolverError("fail", "agent://test.com")
        assert e.error_code == ErrorCode.RESOLVER_ERROR

    def test_streaming_error(self):
        e = StreamingError("fail", "stream-456")
        assert e.error_code == ErrorCode.STREAMING_ERROR


class TestSignatureAndDelegationExceptions:
    def test_signature_verification_error(self):
        e = SignatureVerificationError("bad sig", component="signature")
        assert e.error_code == ErrorCode.SIGNATURE_VERIFICATION_ERROR
        assert e.details["component"] == "signature"

    def test_key_discovery_error(self):
        e = KeyDiscoveryError("no key", source="jwks_uri")
        assert e.error_code == ErrorCode.KEY_DISCOVERY_ERROR
        assert e.details["source"] == "jwks_uri"

    def test_delegation_error(self):
        e = DelegationError("chain broken", reason="step_2")
        assert e.error_code == ErrorCode.DELEGATION_ERROR
        assert e.details["reason"] == "step_2"

    def test_scope_narrowing_violation(self):
        e = ScopeNarrowingViolationError(
            "widened", outer_scope="read", inner_scope="read write"
        )
        assert e.error_code == ErrorCode.SCOPE_NARROWING_VIOLATION
        assert isinstance(e, DelegationError)


class TestExceptionHierarchy:
    def test_server_error_inheritance(self):
        e = SkillNotFoundError("test")
        assert isinstance(e, AgentServerError)
        assert isinstance(e, AgentError)
        assert isinstance(e, Exception)

    def test_client_error_inheritance(self):
        e = InvocationError("test")
        assert isinstance(e, AgentClientError)
        assert isinstance(e, AgentError)

    def test_transport_timeout_inheritance(self):
        e = TransportTimeoutError("test")
        assert isinstance(e, TransportError)
        assert isinstance(e, AgentClientError)
