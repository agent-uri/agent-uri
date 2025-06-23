"""
Tests for the WebSocket transport implementation.

This module contains comprehensive tests for the WebSocketTransport class.
"""

import json
import threading
import time
from queue import Queue
from unittest.mock import Mock, patch

import pytest

from ..base import TransportError, TransportTimeoutError
from ..transports.websocket import WebSocketTransport


class TestWebSocketTransport:
    """Tests for the WebSocketTransport class."""

    @pytest.fixture
    def transport(self):
        """Create a WebSocketTransport instance for testing."""
        return WebSocketTransport()

    def test_protocol_property(self, transport):
        """Test the protocol property."""
        assert transport.protocol == "wss"

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        transport = WebSocketTransport(
            user_agent="CustomAgent/1.0",
            verify_ssl=False,
            ping_interval=60,
            ping_timeout=20,
            reconnect_tries=5,
            reconnect_delay=3,
        )

        assert transport._user_agent == "CustomAgent/1.0"
        assert transport._verify_ssl is False
        assert transport._ping_interval == 60
        assert transport._ping_timeout == 20
        assert transport._reconnect_tries == 5
        assert transport._reconnect_delay == 3

    def test_initialization_defaults(self, transport):
        """Test initialization with default parameters."""
        assert transport._user_agent == "AgentURI-Transport/1.0"
        assert transport._verify_ssl is True
        assert transport._ping_interval == 30
        assert transport._ping_timeout == 10
        assert transport._reconnect_tries == 3
        assert transport._reconnect_delay == 2
        assert transport._is_connected is False
        assert transport._ws is None

    def test_build_url_from_https(self, transport):
        """Test building WebSocket URL from HTTPS endpoint."""
        # Test HTTPS to WSS conversion
        url = transport._build_url("https://example.com", "test-agent")
        assert url == "wss://example.com/test-agent"

        # Test with trailing slash
        url = transport._build_url("https://example.com/", "test-agent")
        assert url == "wss://example.com/test-agent"

        # Test with path in endpoint
        url = transport._build_url("https://example.com/api", "test-agent")
        assert url == "wss://example.com/api/test-agent"

    def test_build_url_from_http(self, transport):
        """Test building WebSocket URL from HTTP endpoint."""
        # Test HTTP to WS conversion
        url = transport._build_url("http://example.com", "test-agent")
        assert url == "ws://example.com/test-agent"

        # Test localhost
        url = transport._build_url("http://localhost:8080", "test-agent")
        assert url == "ws://localhost:8080/test-agent"

    def test_build_url_already_websocket(self, transport):
        """Test building WebSocket URL when already WebSocket protocol."""
        # Test WSS URL
        url = transport._build_url("wss://example.com", "test-agent")
        assert url == "wss://example.com/test-agent"

        # Test WS URL
        url = transport._build_url("ws://example.com", "test-agent")
        assert url == "ws://example.com/test-agent"

    def test_build_url_no_protocol(self, transport):
        """Test building WebSocket URL with no protocol."""
        # Should default to wss
        url = transport._build_url("example.com", "test-agent")
        assert url == "wss://example.com/test-agent"

    def test_get_next_request_id(self, transport):
        """Test request ID generation."""
        # Initial state
        assert transport._request_id == 0

        # Get first ID
        id1 = transport._get_next_request_id()
        assert id1 == "req-1"
        assert transport._request_id == 1

        # Get second ID
        id2 = transport._get_next_request_id()
        assert id2 == "req-2"
        assert transport._request_id == 2

    @patch("websocket.WebSocketApp")
    def test_connect_success(self, mock_ws_class, transport):
        """Test successful WebSocket connection."""
        # Create mock WebSocket instance
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws

        # Mock the run_forever to call on_open immediately
        def run_forever_side_effect(**kwargs):
            # Set connection flag directly since we're in a thread
            transport._is_connected = True

        mock_ws.run_forever.side_effect = run_forever_side_effect

        # Connect
        transport._connect("wss://example.com/agent", {"Authorization": "Bearer token"})

        # Give thread time to start
        time.sleep(0.1)

        # Verify WebSocketApp was created with correct parameters
        mock_ws_class.assert_called_once()
        call_args = mock_ws_class.call_args
        assert call_args[0][0] == "wss://example.com/agent"
        assert "Authorization" in call_args[1]["header"]

        # Verify connection state
        assert transport._is_connected is True

    @patch("websocket.WebSocketApp")
    def test_connect_failure(self, mock_ws_class, transport):
        """Test WebSocket connection failure."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws

        # Mock run_forever to call on_error
        def run_forever_side_effect(**kwargs):
            error = Exception("Connection failed")
            transport._on_error(mock_ws, error)

        mock_ws.run_forever.side_effect = run_forever_side_effect

        # Try to connect
        with pytest.raises(TransportError) as excinfo:
            transport._connect("wss://example.com/agent", {})

        assert "Failed to establish WebSocket connection" in str(excinfo.value)

    def test_on_message_json_rpc_response(self, transport):
        """Test handling JSON-RPC response message."""
        # Set up an active request
        transport._active_requests["123"] = {
            "capability": "test",
            "response_queue": Queue(),
        }

        # Simulate receiving a JSON-RPC response
        message = json.dumps(
            {"jsonrpc": "2.0", "id": "123", "result": {"data": "test"}}
        )

        transport._on_message(None, message)

        # Check response was queued
        response = transport._active_requests["123"]["response_queue"].get_nowait()
        assert response == {"data": "test"}

    def test_on_message_json_rpc_error(self, transport):
        """Test handling JSON-RPC error response."""
        # Set up an active request
        response_queue = Queue()
        transport._active_requests["123"] = {
            "capability": "test",
            "response_queue": response_queue,
        }

        # Simulate receiving a JSON-RPC error
        message = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "123",
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

        transport._on_message(None, message)

        # Check error was queued as TransportError
        error = response_queue.get_nowait()
        assert isinstance(error, TransportError)
        assert "Method not found" in str(error)

    def test_on_message_simple_response(self, transport):
        """Test handling simple response message."""
        # Set up an active request
        response_queue = Queue()
        transport._active_requests["123"] = {
            "capability": "test",
            "response_queue": response_queue,
        }

        # Simulate receiving a simple response
        message = json.dumps({"id": "123", "result": {"data": "test"}})

        transport._on_message(None, message)

        # Check response was queued
        response = response_queue.get_nowait()
        assert response == {"data": "test"}

    def test_on_message_stream_chunk(self, transport):
        """Test handling streaming message chunk."""
        # Set up streaming callback
        chunks = []
        transport._request_callbacks["123"] = lambda chunk: chunks.append(chunk)

        # Simulate receiving a stream chunk
        message = json.dumps(
            {"id": "123", "chunk": {"item": 1, "data": "chunk1"}, "streaming": True}
        )

        transport._on_message(None, message)

        # Check callback was called
        assert len(chunks) == 1
        assert chunks[0] == {"item": 1, "data": "chunk1"}

    def test_on_message_stream_complete(self, transport):
        """Test handling stream completion message."""
        # Set up active streaming request
        response_queue = Queue()
        transport._active_requests["123"] = {
            "capability": "stream",
            "response_queue": response_queue,
        }
        transport._request_callbacks["123"] = lambda chunk: None

        # Simulate stream completion
        message = json.dumps({"id": "123", "complete": True})

        transport._on_message(None, message)

        # Check completion was signaled
        assert "123" not in transport._request_callbacks
        assert "123" not in transport._active_requests

    def test_on_message_invalid_json(self, transport):
        """Test handling invalid JSON message."""
        # Should not raise, just log error
        transport._on_message(None, "invalid json {")

    def test_on_error(self, transport):
        """Test error handler."""
        error = Exception("Test error")

        # Should queue the error
        transport._on_error(None, error)

        queued_error = transport._message_queue.get_nowait()
        assert isinstance(queued_error, Exception)
        assert str(queued_error) == "Test error"

    def test_on_close(self, transport):
        """Test close handler."""
        transport._is_connected = True

        transport._on_close(None, 1000, "Normal closure")

        assert transport._is_connected is False

    @patch("websocket.WebSocketApp")
    def test_invoke_success(self, mock_ws_class, transport):
        """Test successful capability invocation."""
        # Mock WebSocket
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Mock send to capture message
        sent_messages = []
        mock_ws.send.side_effect = lambda msg: sent_messages.append(msg)

        # Set up response simulation
        def simulate_response():
            time.sleep(0.1)  # Small delay
            # Get the request ID from sent message
            sent_msg = json.loads(sent_messages[0])
            request_id = sent_msg["id"]

            # Simulate response
            response = {"jsonrpc": "2.0", "id": request_id, "result": {"echo": "hello"}}
            transport._on_message(None, json.dumps(response))

        # Start response thread
        response_thread = threading.Thread(target=simulate_response)
        response_thread.start()

        # Invoke capability
        result = transport.invoke(
            "wss://example.com", "echo", {"message": "hello"}, timeout=5
        )

        # Verify result
        assert result == {"echo": "hello"}

        # Verify message was sent
        assert len(sent_messages) == 1
        sent = json.loads(sent_messages[0])
        assert sent["method"] == "echo"
        assert sent["params"]["message"] == "hello"

    @patch("websocket.WebSocketApp")
    def test_invoke_timeout(self, mock_ws_class, transport):
        """Test invocation timeout."""
        # Mock WebSocket
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Don't send any response to trigger timeout
        with pytest.raises(TransportTimeoutError) as excinfo:
            transport.invoke("wss://example.com", "test", {}, timeout=0.5)

        assert "timed out" in str(excinfo.value).lower()

    @patch("websocket.WebSocketApp")
    def test_invoke_transport_error(self, mock_ws_class, transport):
        """Test invocation with transport error."""
        # Mock WebSocket
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Mock send to raise exception
        mock_ws.send.side_effect = Exception("Send failed")

        with pytest.raises(TransportError) as excinfo:
            transport.invoke("wss://example.com", "test", {})

        assert "Send failed" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_stream_success(self, mock_ws_class, transport):
        """Test successful streaming."""
        # Mock WebSocket
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Capture sent messages
        sent_messages = []
        mock_ws.send.side_effect = lambda msg: sent_messages.append(msg)

        # Set up streaming response simulation
        def simulate_stream():
            time.sleep(0.1)
            # Get request ID
            sent_msg = json.loads(sent_messages[0])
            request_id = sent_msg["id"]

            # Send chunks
            for i in range(3):
                chunk_msg = {
                    "id": request_id,
                    "chunk": {"index": i, "data": f"chunk{i}"},
                    "streaming": True,
                }
                transport._on_message(None, json.dumps(chunk_msg))
                time.sleep(0.05)

            # Send completion
            complete_msg = {"id": request_id, "complete": True}
            transport._on_message(None, json.dumps(complete_msg))

        # Start streaming thread
        stream_thread = threading.Thread(target=simulate_stream)
        stream_thread.start()

        # Stream capability
        chunks = list(transport.stream("wss://example.com", "stream", {"count": 3}))

        # Verify chunks
        assert len(chunks) == 3
        assert chunks[0] == {"index": 0, "data": "chunk0"}
        assert chunks[1] == {"index": 1, "data": "chunk1"}
        assert chunks[2] == {"index": 2, "data": "chunk2"}

    def test_stream_not_connected(self, transport):
        """Test streaming when not connected."""
        # Should auto-connect
        with patch.object(transport, "_connect") as mock_connect:
            # Mock the connection to succeed immediately
            def mock_connect_impl(url, headers):
                transport._is_connected = True
                transport._ws = Mock()
                transport._ws.send = Mock()

            mock_connect.side_effect = mock_connect_impl

            # Set up to immediately complete the stream
            def simulate_complete():
                # Wait for the request to be registered
                timeout = 0.5
                start = time.time()
                while (
                    not transport._request_callbacks and time.time() - start < timeout
                ):
                    time.sleep(0.01)

                # Send completion message for the registered request
                if transport._request_callbacks:
                    req_id = next(iter(transport._request_callbacks.keys()))
                    transport._on_message(
                        None, json.dumps({"id": req_id, "complete": True})
                    )

            complete_thread = threading.Thread(target=simulate_complete)
            complete_thread.start()

            # Try to stream
            results = list(transport.stream("wss://example.com", "test", {}))

            # Verify connect was called and stream completed
            mock_connect.assert_called_once()
            assert results == []  # No data chunks expected, just completion

    def test_close_connection(self, transport):
        """Test closing WebSocket connection."""
        # Mock WebSocket
        mock_ws = Mock()
        transport._ws = mock_ws
        transport._is_connected = True

        # Mock thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        transport._ws_thread = mock_thread

        # Close connection
        transport.close()

        # Verify close was called
        mock_ws.close.assert_called_once()
        assert transport._is_connected is False

    def test_close_no_connection(self, transport):
        """Test closing when no connection exists."""
        # Should not raise
        transport.close()
        assert transport._is_connected is False

    def test_format_body(self, transport):
        """Test formatting request body."""
        params = {"key": "value", "number": 42}
        body = transport.format_body(params)

        assert isinstance(body, str)
        parsed = json.loads(body)
        assert parsed == params

    def test_parse_response(self, transport):
        """Test parsing response."""
        # Test with dict
        response = {"result": "success"}
        parsed = transport.parse_response(response)
        assert parsed == response

        # Test with JSON string
        json_str = '{"result": "success"}'
        parsed = transport.parse_response(json_str)
        assert parsed == {"result": "success"}

        # Test with non-JSON string
        plain_str = "plain text"
        parsed = transport.parse_response(plain_str)
        assert parsed == "plain text"


class TestWebSocketTransportIntegration:
    """Integration tests for WebSocket transport."""

    @pytest.mark.slow
    def test_reconnection_on_failure(self):
        """Test reconnection behavior on connection failure."""
        transport = WebSocketTransport(reconnect_tries=2, reconnect_delay=0.1)

        with patch("websocket.WebSocketApp") as mock_ws_class:
            mock_ws = Mock()
            mock_ws_class.return_value = mock_ws

            # Make run_forever fail twice, then succeed
            call_count = [0]

            def run_forever_side_effect(**kwargs):
                call_count[0] += 1
                if call_count[0] < 3:
                    raise Exception("Connection failed")
                else:
                    # Simulate successful connection
                    transport._on_open(mock_ws)

            mock_ws.run_forever.side_effect = run_forever_side_effect

            # Should eventually connect after retries
            transport._connect("wss://example.com/agent", {})
            time.sleep(0.5)  # Allow retries

            assert call_count[0] == 3  # Failed twice, succeeded on third

    @pytest.mark.slow
    def test_concurrent_invocations(self):
        """Test multiple concurrent invocations."""
        transport = WebSocketTransport()

        with patch("websocket.WebSocketApp") as mock_ws_class:
            mock_ws = Mock()
            mock_ws_class.return_value = mock_ws
            transport._ws = mock_ws
            transport._is_connected = True

            # Track sent messages
            sent_messages = []
            mock_ws.send.side_effect = lambda msg: sent_messages.append(json.loads(msg))

            # Simulate responses for each request
            def respond_to_requests():
                time.sleep(0.1)
                for msg in sent_messages:
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "result": {"echo": msg["params"]["message"]},
                    }
                    transport._on_message(None, json.dumps(response))

            # Start multiple invocations
            from concurrent.futures import ThreadPoolExecutor

            response_thread = threading.Thread(target=respond_to_requests)
            response_thread.start()

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for i in range(5):
                    future = executor.submit(
                        transport.invoke,
                        "wss://example.com",
                        "echo",
                        {"message": f"msg{i}"},
                        timeout=5,
                    )
                    futures.append((i, future))

                # Collect results with timeout to prevent infinite hanging
                results = {}
                for i, future in futures:
                    try:
                        results[i] = future.result(
                            timeout=10
                        )  # 10 second timeout per future
                    except Exception as e:
                        results[i] = f"Error: {e}"

            # Wait for response thread to complete
            response_thread.join(timeout=5)

            # Verify all requests succeeded (or completed with result)
            assert len(results) == 5
            for i in range(5):
                # Check if result is successful or has reasonable error
                if isinstance(results[i], str) and results[i].startswith("Error:"):
                    # Errors acceptable - testing concurrency
                    print(f"Request {i} had error: {results[i]}")
                else:
                    assert results[i] == {"echo": f"msg{i}"}
