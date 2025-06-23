"""
Tests for WebSocket error handling and edge cases.

This module tests error scenarios, timeout handling, connection failures,
and recovery mechanisms.
"""

import json
import threading
import time
from queue import Queue
from unittest.mock import Mock, patch

import pytest

from agent_uri.transport.base import TransportError, TransportTimeoutError
from agent_uri.transport.transports.websocket import WebSocketTransport


class TestWebSocketErrorHandling:
    """Test WebSocket error handling and edge cases."""

    @pytest.fixture
    def transport(self):
        """Create a WebSocketTransport instance."""
        return WebSocketTransport()

    @patch("websocket.WebSocketApp")
    def test_invoke_websocket_send_error(self, mock_ws_class, transport):
        """Test invoke handles WebSocket send errors."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Simulate send error
        mock_ws.send.side_effect = Exception("Connection lost")

        with pytest.raises(TransportError) as excinfo:
            transport.invoke("wss://example.com", "test", {})

        assert "Error sending WebSocket message" in str(excinfo.value)
        assert "Connection lost" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_invoke_websocket_becomes_none(self, mock_ws_class, transport):
        """Test invoke handles WebSocket becoming None during operation."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Simulate WebSocket becoming None
        def send_side_effect(msg):
            transport._ws = None
            raise Exception("WebSocket closed unexpectedly")

        mock_ws.send.side_effect = send_side_effect

        with pytest.raises(TransportError) as excinfo:
            transport.invoke("wss://example.com", "test", {})

        assert "Error sending WebSocket message" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_invoke_timeout(self, mock_ws_class, transport):
        """Test invoke timeout when no response is received."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Don't simulate any response
        mock_ws.send = Mock()

        with pytest.raises(TransportTimeoutError) as excinfo:
            transport.invoke("wss://example.com", "test", {}, timeout=0.1)

        assert "timed out after 0.1 seconds" in str(excinfo.value)

    def test_on_message_with_invalid_json(self, transport):
        """Test message handler with invalid JSON."""
        invalid_json_cases = [
            '{"incomplete": "json"',  # Missing closing brace
            '{"invalid": json}',  # Invalid syntax
            "not json at all",  # Plain text
            "",  # Empty string
            "}{",  # Malformed brackets
        ]

        for invalid_json in invalid_json_cases:
            # Should not raise exception
            transport._on_message(None, invalid_json)

            # Should queue the message as-is
            queued = transport._message_queue.get_nowait()
            assert queued == invalid_json

    def test_on_message_with_bytes_input(self, transport):
        """Test message handler with bytes input."""
        message = {"id": "123", "result": {"data": "test"}}
        bytes_message = json.dumps(message).encode("utf-8")

        # Set up active request
        transport._active_requests["123"] = {
            "capability": "test",
            "response_queue": Queue(),
        }

        transport._on_message(None, bytes_message)

        # Should handle bytes correctly
        response = transport._active_requests["123"]["response_queue"].get_nowait()
        assert response == {"data": "test"}

    def test_on_message_processing_error(self, transport):
        """Test message handler when processing raises an error."""
        with patch("agent_uri.transport.transports.websocket.logger") as mock_logger:
            # Make logger.error raise an exception
            mock_logger.error.side_effect = Exception("Logger failed")

            # Should still handle the message without raising
            transport._on_message(None, "invalid json {")

            # Message should still be queued
            msg = transport._message_queue.get_nowait()
            assert msg == "invalid json {"

    def test_on_error_with_multiple_callbacks(self, transport):
        """Test error handler propagates to all callbacks."""
        # Set up multiple callbacks
        errors_received = []
        transport._request_callbacks["req1"] = lambda err: errors_received.append(
            ("req1", err)
        )
        transport._request_callbacks["req2"] = lambda err: errors_received.append(
            ("req2", err)
        )
        transport._request_callbacks["req3"] = lambda err: errors_received.append(
            ("req3", err)
        )

        error = Exception("WebSocket error")
        transport._on_error(None, error)

        # All callbacks should receive the error
        assert len(errors_received) == 3
        assert ("req1", error) in errors_received
        assert ("req2", error) in errors_received
        assert ("req3", error) in errors_received

        # Error should also be queued
        queued_error = transport._message_queue.get_nowait()
        assert queued_error == error

    def test_on_close_with_active_requests(self, transport):
        """Test close handler with pending requests."""
        # Set up active state
        transport._is_connected = True
        transport._active_requests = {
            "req1": {"capability": "test1", "response_queue": Queue()},
            "req2": {"capability": "test2", "response_queue": Queue()},
        }
        transport._request_callbacks = {
            "req3": Mock(),
            "req4": Mock(),
        }

        # Add some queued messages
        transport._message_queue.put("msg1")
        transport._message_queue.put("msg2")

        # Trigger close
        transport._on_close(None, 1006, "Abnormal closure")

        # Verify cleanup
        assert transport._is_connected is False
        assert len(transport._active_requests) == 0
        assert len(transport._request_callbacks) == 0
        assert transport._message_queue.empty()

    @patch("websocket.WebSocketApp")
    def test_stream_with_callback_error(self, mock_ws_class, transport):
        """Test streaming handles errors in message callbacks."""
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

            # Trigger callback error after a short delay
            def trigger_error():
                time.sleep(0.01)
                error = TransportError("Callback processing failed")
                if request_id in transport._request_callbacks:
                    transport._request_callbacks[request_id](error)

            threading.Thread(target=trigger_error, daemon=True).start()

        mock_ws.send.side_effect = capture_send

        # Start streaming
        stream_gen = transport.stream("wss://example.com", "error-stream", {})

        # Should raise error when consumed
        with pytest.raises(TransportError) as excinfo:
            next(stream_gen)
        assert "Callback processing failed" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_connection_error_during_establishment(self, mock_ws_class, transport):
        """Test connection errors during establishment."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws

        # Simulate connection error - call the error handler explicitly
        # since that's how the real websocket library would behave
        def run_forever_side_effect(**kwargs):
            error = Exception("Network unreachable")
            # Simulate the library calling the error handler
            transport._on_error(mock_ws, error)
            raise error

        mock_ws.run_forever.side_effect = run_forever_side_effect

        with pytest.raises(TransportError) as excinfo:
            transport._connect("wss://unreachable.example.com", {})

        # With retry logic, the error message includes retry information
        assert "Failed to establish WebSocket connection" in str(excinfo.value)
        assert "Network unreachable" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_concurrent_request_cleanup_on_error(self, mock_ws_class, transport):
        """Test that errors properly clean up concurrent requests."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        # Set up multiple pending requests
        transport._active_requests = {
            "req1": {"capability": "test1", "response_queue": Queue()},
            "req2": {"capability": "test2", "response_queue": Queue()},
        }
        transport._request_callbacks = {
            "req1": Mock(),
            "req2": Mock(),
        }

        # Simulate WebSocket error
        error = Exception("Connection lost")
        transport._on_error(None, error)

        # Verify callbacks were called
        transport._request_callbacks["req1"].assert_called_once_with(error)
        transport._request_callbacks["req2"].assert_called_once_with(error)

    def test_queue_operations_with_errors(self, transport):
        """Test queue operations handle errors gracefully."""
        # Test clearing queue with items that might cause issues
        transport._message_queue.put(Exception("Test error"))
        transport._message_queue.put({"complex": {"data": "structure"}})
        transport._message_queue.put(None)
        transport._message_queue.put("string message")

        # Clear queue should handle all types
        transport._clear_queue(transport._message_queue)
        assert transport._message_queue.empty()

        # Test with response queue
        transport._response_queue.put({"response": "data"})
        transport._response_queue.put(TransportError("Test error"))

        transport._clear_queue(transport._response_queue)
        assert transport._response_queue.empty()

    @patch("websocket.WebSocketApp")
    def test_invoke_with_response_error(self, mock_ws_class, transport):
        """Test invoke handles error responses correctly."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws
        transport._ws = mock_ws
        transport._is_connected = True

        sent_messages = []
        mock_ws.send.side_effect = lambda msg: sent_messages.append(json.loads(msg))

        # Start invoke in a thread
        result_container = {}
        error_container = {}

        def invoke_in_thread():
            try:
                result = transport.invoke(
                    "wss://example.com", "error-test", {}, timeout=5
                )
                result_container["result"] = result
            except Exception as e:
                error_container["error"] = e

        invoke_thread = threading.Thread(target=invoke_in_thread)
        invoke_thread.start()

        # Wait for message to be sent
        time.sleep(0.1)
        request_id = sent_messages[0]["id"]

        # Send error response
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": "Internal server error"},
        }
        transport._on_message(None, json.dumps(error_response))

        invoke_thread.join(timeout=1)

        # Should have received error
        assert "error" in error_container
        assert isinstance(error_container["error"], TransportError)
        assert "Internal server error" in str(error_container["error"])

    def test_disconnect_error_handling(self, transport):
        """Test disconnect handles various error conditions."""
        # Test disconnect when close raises error
        mock_ws = Mock()
        mock_ws.close.side_effect = Exception("Close failed")
        transport._ws = mock_ws
        transport._is_connected = True

        # Should not raise error
        transport._disconnect()
        assert transport._is_connected is False
        assert transport._ws is None

        # Test disconnect when WebSocket is None
        transport._is_connected = True
        transport._ws = None
        transport._disconnect()  # Should not raise
        assert transport._is_connected is False
