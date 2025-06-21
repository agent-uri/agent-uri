"""
Tests for the HTTPS transport.

This module contains tests for the HttpsTransport class.
"""

import json
from unittest.mock import Mock, patch

import pytest
import requests
import requests_mock

from ..base import TransportError, TransportTimeoutError
from ..transports.https import HttpsTransport


class TestHttpsTransport:
    """Tests for the HttpsTransport class."""

    @pytest.fixture
    def transport(self):
        """Create a transport instance for testing."""
        return HttpsTransport()

    def test_protocol_property(self, transport):
        """Test the protocol property."""
        assert transport.protocol == "https"

    def test_invoke_get(self, transport):
        """Test invoking a capability with GET method."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/test-capability?param1=value1",
                json={"result": "success"},
            )

            result = transport.invoke(
                endpoint="https://example.com",
                capability="test-capability",
                params={"param1": "value1"},
                method="GET",
            )

            assert result == {"result": "success"}

    def test_invoke_post(self, transport):
        """Test invoking a capability with POST method."""
        with requests_mock.Mocker() as m:
            # Set up the mock to match a POST request with JSON body
            m.post("https://example.com/test-capability", json={"result": "success"})

            result = transport.invoke(
                endpoint="https://example.com",
                capability="test-capability",
                params={"param1": "value1"},
                method="POST",
            )

            # Verify the result
            assert result == {"result": "success"}

            # Verify that the JSON body was sent correctly
            request = m.request_history[0]
            assert request.method == "POST"
            assert json.loads(request.body) == {"param1": "value1"}
            assert request.headers["Content-Type"] == "application/json"

    def test_invoke_default_method(self, transport):
        """Test invoking a capability with default method selection."""
        with requests_mock.Mocker() as m:
            # With params, should use POST by default
            m.post("https://example.com/test-capability", json={"result": "post"})

            result = transport.invoke(
                endpoint="https://example.com",
                capability="test-capability",
                params={"param1": "value1"},
            )

            assert result == {"result": "post"}

            # Without params, should use GET by default
            m.get("https://example.com/test-capability", json={"result": "get"})

            result = transport.invoke(
                endpoint="https://example.com", capability="test-capability"
            )

            assert result == {"result": "get"}

    def test_invoke_with_headers(self, transport):
        """Test invoking a capability with custom headers."""
        with requests_mock.Mocker() as m:
            m.get("https://example.com/test-capability", json={"result": "success"})

            transport.invoke(
                endpoint="https://example.com",
                capability="test-capability",
                headers={"X-Custom-Header": "value"},
            )

            request = m.request_history[0]
            assert request.headers["X-Custom-Header"] == "value"

    def test_invoke_with_auth(self, transport):
        """Test invoking a capability with authentication."""
        with requests_mock.Mocker() as m:
            m.get("https://example.com/test-capability", json={"result": "success"})

            transport.invoke(
                endpoint="https://example.com",
                capability="test-capability",
                auth=("username", "password"),
            )

            request = m.request_history[0]
            assert request.headers["Authorization"].startswith("Basic ")

    def test_invoke_error_status(self, transport):
        """Test invoking a capability that returns an error status."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/test-capability",
                status_code=500,
                json={"error": "Server error"},
            )

            with pytest.raises(TransportError) as excinfo:
                transport.invoke(
                    endpoint="https://example.com", capability="test-capability"
                )

            assert "500" in str(excinfo.value)
            assert "Server error" in str(excinfo.value)

    def test_invoke_timeout(self, transport):
        """Test invoking a capability that times out."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/test-capability", exc=requests.exceptions.Timeout
            )

            with pytest.raises(TransportTimeoutError):
                transport.invoke(
                    endpoint="https://example.com", capability="test-capability"
                )

    def test_invoke_connection_error(self, transport):
        """Test invoking a capability with a connection error."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/test-capability",
                exc=requests.exceptions.ConnectionError,
            )

            with pytest.raises(TransportError) as excinfo:
                transport.invoke(
                    endpoint="https://example.com", capability="test-capability"
                )

            assert "Connection error" in str(excinfo.value)

    def test_build_url(self, transport):
        """Test building a URL from endpoint and capability."""
        # Method is private but we want to test it directly
        url = transport._build_url("https://example.com", "test-capability")
        assert url == "https://example.com/test-capability"

        # Should handle trailing slashes in endpoint
        url = transport._build_url("https://example.com/", "test-capability")
        assert url == "https://example.com/test-capability"

        # Should handle leading slashes in capability
        url = transport._build_url("https://example.com", "/test-capability")
        assert url == "https://example.com/test-capability"

    def test_parse_response(self, transport):
        """Test parsing responses of different content types."""

        # Create a mock response object
        class MockResponse:
            def __init__(self, content_type, data):
                self.headers = {"Content-Type": content_type}
                self._data = data

            def json(self):
                if isinstance(self._data, (dict, list)):
                    return self._data
                return json.loads(self._data)

            @property
            def text(self):
                if isinstance(self._data, str):
                    return self._data
                return json.dumps(self._data)

        # Test JSON content type
        json_response = MockResponse("application/json", {"key": "value"})
        result = transport._parse_response(json_response)
        assert result == {"key": "value"}

        # Test plain text content type
        text_response = MockResponse("text/plain", "Hello, world!")
        result = transport._parse_response(text_response)
        assert result == "Hello, world!"

        # Test unknown content type with JSON data
        unknown_response = MockResponse("application/unknown", {"key": "value"})
        result = transport._parse_response(unknown_response)
        assert result == {"key": "value"}

        # Test unknown content type with non-JSON data
        unknown_response = MockResponse("application/unknown", "non-json")
        result = transport._parse_response(unknown_response)
        assert result == "non-json"

    def test_extract_error_detail(self, transport):
        """Test extracting error details from different response formats."""

        # Create a mock response object
        class MockResponse:
            def __init__(self, content_type, data, status_code=500):
                self.headers = {"Content-Type": content_type}
                self._data = data
                self.status_code = status_code

            def json(self):
                return self._data

            @property
            def text(self):
                if isinstance(self._data, str):
                    return self._data
                return json.dumps(self._data)

        # Test RFC7807 problem+json
        problem_response = MockResponse(
            "application/problem+json",
            {"title": "Error Title", "detail": "Detailed error message"},
        )
        result = transport._extract_error_detail(problem_response)
        assert "Error Title" in result
        assert "Detailed error message" in result

        # Test regular JSON with error field
        json_response = MockResponse("application/json", {"error": "Error message"})
        result = transport._extract_error_detail(json_response)
        assert "Error message" in result

        # Test regular JSON with nested error field
        json_response = MockResponse(
            "application/json", {"error": {"message": "Nested error message"}}
        )
        result = transport._extract_error_detail(json_response)
        assert "Nested error message" in result

        # Test plain text
        text_response = MockResponse("text/plain", "Plain text error")
        result = transport._extract_error_detail(text_response)
        assert "Plain text error" in result

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        # Create a custom session
        custom_session = requests.Session()
        custom_session.headers["X-Custom"] = "value"

        transport = HttpsTransport(
            session=custom_session,
            verify_ssl=False,
            user_agent="TestAgent/2.0",
        )

        assert transport._session is custom_session
        assert transport._verify_ssl is False
        assert transport._user_agent == "TestAgent/2.0"
        assert transport.session.headers["User-Agent"] == "TestAgent/2.0"
        assert transport.session.headers["Accept"] == "application/json"
        assert transport.session.headers["X-Custom"] == "value"

    def test_initialization_defaults(self, transport):
        """Test default initialization."""
        assert transport._verify_ssl is True
        assert transport._user_agent == "AgentURI-Transport/1.0"
        assert transport.session.headers["User-Agent"] == "AgentURI-Transport/1.0"
        assert transport.session.headers["Accept"] == "application/json"

    def test_session_property(self, transport):
        """Test session property getter."""
        assert isinstance(transport.session, requests.Session)
        assert transport.session is transport._session

    def test_format_body(self, transport):
        """Test body formatting."""
        data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        body = transport.format_body(data)
        assert isinstance(body, str)
        assert json.loads(body) == data

    def test_prepare_request_args(self, transport):
        """Test preparing request arguments."""
        # Test with all parameters
        args = transport._prepare_request_args(
            params={"param1": "value1"},
            headers={"X-Custom": "header"},
            timeout=30,
            auth=("user", "pass"),
            allow_redirects=False,
        )

        assert args["params"] == {"param1": "value1"}
        assert args["headers"] == {"X-Custom": "header"}
        assert args["timeout"] == 30
        assert args["auth"] == ("user", "pass")
        assert args["allow_redirects"] is False
        assert args["verify"] is True  # From instance default

        # Test with verify override
        args = transport._prepare_request_args(verify=False)
        assert args["verify"] is False

        # Test with no params
        args = transport._prepare_request_args()
        assert "params" not in args
        assert "headers" not in args
        assert "timeout" not in args
        assert args["verify"] is True

    def test_invoke_post_with_query_params(self, transport):
        """Test POST with query parameters handled through prepare_request_args."""
        with requests_mock.Mocker() as m:
            m.post(
                "https://example.com/test",
                json={"result": "success"},
            )

            # The implementation doesn't support separate query params for POST
            # Instead, test that params go in the body for POST
            result = transport.invoke(
                endpoint="https://example.com",
                capability="test",
                params={"body": "data", "query": "param"},  # All go in body for POST
                method="POST",
            )

            assert result == {"result": "success"}
            request = m.request_history[0]
            assert json.loads(request.body) == {"body": "data", "query": "param"}

    def test_invoke_put_method(self, transport):
        """Test invoking with PUT method."""
        with requests_mock.Mocker() as m:
            m.put("https://example.com/test", json={"result": "updated"})

            result = transport.invoke(
                endpoint="https://example.com",
                capability="test",
                params={"data": "update"},
                method="PUT",
            )

            assert result == {"result": "updated"}
            request = m.request_history[0]
            assert request.method == "PUT"
            assert json.loads(request.body) == {"data": "update"}

    def test_invoke_delete_method(self, transport):
        """Test invoking with DELETE method."""
        with requests_mock.Mocker() as m:
            m.delete("https://example.com/test/123", json={"result": "deleted"})

            result = transport.invoke(
                endpoint="https://example.com",
                capability="test/123",
                method="DELETE",
            )

            assert result == {"result": "deleted"}
            request = m.request_history[0]
            assert request.method == "DELETE"

    def test_invoke_ssl_verification(self):
        """Test SSL verification settings."""
        # Transport with SSL verification disabled
        transport = HttpsTransport(verify_ssl=False)

        with requests_mock.Mocker() as m:
            m.get("https://example.com/test", json={"result": "success"})

            transport.invoke(
                endpoint="https://example.com",
                capability="test",
            )

            # Note: requests_mock doesn't actually verify SSL,
            # but we can check the request was made
            assert m.last_request is not None

    def test_invoke_request_exception_without_response(self, transport):
        """Test handling RequestException without response object."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/test",
                exc=requests.exceptions.RequestException("Generic error"),
            )

            with pytest.raises(TransportError) as excinfo:
                transport.invoke(
                    endpoint="https://example.com",
                    capability="test",
                )

            assert "Request failed: Generic error" in str(excinfo.value)

    def test_invoke_http_error_with_problem_json(self, transport):
        """Test handling HTTP error with RFC7807 problem details."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/test",
                status_code=400,
                headers={"Content-Type": "application/problem+json"},
                json={
                    "type": "https://example.com/errors/bad-request",
                    "title": "Bad Request",
                    "detail": "The request was invalid",
                    "status": 400,
                },
            )

            with pytest.raises(TransportError) as excinfo:
                transport.invoke(
                    endpoint="https://example.com",
                    capability="test",
                )

            assert "HTTP 400 error" in str(excinfo.value)
            assert "Bad Request" in str(excinfo.value)
            assert "The request was invalid" in str(excinfo.value)

    def test_stream_ndjson_format(self, transport):
        """Test streaming with newline-delimited JSON format."""
        with requests_mock.Mocker() as m:
            # Mock a streaming response with NDJSON
            response_data = b'{"chunk": 1}\n{"chunk": 2}\n{"chunk": 3}\n'
            m.get(
                "https://example.com/stream",
                content=response_data,
                headers={"Content-Type": "application/x-ndjson"},
            )

            chunks = list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                    stream_format="ndjson",
                )
            )

            assert len(chunks) == 3
            assert chunks[0] == {"chunk": 1}
            assert chunks[1] == {"chunk": 2}
            assert chunks[2] == {"chunk": 3}

    def test_stream_ndjson_with_invalid_line(self, transport):
        """Test streaming NDJSON with invalid JSON line."""
        with requests_mock.Mocker() as m:
            # Mix valid JSON with invalid lines
            response_data = b'{"chunk": 1}\ninvalid json\n{"chunk": 2}\n'
            m.get(
                "https://example.com/stream",
                content=response_data,
            )

            chunks = list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                    stream_format="ndjson",
                )
            )

            assert len(chunks) == 3
            assert chunks[0] == {"chunk": 1}
            assert chunks[1] == "invalid json"  # Falls back to raw string
            assert chunks[2] == {"chunk": 2}

    def test_stream_sse_format(self, transport):
        """Test streaming with Server-Sent Events format."""
        with requests_mock.Mocker() as m:
            # Mock SSE response
            sse_data = (
                b'data: {"event": 1}\n\n'
                b'data: {"event": 2}\n\n'
                b'data: {"event": 3}\n\n'
            )
            m.get(
                "https://example.com/stream",
                content=sse_data,
                headers={"Content-Type": "text/event-stream"},
            )

            # Mock SSEClient to simulate event parsing
            with patch("agent_uri.transport.transports.https.sseclient") as mock_sse:
                mock_client = Mock()
                mock_sse.SSEClient.return_value = mock_client

                # Create mock events
                mock_events = [
                    Mock(data='{"event": 1}'),
                    Mock(data='{"event": 2}'),
                    Mock(data='{"event": 3}'),
                ]
                mock_client.events.return_value = iter(mock_events)

                chunks = list(
                    transport.stream(
                        endpoint="https://example.com",
                        capability="stream",
                        stream_format="sse",
                    )
                )

                assert len(chunks) == 3
                assert chunks[0] == {"event": 1}
                assert chunks[1] == {"event": 2}
                assert chunks[2] == {"event": 3}

    def test_stream_sse_with_non_json_data(self, transport):
        """Test SSE streaming with non-JSON data."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/stream",
                content=b"data: plain text\n\n",
            )

            with patch("agent_uri.transport.transports.https.sseclient") as mock_sse:
                mock_client = Mock()
                mock_sse.SSEClient.return_value = mock_client

                # Create mock event with non-JSON data
                mock_event = Mock(data="plain text")
                mock_client.events.return_value = iter([mock_event])

                chunks = list(
                    transport.stream(
                        endpoint="https://example.com",
                        capability="stream",
                        stream_format="sse",
                    )
                )

                assert len(chunks) == 1
                assert chunks[0] == "plain text"

    def test_stream_raw_format(self, transport):
        """Test streaming with raw format (binary chunks)."""
        with requests_mock.Mocker() as m:
            # Mock raw binary data
            raw_data = b"chunk1" + b"chunk2" + b"chunk3"
            m.get(
                "https://example.com/stream",
                content=raw_data,
            )

            # Collect all chunks
            chunks = list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                    stream_format="raw",
                )
            )

            # Combine chunks
            combined = b"".join(chunks)
            assert combined == raw_data

    def test_stream_with_post_method(self, transport):
        """Test streaming with POST method and parameters."""
        with requests_mock.Mocker() as m:
            response_data = b'{"chunk": 1}\n{"chunk": 2}\n'
            m.post(
                "https://example.com/stream",
                content=response_data,
            )

            chunks = list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                    params={"filter": "active"},
                    method="POST",
                    stream_format="ndjson",
                )
            )

            assert len(chunks) == 2
            assert chunks[0] == {"chunk": 1}
            assert chunks[1] == {"chunk": 2}

            # Verify request details
            request = m.request_history[0]
            assert request.method == "POST"
            assert json.loads(request.body) == {"filter": "active"}

    def test_stream_timeout(self, transport):
        """Test streaming timeout."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/stream",
                exc=requests.exceptions.Timeout,
            )

            with pytest.raises(TransportTimeoutError) as excinfo:
                list(
                    transport.stream(
                        endpoint="https://example.com",
                        capability="stream",
                        timeout=1,
                    )
                )

            assert "timed out" in str(excinfo.value)

    def test_stream_connection_error(self, transport):
        """Test streaming connection error."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/stream",
                exc=requests.exceptions.ConnectionError("Connection refused"),
            )

            with pytest.raises(TransportError) as excinfo:
                list(
                    transport.stream(
                        endpoint="https://example.com",
                        capability="stream",
                    )
                )

            assert "Connection error" in str(excinfo.value)

    def test_stream_http_error(self, transport):
        """Test streaming HTTP error."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/stream",
                status_code=503,
                json={"error": "Service unavailable"},
            )

            with pytest.raises(TransportError) as excinfo:
                list(
                    transport.stream(
                        endpoint="https://example.com",
                        capability="stream",
                    )
                )

            assert "HTTP 503 error" in str(excinfo.value)
            assert "Service unavailable" in str(excinfo.value)

    def test_stream_request_exception_without_response(self, transport):
        """Test streaming RequestException without response."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/stream",
                exc=requests.exceptions.RequestException("Stream error"),
            )

            with pytest.raises(TransportError) as excinfo:
                list(
                    transport.stream(
                        endpoint="https://example.com",
                        capability="stream",
                    )
                )

            assert "Streaming request failed: Stream error" in str(excinfo.value)

    def test_stream_with_custom_headers(self, transport):
        """Test streaming with custom headers."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/stream",
                content=b'{"data": "test"}\n',
            )

            list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                    headers={"X-Stream-Token": "abc123"},
                )
            )

            request = m.request_history[0]
            assert request.headers["X-Stream-Token"] == "abc123"

    def test_stream_default_method_selection(self, transport):
        """Test stream default method selection."""
        with requests_mock.Mocker() as m:
            # Without params, should use GET
            m.get(
                "https://example.com/stream",
                content=b'{"data": "get"}\n',
            )

            chunks = list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                )
            )

            assert len(chunks) == 1
            assert chunks[0] == {"data": "get"}

            # With params, should use POST
            m.post(
                "https://example.com/stream",
                content=b'{"data": "post"}\n',
            )

            chunks = list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                    params={"param": "value"},
                )
            )

            assert len(chunks) == 1
            assert chunks[0] == {"data": "post"}

    def test_parse_response_with_parse_error(self, transport):
        """Test response parsing with JSON parse error."""

        # Mock response with invalid JSON
        class MockResponse:
            headers = {"Content-Type": "application/json"}
            text = "invalid json"

            def json(self):
                raise ValueError("Invalid JSON")

        # Should fall back to text
        result = transport._parse_response(MockResponse())
        assert result == "invalid json"

    def test_extract_error_detail_with_json_message_field(self, transport):
        """Test error extraction with message field in JSON."""

        class MockResponse:
            headers = {"Content-Type": "application/json"}
            status_code = 400
            _data = {"message": "Validation failed"}

            def json(self):
                return self._data

            @property
            def text(self):
                return json.dumps(self._data)

        result = transport._extract_error_detail(MockResponse())
        assert result == "Validation failed"

    def test_extract_error_detail_fallback(self, transport):
        """Test error extraction fallback cases."""

        # Test with JSON parse error
        class MockResponse:
            headers = {"Content-Type": "application/json"}
            status_code = 500

            def json(self):
                raise ValueError("Invalid JSON")

            @property
            def text(self):
                return ""

        result = transport._extract_error_detail(MockResponse())
        assert result == "HTTP 500 error"

        # Test with non-dict error field
        class MockResponse2:
            headers = {"Content-Type": "application/json"}
            status_code = 400
            _data = {"error": "Simple string error"}

            def json(self):
                return self._data

            @property
            def text(self):
                return json.dumps(self._data)

        result = transport._extract_error_detail(MockResponse2())
        assert result == "Simple string error"

    def test_extract_error_detail_unknown_json(self, transport):
        """Test error extraction with JSON without error fields."""

        class MockResponse:
            headers = {"Content-Type": "application/json"}
            status_code = 400
            _data = {"status": "failed", "code": "ERR001"}

            def json(self):
                return self._data

            @property
            def text(self):
                return json.dumps(self._data)

        result = transport._extract_error_detail(MockResponse())
        assert result == "Unknown error"

    def test_build_url_edge_cases(self, transport):
        """Test URL building edge cases."""
        # Multiple slashes
        url = transport._build_url("https://example.com///", "///test///")
        assert url == "https://example.com/test///"

        # Path with query string
        url = transport._build_url("https://example.com", "test?param=value")
        assert url == "https://example.com/test?param=value"

        # Complex capability path
        url = transport._build_url("https://example.com/api/v1", "agents/test/invoke")
        assert url == "https://example.com/api/v1/agents/test/invoke"

    def test_invoke_with_allow_redirects(self, transport):
        """Test invoke with redirect control."""
        with requests_mock.Mocker() as m:
            # Set up redirect
            m.get(
                "https://example.com/test",
                status_code=301,
                headers={"Location": "https://example.com/redirected"},
            )
            m.get(
                "https://example.com/redirected",
                json={"result": "redirected"},
            )

            # Test with redirects allowed (default)
            result = transport.invoke(
                endpoint="https://example.com",
                capability="test",
                allow_redirects=True,
            )

            assert result == {"result": "redirected"}
            assert len(m.request_history) == 2

    def test_stream_empty_response(self, transport):
        """Test streaming with empty response."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/stream",
                content=b"",
            )

            chunks = list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                    stream_format="ndjson",
                )
            )

            assert len(chunks) == 0

    def test_stream_with_query_params_in_post(self, transport):
        """Test POST streaming with all params in body."""
        with requests_mock.Mocker() as m:
            m.post(
                "https://example.com/stream",
                content=b'{"data": "filtered"}\n',
            )

            chunks = list(
                transport.stream(
                    endpoint="https://example.com",
                    capability="stream",
                    params={
                        "body_param": "value",
                        "filter": "active",
                    },  # All go in body
                    method="POST",
                    stream_format="ndjson",
                )
            )

            assert len(chunks) == 1
            assert chunks[0] == {"data": "filtered"}

            request = m.request_history[0]
            assert json.loads(request.body) == {
                "body_param": "value",
                "filter": "active",
            }


class TestHttpsTransportIntegration:
    """Integration tests for HTTPS transport."""

    @pytest.fixture
    def transport(self):
        """Create transport for integration tests."""
        return HttpsTransport()

    def test_full_request_response_cycle(self, transport):
        """Test complete request/response cycle with various options."""
        with requests_mock.Mocker() as m:
            # Mock complex response
            m.post(
                "https://api.example.com/v1/agents/test-agent/capabilities/process",
                json={
                    "id": "12345",
                    "status": "completed",
                    "result": {"processed": True, "items": 10},
                },
                headers={
                    "X-Request-ID": "req-12345",
                    "X-Rate-Limit": "100",
                },
            )

            result = transport.invoke(
                endpoint="https://api.example.com/v1",
                capability="agents/test-agent/capabilities/process",
                params={"input": "data", "options": {"validate": True}},
                headers={
                    "Authorization": "Bearer token123",
                    "X-Client-ID": "client-001",
                },
                timeout=30,
                method="POST",
            )

            assert result["id"] == "12345"
            assert result["status"] == "completed"
            assert result["result"]["processed"] is True

            # Verify request details
            request = m.request_history[0]
            assert request.headers["Authorization"] == "Bearer token123"
            assert request.headers["X-Client-ID"] == "client-001"
            assert request.headers["Content-Type"] == "application/json"
            assert request.timeout == 30

    def test_error_handling_cascade(self, transport):
        """Test various error scenarios in sequence."""
        with requests_mock.Mocker() as m:
            # 1. Connection error
            m.get(
                "https://example.com/test1",
                exc=requests.exceptions.ConnectionError("DNS failure"),
            )

            with pytest.raises(TransportError) as exc:
                transport.invoke("https://example.com", "test1")
            assert "Connection error" in str(exc.value)

            # 2. Timeout error
            m.get(
                "https://example.com/test2",
                exc=requests.exceptions.Timeout(),
            )

            with pytest.raises(TransportTimeoutError):
                transport.invoke("https://example.com", "test2")

            # 3. HTTP error with details
            m.get(
                "https://example.com/test3",
                status_code=422,
                json={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid input parameters",
                        "details": [
                            {"field": "name", "error": "required"},
                            {"field": "age", "error": "must be positive"},
                        ],
                    }
                },
            )

            with pytest.raises(TransportError) as exc:
                transport.invoke("https://example.com", "test3")
            assert "422" in str(exc.value)
            assert "Invalid input parameters" in str(exc.value)

    def test_streaming_large_response(self, transport):
        """Test streaming a large response efficiently."""
        with requests_mock.Mocker() as m:
            # Generate large NDJSON response
            large_data = b""
            for i in range(1000):
                large_data += f'{{"index": {i}, "data": "item-{i}"}}\n'.encode()

            m.get(
                "https://example.com/large-stream",
                content=large_data,
            )

            # Stream and count chunks
            chunk_count = 0
            first_chunk = None
            last_chunk = None

            for chunk in transport.stream(
                endpoint="https://example.com",
                capability="large-stream",
                stream_format="ndjson",
            ):
                if first_chunk is None:
                    first_chunk = chunk
                last_chunk = chunk
                chunk_count += 1

            assert chunk_count == 1000
            assert first_chunk == {"index": 0, "data": "item-0"}
            assert last_chunk == {"index": 999, "data": "item-999"}

    def test_session_persistence(self):
        """Test that transport uses the provided session."""
        # Create transport with custom session
        session = requests.Session()
        session.headers["X-Custom-Session"] = "test123"
        transport = HttpsTransport(session=session)

        with requests_mock.Mocker(session=session) as m:
            m.get(
                "https://example.com/test",
                json={"status": "success"},
            )

            # Make request
            transport.invoke("https://example.com", "test")

            # Verify custom session header was sent
            request = m.request_history[0]
            assert request.headers["X-Custom-Session"] == "test123"
            assert request.headers["User-Agent"] == "AgentURI-Transport/1.0"

    @pytest.mark.slow
    def test_concurrent_requests_isolation(self):
        """Test that concurrent requests don't interfere."""
        import threading
        import time

        transport = HttpsTransport()
        results = {}
        errors = {}
        lock = threading.Lock()

        with requests_mock.Mocker() as m:
            # Set up all mocks before threading
            for i in range(5):
                m.get(
                    f"https://example.com/test{i}",
                    json={"id": i, "thread_safe": True},
                )

            def make_request(id: int, delay: float):
                """Make a request with a specific delay."""
                try:
                    time.sleep(delay)
                    result = transport.invoke(
                        "https://example.com",
                        f"test{id}",
                    )
                    with lock:
                        results[id] = result
                except Exception as e:
                    with lock:
                        errors[id] = e

            # Start multiple threads
            threads = []
            for i in range(5):
                t = threading.Thread(
                    target=make_request,
                    args=(i, 0.001 * i),  # Smaller delays
                )
                threads.append(t)
                t.start()

            # Wait for all to complete
            for t in threads:
                t.join(timeout=5)

            # Verify all requests completed successfully
            assert len(results) == 5
            assert len(errors) == 0
            for i in range(5):
                assert results[i]["id"] == i
                assert results[i]["thread_safe"] is True
