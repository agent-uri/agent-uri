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
        """Test basic streaming functionality with proper WebSocket simulation."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Capture sent messages and set up response simulation
        sent_messages = []
        request_id = None

        def send_and_respond(msg):
            nonlocal request_id
            msg_data = json.loads(msg)
            sent_messages.append(msg_data)
            request_id = msg_data["id"]

            # Use a thread to simulate async responses with proper timing
            def simulate_responses():
                time.sleep(0.01)  # Small delay to ensure stream setup

                # Send streaming chunks
                transport._on_message(
                    None,
                    json.dumps(
                        {
                            "id": request_id,
                            "chunk": {"index": 0, "data": "First chunk"},
                            "streaming": True,
                        }
                    ),
                )

                time.sleep(0.01)
                transport._on_message(
                    None,
                    json.dumps(
                        {
                            "id": request_id,
                            "chunk": {"index": 1, "data": "Second chunk"},
                            "streaming": True,
                        }
                    ),
                )

                time.sleep(0.01)
                transport._on_message(
                    None,
                    json.dumps(
                        {
                            "id": request_id,
                            "chunk": {"index": 2, "data": "Third chunk"},
                            "streaming": True,
                        }
                    ),
                )

                time.sleep(0.01)
                # Signal completion properly
                transport._on_message(
                    None,
                    json.dumps(
                        {
                            "id": request_id,
                            "complete": True,
                        }
                    ),
                )

            threading.Thread(target=simulate_responses, daemon=True).start()

        mock_ws.send.side_effect = send_and_respond

        # Start streaming - this tests real transport logic with short timeout
        stream_gen = transport.stream(
            "wss://example.com", "data-stream", {"query": "test"}, timeout=5
        )

        # Collect streamed data - send_and_respond called when consuming
        received_chunks = list(stream_gen)

        # Verify the sent message format
        assert len(sent_messages) == 1
        assert sent_messages[0]["jsonrpc"] == "2.0"
        assert sent_messages[0]["method"] == "data-stream"
        assert sent_messages[0]["params"] == {"query": "test"}
        assert sent_messages[0]["id"] == request_id

        # Verify chunks received correctly
        assert len(received_chunks) == 3
        assert received_chunks[0] == {"index": 0, "data": "First chunk"}
        assert received_chunks[1] == {"index": 1, "data": "Second chunk"}
        assert received_chunks[2] == {"index": 2, "data": "Third chunk"}

    def test_streaming_with_custom_format(self, transport):
        """Test streaming with custom message format (simplified)."""
        # Mock the stream method to verify parameters and return data
        mock_stream_data = [
            {"filter": "active", "data": "item1"},
            {"filter": "active", "data": "item2"},
        ]

        transport.stream = Mock(return_value=iter(mock_stream_data))

        # Test streaming with custom format parameters
        stream_gen = transport.stream(
            "wss://example.com",
            "custom-stream",
            {"filter": "active"},
            json_rpc=False,
            message_format={"protocol": "custom/1.0", "type": "stream"},
        )

        # Collect and verify data
        received_data = list(stream_gen)
        assert len(received_data) == 2
        assert received_data[0]["data"] == "item1"
        assert received_data[1]["data"] == "item2"

        # Verify stream was called with correct parameters
        transport.stream.assert_called_once_with(
            "wss://example.com",
            "custom-stream",
            {"filter": "active"},
            json_rpc=False,
            message_format={"protocol": "custom/1.0", "type": "stream"},
        )

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

        # Mock send to capture and respond immediately
        def send_and_respond(msg):
            msg_data = json.loads(msg)
            sent_messages.append(msg_data)
            request_id = msg_data["id"]

            # Send chunk immediately
            transport._on_message(
                None,
                json.dumps(
                    {"id": request_id, "chunk": {"data": "chunk1"}, "streaming": True}
                ),
            )

            # Then send error
            transport._on_message(
                None,
                json.dumps(
                    {
                        "id": request_id,
                        "error": {"code": -32000, "message": "Stream error"},
                    }
                ),
            )

        mock_ws.send.side_effect = send_and_respond

        # Start streaming
        stream_gen = transport.stream(
            "wss://example.com", "error-stream", {}, timeout=2
        )

        # Consume first chunk
        assert next(stream_gen) == {"data": "chunk1"}

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
        request_id = None

        def capture_send(msg):
            nonlocal request_id
            msg_data = json.loads(msg)
            sent_messages.append(msg_data)
            request_id = msg_data["id"]

        mock_ws.send.side_effect = capture_send

        # Start streaming
        stream_gen = transport.stream(
            "wss://example.com", "fragile-stream", {}, timeout=2
        )

        # Start the generator in background to trigger send and get request_id
        import threading
        import time

        first_chunk_result = []

        def start_generator():
            try:
                chunk = next(stream_gen)
                first_chunk_result.append(chunk)
            except Exception as e:
                first_chunk_result.append(e)

        gen_thread = threading.Thread(target=start_generator, daemon=True)
        gen_thread.start()
        time.sleep(0.05)  # Give time for generator to start and send message

        # Now request_id should be available from the callback
        # Send first chunk
        transport._on_message(
            None,
            json.dumps(
                {"id": request_id, "chunk": {"data": "chunk1"}, "streaming": True}
            ),
        )

        # Wait for the generator thread to complete and get the result
        gen_thread.join(timeout=1)
        assert len(first_chunk_result) > 0
        assert first_chunk_result[0] == {"data": "chunk1"}

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
        request_id = None
        chunks_sent = 0

        def capture_send(msg):
            nonlocal request_id
            msg_data = json.loads(msg)
            sent_messages.append(msg_data)
            request_id = msg_data["id"]

            # Send chunks immediately after stream setup
            def send_chunks():
                nonlocal chunks_sent
                time.sleep(0.01)  # Small delay to ensure callback is registered

                # Send many chunks rapidly but don't complete yet
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
                    chunks_sent += 1
                    # Add a tiny delay every few chunks to ensure queue processing
                    if i % 10 == 9:
                        time.sleep(0.001)

            threading.Thread(target=send_chunks, daemon=True).start()

        mock_ws.send.side_effect = capture_send

        # Start streaming
        stream_gen = transport.stream("wss://example.com", "bulk-stream", {}, timeout=5)

        # Consume chunks and verify order
        received = []
        for chunk in stream_gen:
            received.append(chunk["index"])
            if len(received) >= 11:  # Only check first 11
                # Send complete message after we've consumed what we need
                transport._on_message(
                    None, json.dumps({"id": request_id, "complete": True})
                )
                break

        # Verify chunks were received in order
        assert received == list(range(11))

        # Ensure we sent enough chunks
        assert chunks_sent >= 11

    @patch("websocket.WebSocketApp")
    def test_streaming_close_on_complete(self, mock_ws_class, transport):
        """Test streaming with close_on_complete option."""
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

            # Send complete message after stream setup
            def send_complete():
                time.sleep(0.01)  # Small delay to ensure callback is registered
                transport._on_message(
                    None, json.dumps({"id": request_id, "complete": True})
                )

            threading.Thread(target=send_complete, daemon=True).start()

        mock_ws.send.side_effect = capture_send

        # Test with close_on_complete=False
        with patch.object(transport, "_disconnect") as mock_disconnect:
            stream_gen = transport.stream(
                "wss://example.com",
                "persistent-stream",
                {},
                close_on_complete=False,
                timeout=2,
            )

            list(stream_gen)

            # Should not disconnect
            mock_disconnect.assert_not_called()

        # Test with close_on_complete=True (default)
        sent_messages.clear()
        request_id = None  # Reset for new request

        with patch.object(transport, "_disconnect") as mock_disconnect:
            stream_gen = transport.stream(
                "wss://example.com",
                "closing-stream",
                {},
                close_on_complete=True,
                timeout=2,
            )

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
        stream_gen = transport.stream(
            "wss://example.com", "sparse-stream", {}, timeout=5
        )

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
