"""
Detailed tests for FastAPI server module functionality.

This module provides comprehensive tests for the uncovered FastAPI functionality
including HTTP request handling, WebSocket connections, and error scenarios.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ..capability import Capability, CapabilityMetadata
from ..exceptions import (
    AuthenticationError,
    CapabilityNotFoundError,
    ConfigurationError,
    HandlerError,
    InvalidInputError,
)
from ..server import FASTAPI_AVAILABLE

if FASTAPI_AVAILABLE:
    from fastapi import HTTPException, Request, WebSocket
    from fastapi.responses import JSONResponse

    from ..server import FastAPIAgentServer
else:
    FastAPIAgentServer = None
    Request = None
    WebSocket = None
    HTTPException = None
    JSONResponse = None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIRequestHandling:
    """Test FastAPI request handling functionality."""

    @pytest.fixture
    def server(self):
        """Create a FastAPI server for testing."""
        return FastAPIAgentServer(
            name="test-agent",
            version="1.0.0",
            description="Test server for detailed testing",
        )

    @pytest.fixture
    def mock_capability(self):
        """Create a mock capability for testing."""
        metadata = CapabilityMetadata(
            name="test_capability",
            description="Test capability for detailed testing",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
        )

        async def test_handler(message: str) -> dict:
            return {"response": f"Processed: {message}"}

        return Capability(test_handler, metadata)

    @pytest.mark.asyncio
    async def test_handle_http_request_get_with_query_params(self, server):
        """Test HTTP GET request with query parameters."""
        # Create a mock Request object
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.query_params = {"param1": "value1", "param2": "value2"}
        mock_request.headers = {"Content-Type": "application/json"}
        mock_request.body = AsyncMock(return_value=b"")

        # Mock the handler to return a specific result
        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"result": "success", "params_received": True}

            response = await server._handle_http_request(mock_request, "/test")

            # Verify response
            assert isinstance(response, JSONResponse)
            assert response.status_code == 200
            content = json.loads(response.body)
            assert content["result"] == "success"

            # Verify handler was called with correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args
            assert call_args[1]["path"] == "/test"
            assert call_args[1]["params"]["param1"] == "value1"
            assert call_args[1]["params"]["param2"] == "value2"

    @pytest.mark.asyncio
    async def test_handle_http_request_post_with_json_body(self, server):
        """Test HTTP POST request with JSON body."""
        # Create a mock Request object with JSON body
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.query_params = {}
        mock_request.headers = {"Content-Type": "application/json"}

        json_body = {"message": "test message", "data": {"nested": "value"}}
        mock_request.body = AsyncMock(return_value=json.dumps(json_body).encode())

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"processed": True}

            await server._handle_http_request(mock_request, "/process")

            # Verify handler received JSON body parameters
            call_args = mock_handler.call_args
            assert call_args[1]["params"]["message"] == "test message"
            assert call_args[1]["params"]["data"]["nested"] == "value"

    @pytest.mark.asyncio
    async def test_handle_http_request_post_with_raw_body(self, server):
        """Test HTTP POST request with non-JSON raw body."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.query_params = {}
        mock_request.headers = {"Content-Type": "text/plain"}
        mock_request.body = AsyncMock(return_value=b"raw text data")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"received_raw": True}

            await server._handle_http_request(mock_request, "/raw")

            # Verify raw body was added as 'body' parameter
            call_args = mock_handler.call_args
            assert call_args[1]["params"]["body"] == "raw text data"

    @pytest.mark.asyncio
    async def test_handle_http_request_with_session_header(self, server):
        """Test HTTP request with session ID in headers."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.query_params = {}
        mock_request.headers = {
            "Content-Type": "application/json",
            "X-Session-ID": "session-12345",
        }
        mock_request.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"session_handled": True}

            await server._handle_http_request(mock_request, "/session")

            # Verify session metadata was passed
            call_args = mock_handler.call_args
            assert "session_metadata" in call_args[1]
            assert call_args[1]["session_metadata"]["session_id"] == "session-12345"

    @pytest.mark.asyncio
    async def test_handle_http_request_capability_not_found_error(self, server):
        """Test HTTP request handling when capability is not found."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.query_params = {}
        mock_request.headers = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = CapabilityNotFoundError("Capability not found")

            with pytest.raises(HTTPException) as exc_info:
                await server._handle_http_request(mock_request, "/nonexistent")

            assert exc_info.value.status_code == 404
            assert "Capability not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_http_request_authentication_error(self, server):
        """Test HTTP request handling with authentication error."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.query_params = {}
        mock_request.headers = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = AuthenticationError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await server._handle_http_request(mock_request, "/secure")

            assert exc_info.value.status_code == 401
            assert "Invalid token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_http_request_invalid_input_error(self, server):
        """Test HTTP request handling with invalid input error."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.query_params = {}
        mock_request.headers = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = InvalidInputError("Invalid parameters")

            with pytest.raises(HTTPException) as exc_info:
                await server._handle_http_request(mock_request, "/validate")

            assert exc_info.value.status_code == 400
            assert "Invalid parameters" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_http_request_handler_error(self, server):
        """Test HTTP request handling with handler error."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.query_params = {}
        mock_request.headers = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = HandlerError("Handler failed")

            with pytest.raises(HTTPException) as exc_info:
                await server._handle_http_request(mock_request, "/error")

            assert exc_info.value.status_code == 500
            assert "Handler failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_http_request_unexpected_error(self, server):
        """Test HTTP request handling with unexpected error."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.query_params = {}
        mock_request.headers = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = ValueError("Unexpected error")

            with pytest.raises(HTTPException) as exc_info:
                await server._handle_http_request(mock_request, "/unexpected")

            assert exc_info.value.status_code == 500
            assert "Internal server error" in str(exc_info.value.detail)
            assert "Unexpected error" in str(exc_info.value.detail)


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIWebSocketHandling:
    """Test FastAPI WebSocket handling functionality."""

    @pytest.fixture
    def server(self):
        """Create a FastAPI server for testing."""
        return FastAPIAgentServer(
            name="websocket-agent",
            version="1.0.0",
            description="WebSocket test server",
        )

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_basic(self, server):
        """Test basic WebSocket connection handling."""
        # Create a mock WebSocket
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(
            return_value='{"message": "test", "session_id": "ws-session-123"}'
        )
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        # Mock the WebSocket handler to yield streaming data
        async def mock_stream():
            yield {"chunk": 1, "data": "first"}
            yield {"chunk": 2, "data": "second"}

        with patch.object(
            server, "handle_websocket_request", return_value=mock_stream()
        ):
            await server._handle_websocket_connection(mock_websocket, "/stream")

            # Verify WebSocket interactions
            mock_websocket.accept.assert_called_once()
            mock_websocket.receive_text.assert_called_once()

            # Verify streaming responses were sent
            assert mock_websocket.send_text.call_count == 2

            # Check the sent data
            sent_calls = mock_websocket.send_text.call_args_list
            first_chunk = json.loads(sent_calls[0][0][0])
            second_chunk = json.loads(sent_calls[1][0][0])

            assert first_chunk["chunk"] == 1
            assert second_chunk["chunk"] == 2

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_with_session_metadata(self, server):
        """Test WebSocket connection with session metadata extraction."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(
            return_value='{"param": "value", "session_id": "ws-session-456"}'
        )
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        async def mock_stream():
            yield {"response": "processed"}

        with patch.object(
            server, "handle_websocket_request", return_value=mock_stream()
        ) as mock_handler:
            await server._handle_websocket_connection(mock_websocket, "/test")

            # Verify session metadata was extracted and passed
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args
            assert "session_metadata" in call_args[1]
            assert call_args[1]["session_metadata"]["session_id"] == "ws-session-456"

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_different_data_types(self, server):
        """Test WebSocket handling different data types."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"test": "data"}')
        mock_websocket.send_text = AsyncMock()
        mock_websocket.send_bytes = AsyncMock()
        mock_websocket.close = AsyncMock()

        async def mock_stream():
            yield {"dict": "data"}  # Dict/list should be JSON encoded
            yield "string data"  # String should be sent directly
            yield b"byte data"  # Bytes should use send_bytes
            yield 42  # Other types should be converted to string

        with patch.object(
            server, "handle_websocket_request", return_value=mock_stream()
        ):
            await server._handle_websocket_connection(mock_websocket, "/types")

            # Verify different send methods were used appropriately
            assert mock_websocket.send_text.call_count == 3  # dict, string, number
            assert mock_websocket.send_bytes.call_count == 1  # bytes

            # Check the sent data
            text_calls = mock_websocket.send_text.call_args_list
            bytes_calls = mock_websocket.send_bytes.call_args_list

            # Dict should be JSON encoded
            first_text = text_calls[0][0][0]
            assert json.loads(first_text) == {"dict": "data"}

            # String should be sent as-is
            second_text = text_calls[1][0][0]
            assert second_text == "string data"

            # Number should be stringified
            third_text = text_calls[2][0][0]
            assert third_text == "42"

            # Bytes should use send_bytes
            sent_bytes = bytes_calls[0][0][0]
            assert sent_bytes == b"byte data"

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_capability_not_found(self, server):
        """Test WebSocket connection with capability not found error."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"test": "data"}')
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=CapabilityNotFoundError("WebSocket capability not found"),
        ):
            await server._handle_websocket_connection(mock_websocket, "/missing")

            # Verify error message was sent
            mock_websocket.send_text.assert_called_once()
            error_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert error_message["error"] == "CapabilityNotFound"
            assert "WebSocket capability not found" in error_message["message"]

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_authentication_error(self, server):
        """Test WebSocket connection with authentication error."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"test": "data"}')
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=AuthenticationError("WebSocket auth failed"),
        ):
            await server._handle_websocket_connection(mock_websocket, "/secure")

            # Verify error message was sent
            error_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert error_message["error"] == "AuthenticationError"
            assert "WebSocket auth failed" in error_message["message"]

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_invalid_input_error(self, server):
        """Test WebSocket connection with invalid input error."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"test": "data"}')
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=InvalidInputError("WebSocket input invalid"),
        ):
            await server._handle_websocket_connection(mock_websocket, "/validate")

            error_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert error_message["error"] == "InvalidInput"
            assert "WebSocket input invalid" in error_message["message"]

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_handler_error(self, server):
        """Test WebSocket connection with handler error."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"test": "data"}')
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=HandlerError("WebSocket handler failed"),
        ):
            await server._handle_websocket_connection(mock_websocket, "/error")

            error_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert error_message["error"] == "HandlerError"
            assert "WebSocket handler failed" in error_message["message"]

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_unexpected_error(self, server):
        """Test WebSocket connection with unexpected error."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"test": "data"}')
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=RuntimeError("Unexpected WebSocket error"),
        ):
            await server._handle_websocket_connection(mock_websocket, "/unexpected")

            error_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert error_message["error"] == "InternalServerError"
            assert "Unexpected WebSocket error" in error_message["message"]

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_cleanup(self, server):
        """Test WebSocket connection cleanup in finally block."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"test": "data"}')
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        # Even with successful execution, should close WebSocket
        async def mock_stream():
            yield {"success": True}

        with patch.object(
            server, "handle_websocket_request", return_value=mock_stream()
        ):
            await server._handle_websocket_connection(mock_websocket, "/cleanup")

            # Verify WebSocket was closed
            mock_websocket.close.assert_called_once()


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIConfigurationEdgeCases:
    """Test FastAPI configuration and edge cases."""

    @pytest.mark.asyncio
    async def test_handle_http_request_no_http_handler(self):
        """Test HTTP request when no HTTP handler is configured."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Remove HTTP handler to simulate configuration error
        del server._handlers["http"]

        with pytest.raises(ConfigurationError, match="No HTTP handler registered"):
            await server.handle_http_request("/test", {})

    @pytest.mark.asyncio
    async def test_handle_websocket_request_no_websocket_handler(self):
        """Test WebSocket request when no WebSocket handler is configured."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Remove WebSocket handler to simulate configuration error
        del server._handlers["websocket"]

        with pytest.raises(ConfigurationError, match="No WebSocket handler registered"):
            chunks = []
            async for chunk in server.handle_websocket_request("/test", {}):
                chunks.append(chunk)

    @pytest.mark.asyncio
    async def test_handle_http_request_handler_returns_non_coroutine(self):
        """Test HTTP request when handler returns unexpected type."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Mock handler to return non-coroutine
        with patch.object(
            server._handlers["http"], "handle_request", return_value="not_a_coroutine"
        ):
            with pytest.raises(
                ConfigurationError, match="HTTP handler returned unexpected result type"
            ):
                await server.handle_http_request("/test", {})

    @pytest.mark.asyncio
    async def test_handle_websocket_request_non_async_iterable(self):
        """Test WebSocket request when handler returns non-async iterable."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Create a mock coroutine that returns a single value (not an async generator)
        async def mock_single_result():
            return {"single": "response"}

        with patch.object(
            server._handlers["websocket"],
            "handle_request",
            return_value=mock_single_result(),
        ):
            chunks = []
            async for chunk in server.handle_websocket_request("/test", {}):
                chunks.append(chunk)

            # Should handle single response
            assert len(chunks) == 1
            assert chunks[0] == {"single": "response"}


@pytest.mark.skipif(FASTAPI_AVAILABLE, reason="Testing when FastAPI is not available")
class TestFastAPIImportHandling:
    """Test behavior when FastAPI is not available."""

    def test_fastapi_server_placeholder_methods(self):
        """Test placeholder methods when FastAPI is not available."""
        # This tests the placeholder class that's defined when FastAPI is unavailable
        # The placeholder should raise ImportError on instantiation

        # Import the placeholder class directly from the module
        from ..server import FastAPIAgentServer

        # Should raise ImportError when instantiating
        with pytest.raises(ImportError, match="FastAPI is not installed"):
            FastAPIAgentServer("test", "1.0.0")

    @pytest.mark.asyncio
    async def test_fastapi_unavailable_placeholder_methods(self):
        """Test that placeholder methods exist when FastAPI is unavailable."""
        from ..server import FastAPIAgentServer

        # We can test the method signatures exist without instantiating
        assert hasattr(FastAPIAgentServer, "handle_http_request")
        assert hasattr(FastAPIAgentServer, "handle_websocket_request")
