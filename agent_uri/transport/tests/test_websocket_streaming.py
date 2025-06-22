"""
Tests for WebSocket streaming functionality.

This module tests streaming data over WebSocket connections,
including chunk handling, backpressure, and stream lifecycle.
"""

import json
import threading
import time
from unittest.mock import Mock, patch

import pytest

from agent_uri.transport.base import TransportError
from agent_uri.transport.transports.websocket import WebSocketTransport


class TestWebSocketStreaming:
    """Test WebSocket streaming capabilities."""

    @pytest.fixture
    def transport(self):
        """Create a WebSocketTransport instance."""
        return WebSocketTransport()

    @patch("websocket.WebSocketApp")
    def test_basic_streaming(self, mock_ws_class, transport):
        """Test basic streaming functionality."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Capture sent message and request ID
        sent_messages = []
        request_id = None

        def capture_send(msg):
            nonlocal request_id
            msg_data = json.loads(msg)
            sent_messages.append(msg_data)
            request_id = msg_data["id"]

        mock_ws.send.side_effect = capture_send

        # Start streaming
        stream_gen = transport.stream(
            "wss://example.com", "data-stream", {"query": "test"}
        )

        # Send chunks in a thread to simulate async streaming
        def send_chunks():
            # Give time for stream_gen to start and register callback
            time.sleep(0.01)

            # Send chunks
            chunks = [
                {
                    "id": request_id,
                    "chunk": {"index": 0, "data": "First chunk"},
                    "streaming": True,
                },
                {
                    "id": request_id,
                    "chunk": {"index": 1, "data": "Second chunk"},
                    "streaming": True,
                },
                {
                    "id": request_id,
                    "chunk": {"index": 2, "data": "Third chunk"},
                    "streaming": True,
                },
                {"id": request_id, "complete": True},
            ]

            for chunk in chunks:
                time.sleep(0.01)  # Small delay between chunks
                transport._on_message(None, json.dumps(chunk))

        chunk_thread = threading.Thread(target=send_chunks)
        chunk_thread.start()

        # Collect streamed data
        received_chunks = []
        for chunk in stream_gen:
            received_chunks.append(chunk)

        chunk_thread.join()

        # Verify chunks received correctly
        assert len(received_chunks) == 3
        assert received_chunks[0] == {"index": 0, "data": "First chunk"}
        assert received_chunks[1] == {"index": 1, "data": "Second chunk"}
        assert received_chunks[2] == {"index": 2, "data": "Third chunk"}

    @patch("websocket.WebSocketApp")
    def test_streaming_with_custom_format(self, mock_ws_class, transport):
        """Test streaming with non-JSON-RPC message format."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        sent_messages = []
        mock_ws.send.side_effect = lambda msg: sent_messages.append(json.loads(msg))

        # Start streaming with custom format
        stream_gen = transport.stream(
            "wss://example.com",
            "custom-stream",
            {"filter": "active"},
            json_rpc=False,
            message_format={"protocol": "custom/1.0", "type": "stream"},
        )

        # Verify custom format in sent message
        assert len(sent_messages) == 1
        msg = sent_messages[0]
        assert "jsonrpc" not in msg
        assert msg["capability"] == "custom-stream"
        assert msg["protocol"] == "custom/1.0"
        assert msg["type"] == "stream"
        assert msg["stream"] is True
        assert msg["params"] == {"filter": "active"}

        # Complete the stream
        request_id = msg["id"]
        transport._request_callbacks[request_id]({"type": "complete"})
        list(stream_gen)  # Consume to completion

    @patch("websocket.WebSocketApp")
    def test_streaming_timeout(self, mock_ws_class, transport):
        """Test streaming timeout when no data is received."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        mock_ws.send = Mock()

        # Start streaming with short timeout
        stream_gen = transport.stream(
            "wss://example.com", "slow-stream", {}, timeout=0.1
        )

        # Simulate connection loss to trigger timeout
        def disconnect_after_delay():
            time.sleep(0.2)  # Wait longer than timeout
            transport._is_connected = False
            transport._ws = None

        disconnect_thread = threading.Thread(target=disconnect_after_delay)
        disconnect_thread.start()

        # Should timeout/disconnect and raise error
        with pytest.raises(TransportError) as excinfo:
            list(stream_gen)

        disconnect_thread.join()
        # Should timeout with either timeout or connection closed error
        assert "timed out" in str(
            excinfo.value
        ) or "WebSocket connection closed" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_streaming_error_handling(self, mock_ws_class, transport):
        """Test streaming handles errors gracefully."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        sent_messages = []
        mock_ws.send.side_effect = lambda msg: sent_messages.append(json.loads(msg))

        # Start streaming
        stream_gen = transport.stream("wss://example.com", "error-stream", {})
        request_id = sent_messages[0]["id"]

        # Send some successful chunks first
        transport._on_message(
            None,
            json.dumps(
                {"id": request_id, "chunk": {"data": "chunk1"}, "streaming": True}
            ),
        )

        # Consume first chunk
        assert next(stream_gen) == {"data": "chunk1"}

        # Now send an error
        transport._request_callbacks[request_id](TransportError("Stream error"))

        # Next iteration should raise the error
        with pytest.raises(TransportError) as excinfo:
            next(stream_gen)
        assert "Stream error" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_streaming_connection_lost(self, mock_ws_class, transport):
        """Test streaming when connection is lost mid-stream."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        sent_messages = []
        mock_ws.send.side_effect = lambda msg: sent_messages.append(json.loads(msg))

        # Start streaming
        stream_gen = transport.stream("wss://example.com", "fragile-stream", {})
        request_id = sent_messages[0]["id"]

        # Send first chunk
        transport._on_message(
            None,
            json.dumps(
                {"id": request_id, "chunk": {"data": "chunk1"}, "streaming": True}
            ),
        )

        # Consume first chunk
        assert next(stream_gen) == {"data": "chunk1"}

        # Simulate connection loss
        transport._is_connected = False
        transport._ws = None

        # Should raise error on next iteration
        with pytest.raises(TransportError) as excinfo:
            next(stream_gen)
        assert "WebSocket connection closed" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_streaming_backpressure(self, mock_ws_class, transport):
        """Test streaming handles backpressure with many chunks."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        sent_messages = []
        mock_ws.send.side_effect = lambda msg: sent_messages.append(json.loads(msg))

        # Start streaming
        stream_gen = transport.stream("wss://example.com", "bulk-stream", {})
        request_id = sent_messages[0]["id"]

        # Send many chunks rapidly
        num_chunks = 50
        for i in range(num_chunks):
            transport._on_message(
                None,
                json.dumps(
                    {
                        "id": request_id,
                        "chunk": {"index": i, "data": f"chunk_{i}"},
                        "streaming": True,
                    }
                ),
            )

        # Consume slowly and verify order
        received = []
        for i, chunk in enumerate(stream_gen):
            received.append(chunk["index"])
            if i >= 10:  # Only consume first 10
                break

        # Complete the stream
        transport._on_message(None, json.dumps({"id": request_id, "complete": True}))

        # Verify chunks were received in order
        assert received == list(range(11))

    @patch("websocket.WebSocketApp")
    def test_streaming_close_on_complete(self, mock_ws_class, transport):
        """Test streaming with close_on_complete option."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        sent_messages = []
        mock_ws.send.side_effect = lambda msg: sent_messages.append(json.loads(msg))

        # Test with close_on_complete=False
        with patch.object(transport, "_disconnect") as mock_disconnect:
            stream_gen = transport.stream(
                "wss://example.com", "persistent-stream", {}, close_on_complete=False
            )

            request_id = sent_messages[0]["id"]

            # Complete the stream
            transport._request_callbacks[request_id]({"type": "complete"})
            list(stream_gen)

            # Should not disconnect
            mock_disconnect.assert_not_called()

        # Test with close_on_complete=True (default)
        sent_messages.clear()
        with patch.object(transport, "_disconnect") as mock_disconnect:
            stream_gen = transport.stream(
                "wss://example.com", "closing-stream", {}, close_on_complete=True
            )

            request_id = sent_messages[1]["id"]

            # Complete the stream
            transport._request_callbacks[request_id]({"type": "complete"})
            list(stream_gen)

            # Should disconnect
            mock_disconnect.assert_called_once()

    @patch("websocket.WebSocketApp")
    def test_streaming_empty_chunks(self, mock_ws_class, transport):
        """Test streaming handles empty chunks correctly."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        sent_messages = []
        request_id = None

        def capture_send(msg):
            nonlocal request_id
            msg_data = json.loads(msg)
            sent_messages.append(msg_data)
            request_id = msg_data["id"]

        mock_ws.send.side_effect = capture_send

        # Start streaming
        stream_gen = transport.stream("wss://example.com", "sparse-stream", {})

        # Send mix of empty and non-empty chunks in thread
        def send_chunks():
            time.sleep(0.01)  # Let stream_gen initialize
            chunks = [
                {"id": request_id, "chunk": {"data": "chunk1"}, "streaming": True},
                {"id": request_id, "chunk": {}, "streaming": True},  # Empty chunk
                {
                    "id": request_id,
                    "chunk": {"data": ""},
                    "streaming": True,
                },  # Empty data
                {"id": request_id, "chunk": {"data": "chunk4"}, "streaming": True},
                {"id": request_id, "complete": True},
            ]

            for chunk in chunks:
                time.sleep(0.01)
                transport._on_message(None, json.dumps(chunk))

        chunk_thread = threading.Thread(target=send_chunks)
        chunk_thread.start()

        # Collect all chunks
        received = list(stream_gen)
        chunk_thread.join()

        # Should receive all chunks including empty ones
        assert len(received) == 4
        assert received[0] == {"data": "chunk1"}
        assert received[1] == {}
        assert received[2] == {"data": ""}
        assert received[3] == {"data": "chunk4"}
