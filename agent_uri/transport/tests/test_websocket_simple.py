"""
Simplified tests for WebSocket transport implementation.

This module contains basic tests for the WebSocketTransport class
focusing on testable methods.
"""

import json
from unittest.mock import Mock, patch

import pytest

from ..base import TransportError
from ..transports.websocket import WebSocketTransport


class TestWebSocketTransportBasic:
    """Basic tests for WebSocketTransport."""

    @pytest.fixture
    def transport(self):
        """Create a WebSocketTransport instance."""
        return WebSocketTransport()

    def test_protocol_property(self, transport):
        """Test protocol property returns correct value."""
        assert transport.protocol == "wss"

    def test_initialization_defaults(self, transport):
        """Test default initialization values."""
        assert transport._user_agent == "AgentURI-Transport/1.0"
        assert transport._verify_ssl is True
        assert transport._ping_interval == 30
        assert transport._ping_timeout == 10
        assert transport._reconnect_tries == 3
        assert transport._reconnect_delay == 2
        assert transport._is_connected is False
        assert transport._request_id == 0

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        transport = WebSocketTransport(
            user_agent="TestAgent/2.0",
            verify_ssl=False,
            ping_interval=60,
            ping_timeout=15,
            reconnect_tries=5,
            reconnect_delay=3,
        )

        assert transport._user_agent == "TestAgent/2.0"
        assert transport._verify_ssl is False
        assert transport._ping_interval == 60
        assert transport._ping_timeout == 15
        assert transport._reconnect_tries == 5
        assert transport._reconnect_delay == 3

    def test_build_url_https_conversion(self, transport):
        """Test building WebSocket URL from HTTPS."""
        url = transport._build_url("https://example.com", "test-capability")
        assert url == "wss://example.com/test-capability"

    def test_build_url_http_conversion(self, transport):
        """Test building WebSocket URL from HTTP."""
        url = transport._build_url("http://example.com", "test-capability")
        assert url == "ws://example.com/test-capability"

    def test_build_url_websocket_passthrough(self, transport):
        """Test WebSocket URLs pass through unchanged."""
        wss_url = transport._build_url("wss://example.com", "test")
        assert wss_url == "wss://example.com/test"

        ws_url = transport._build_url("ws://example.com", "test")
        assert ws_url == "ws://example.com/test"

    def test_build_url_no_protocol(self, transport):
        """Test URL building with no protocol defaults to wss."""
        url = transport._build_url("example.com", "test")
        assert url == "wss://example.com/test"

    def test_build_url_slash_handling(self, transport):
        """Test proper slash handling in URL building."""
        # Trailing slash in endpoint
        url1 = transport._build_url("https://example.com/", "test")
        assert url1 == "wss://example.com/test"

        # Leading slash in capability
        url2 = transport._build_url("https://example.com", "/test")
        assert url2 == "wss://example.com/test"

        # Both
        url3 = transport._build_url("https://example.com/", "/test")
        assert url3 == "wss://example.com/test"

    def test_get_next_request_id(self, transport):
        """Test request ID generation."""
        assert transport._request_id == 0

        id1 = transport._get_next_request_id()
        assert id1 == "req-1"
        assert transport._request_id == 1

        id2 = transport._get_next_request_id()
        assert id2 == "req-2"
        assert transport._request_id == 2

        id3 = transport._get_next_request_id()
        assert id3 == "req-3"
        assert transport._request_id == 3

    def test_on_close_handler(self, transport):
        """Test WebSocket close handler."""
        transport._is_connected = True

        # Call the close handler
        transport._on_close(None, 1000, "Normal closure")

        assert transport._is_connected is False

    def test_on_error_handler(self, transport):
        """Test WebSocket error handler."""
        # Error should be queued in message queue
        error = Exception("Test error")
        transport._on_error(None, error)

        # Check error was queued
        queued_error = transport._message_queue.get_nowait()
        assert isinstance(queued_error, Exception)
        assert str(queued_error) == "Test error"

    def test_clear_queue(self, transport):
        """Test queue clearing utility."""
        from queue import Queue

        test_queue = Queue()
        test_queue.put("item1")
        test_queue.put("item2")
        test_queue.put("item3")

        assert test_queue.qsize() == 3

        transport._clear_queue(test_queue)

        assert test_queue.qsize() == 0

    def test_format_body(self, transport):
        """Test body formatting from base class."""
        params = {"key": "value", "number": 42}
        body = transport.format_body(params)

        assert isinstance(body, str)
        parsed = json.loads(body)
        assert parsed == params

    def test_parse_response(self, transport):
        """Test response parsing from base class."""
        # Test dict passthrough
        dict_response = {"result": "success"}
        assert transport.parse_response(dict_response) == dict_response

        # Test JSON string parsing
        json_str = '{"result": "success"}'
        parsed = transport.parse_response(json_str)
        assert parsed == {"result": "success"}

        # Test non-JSON string passthrough
        plain_str = "plain text"
        assert transport.parse_response(plain_str) == "plain text"

    def test_invoke_not_connected_raises_error(self, transport):
        """Test that invoke raises error when WebSocket fails to connect."""
        with patch.object(transport, "_connect") as mock_connect:
            # Make connect fail
            mock_connect.side_effect = TransportError("Connection failed")

            with pytest.raises(TransportError) as excinfo:
                transport.invoke("wss://example.com", "test", {})

            assert "Connection failed" in str(excinfo.value)

    def test_stream_not_connected_attempts_connect(self, transport):
        """Test that stream attempts to connect when not connected."""
        with patch.object(transport, "_connect") as mock_connect:
            # Make connect set connected state
            def fake_connect(url, headers):
                transport._is_connected = True
                transport._ws = Mock()

                # Mock the send method to register the callback
                def fake_send(msg):
                    msg_data = json.loads(msg)
                    request_id = msg_data.get("id")
                    # Simulate immediate completion
                    if request_id in transport._request_callbacks:
                        transport._request_callbacks[request_id]({"type": "complete"})

                transport._ws.send = Mock(side_effect=fake_send)

            mock_connect.side_effect = fake_connect

            # Start streaming and consume
            list(transport.stream("wss://example.com", "test", {}))

            mock_connect.assert_called_once()

    def test_disconnect_when_connected(self, transport):
        """Test disconnect when connected."""
        # Set up connected state
        mock_ws = Mock()
        transport._ws = mock_ws
        transport._is_connected = True

        # Call disconnect
        transport._disconnect()

        # Verify WebSocket was closed
        mock_ws.close.assert_called_once()
        assert transport._is_connected is False

    def test_disconnect_when_not_connected(self, transport):
        """Test disconnect when not connected."""
        # Should not raise error
        transport._disconnect()
        assert transport._is_connected is False


