"""
Tests for the HTTPS transport.

This module contains tests for the HttpsTransport class.
"""

import json

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