class TestWebSocketMessageHandling:
    """Test WebSocket message handling."""

    @pytest.fixture
    def transport(self):
        """Create a WebSocketTransport instance."""
        return WebSocketTransport()

    def test_on_message_json_rpc_response(self, transport):
        """Test handling JSON-RPC response."""
        # Set up a callback for request ID
        response_received = []
        transport._request_callbacks["123"] = lambda resp: response_received.append(
            resp
        )

        # Simulate JSON-RPC response
        message = json.dumps(
            {"jsonrpc": "2.0", "id": "123", "result": {"data": "test"}}
        )

        transport._on_message(None, message)

        # Check callback was called with result
        assert len(response_received) == 1
        assert response_received[0] == {"data": "test"}

        # Callback should be removed
        assert "123" not in transport._request_callbacks

    def test_on_message_json_rpc_error(self, transport):
        """Test handling JSON-RPC error response."""
        error_received = []
        transport._request_callbacks["123"] = lambda resp: error_received.append(resp)

        # Simulate JSON-RPC error
        message = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "123",
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

        transport._on_message(None, message)

        # Check error was received
        assert len(error_received) == 1
        assert isinstance(error_received[0], TransportError)
        assert "Method not found" in str(error_received[0])

    def test_on_message_simple_response(self, transport):
        """Test handling simple response format."""
        response_received = []
        transport._request_callbacks["456"] = lambda resp: response_received.append(
            resp
        )

        # Simulate simple response
        message = json.dumps({"id": "456", "result": {"echo": "hello"}})

        transport._on_message(None, message)

        # Check response was received
        assert len(response_received) == 1
        assert response_received[0] == {"echo": "hello"}

    def test_on_message_streaming_chunk(self, transport):
        """Test handling streaming message chunk."""
        chunks_received = []
        transport._request_callbacks["789"] = lambda chunk: chunks_received.append(
            chunk
        )

        # Simulate streaming chunk
        message = json.dumps(
            {"id": "789", "chunk": {"index": 1, "data": "chunk1"}, "streaming": True}
        )

        transport._on_message(None, message)

        # Check chunk was received (callback should not be removed for streaming)
        assert len(chunks_received) == 1
        assert chunks_received[0] == {"index": 1, "data": "chunk1"}
        assert "789" in transport._request_callbacks

    def test_on_message_streaming_complete(self, transport):
        """Test handling streaming completion."""
        transport._request_callbacks["789"] = lambda chunk: None

        # Simulate completion
        message = json.dumps({"id": "789", "complete": True})

        transport._on_message(None, message)

        # Callback should be removed
        assert "789" not in transport._request_callbacks

    def test_on_message_invalid_json(self, transport):
        """Test handling invalid JSON gracefully."""
        # Should not raise exception
        transport._on_message(None, "invalid json {")

        # Should not crash
        transport._on_message(None, "")
        transport._on_message(None, "not json at all")

    def test_on_message_unknown_request_id(self, transport):
        """Test handling message with unknown request ID."""
        # Should not raise exception
        message = json.dumps({"id": "unknown", "result": {"data": "test"}})

        transport._on_message(None, message)

        # Should handle gracefully


class TestWebSocketTransportExtended:
    """Extended tests for additional coverage."""

    @pytest.fixture
    def transport(self):
        """Create transport instance."""
        return WebSocketTransport()

    def test_invoke_json_rpc_format(self, transport):
        """Test invoke creates correct JSON-RPC message format."""
        with patch.object(transport, "_connect"):
            with patch.object(transport, "_ws") as mock_ws:
                mock_ws.send = Mock()
                transport._is_connected = True

                # Mock the callback mechanism
                sent_messages = []

                def capture_send(msg):
                    sent_messages.append(json.loads(msg))
                    # Simulate immediate response to avoid timeout
                    request_id = json.loads(msg)["id"]
                    if request_id in transport._request_callbacks:
                        transport._request_callbacks[request_id]({"result": "test"})

                mock_ws.send.side_effect = capture_send

                # Test invoke
                result = transport.invoke(
                    "wss://example.com",
                    "test-capability",
                    {"param": "value"},
                    timeout=1,
                )

                # Verify message format
                assert len(sent_messages) == 1
                msg = sent_messages[0]
                assert msg["jsonrpc"] == "2.0"
                assert msg["method"] == "test-capability"
                assert msg["params"] == {"param": "value"}
                assert "id" in msg

                # Verify result
                assert result == {"result": "test"}

    def test_invoke_simple_format(self, transport):
        """Test invoke with simple message format."""
        with patch.object(transport, "_connect"):
            with patch.object(transport, "_ws") as mock_ws:
                transport._is_connected = True

                sent_messages = []

                def capture_send(msg):
                    sent_messages.append(json.loads(msg))
                    request_id = json.loads(msg)["id"]
                    if request_id in transport._request_callbacks:
                        transport._request_callbacks[request_id]({"result": "simple"})

                mock_ws.send.side_effect = capture_send

                # Test invoke with json_rpc=False
                result = transport.invoke(
                    "wss://example.com",
                    "test",
                    {"param": "value"},
                    json_rpc=False,
                    timeout=1,
                )

                # Verify simple message format
                msg = sent_messages[0]
                assert "jsonrpc" not in msg
                assert msg["capability"] == "test"
                assert msg["params"] == {"param": "value"}
                assert result == {"result": "simple"}

    def test_invoke_websocket_not_established_error(self, transport):
        """Test invoke when WebSocket is None."""
        with patch.object(transport, "_connect"):
            transport._is_connected = True
            transport._ws = None  # WebSocket not established

            with pytest.raises(TransportError) as excinfo:
                transport.invoke("wss://example.com", "test", {})

            assert "WebSocket connection not established" in str(excinfo.value)
