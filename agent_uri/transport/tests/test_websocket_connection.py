"""
Tests for WebSocket connection management functionality.

This module tests connection establishment, reconnection, SSL handling,
and connection lifecycle management.
"""

import time
from unittest.mock import Mock, patch

import pytest

from agent_uri.transport.base import TransportError
from agent_uri.transport.transports.websocket import WebSocketTransport


class TestWebSocketConnection:
    """Test WebSocket connection establishment and management."""

    @pytest.fixture
    def transport(self):
        """Create a WebSocketTransport instance."""
        return WebSocketTransport()

    @patch("websocket.WebSocketApp")
    def test_connection_with_custom_headers(self, mock_ws_class, transport):
        """Test that custom headers are properly included in connection."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws

        def run_forever_side_effect(**kwargs):
            transport._is_connected = True

        mock_ws.run_forever.side_effect = run_forever_side_effect

        # Connect with custom headers
        custom_headers = {
            "Authorization": "Bearer token123",
            "X-API-Key": "secret-key",
            "X-Custom-Header": "custom-value",
        }
        transport._connect("wss://api.example.com/v1/agent", custom_headers)

        # Verify headers were passed correctly
        call_args = mock_ws_class.call_args
        headers = call_args[1]["header"]
        assert headers["Authorization"] == "Bearer token123"
        assert headers["X-API-Key"] == "secret-key"
        assert headers["X-Custom-Header"] == "custom-value"
        assert "User-Agent" in headers  # Default header should be included

    @patch("websocket.WebSocketApp")
    def test_connection_url_conversion(self, mock_ws_class, transport):
        """Test URL protocol conversion for WebSocket connections."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws

        def run_forever_side_effect(**kwargs):
            transport._is_connected = True

        mock_ws.run_forever.side_effect = run_forever_side_effect

        test_cases = [
            ("http://example.com/agent", "ws://example.com/agent"),
            ("https://example.com/agent", "wss://example.com/agent"),
            ("example.com/agent", "wss://example.com/agent"),
            ("ws://example.com/agent", "ws://example.com/agent"),
            ("wss://example.com/agent", "wss://example.com/agent"),
        ]

        for input_url, expected_url in test_cases:
            mock_ws_class.reset_mock()
            transport._is_connected = False

            transport._connect(input_url, {})

            call_args = mock_ws_class.call_args
            assert call_args[0][0] == expected_url

    @patch("websocket.WebSocketApp")
    def test_connection_already_connected(self, mock_ws_class, transport):
        """Test that connecting when already connected is a no-op."""
        transport._is_connected = True
        transport._ws = Mock()

        transport._connect("wss://example.com", {})

        # Should not create new WebSocket
        mock_ws_class.assert_not_called()

    @patch("websocket.WebSocketApp")
    def test_connection_timeout(self, mock_ws_class, transport):
        """Test connection timeout when WebSocket fails to connect."""
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws

        # Never set connected flag to simulate timeout
        def run_forever_side_effect(**kwargs):
            time.sleep(0.1)  # Simulate some work

        mock_ws.run_forever.side_effect = run_forever_side_effect

        # Should raise TransportError after timeout
        with pytest.raises(TransportError) as excinfo:
            transport._connect("wss://example.com/agent", {})

        assert "Failed to establish WebSocket connection" in str(excinfo.value)

    @patch("websocket.WebSocketApp")
    def test_ssl_verification_settings(self, mock_ws_class):
        """Test SSL verification configuration without bypassing security."""
        # Test with SSL verification enabled (default and recommended)
        transport = WebSocketTransport(verify_ssl=True)
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws

        thread_kwargs_captured = {}

        # Mock threading.Thread to capture kwargs and simulate connection
        with patch("threading.Thread") as mock_thread_class:

            def thread_init(target=None, kwargs=None, daemon=None):
                # Capture the kwargs passed to Thread
                thread_kwargs_captured.update(kwargs or {})

                # Create a mock thread that sets connection flag when started
                mock_thread = Mock()

                def thread_start():
                    transport._is_connected = True

                mock_thread.start = thread_start
                return mock_thread

            mock_thread_class.side_effect = thread_init

            transport._connect("wss://secure.example.com", {})

            # Verify SSL verification enabled (cert_reqs=2 means CERT_REQUIRED)
            assert thread_kwargs_captured["sslopt"]["cert_reqs"] == 2

        # Test SSL configuration object structure without disabling verification
        transport2 = WebSocketTransport(verify_ssl=True)
        mock_ws_class.reset_mock()
        thread_kwargs_captured.clear()

        with patch("threading.Thread") as mock_thread_class:

            def thread_init(target=None, kwargs=None, daemon=None):
                # Capture the kwargs passed to Thread
                thread_kwargs_captured.update(kwargs or {})

                # Create a mock thread that sets connection flag when started
                mock_thread = Mock()

                def thread_start():
                    transport2._is_connected = True

                mock_thread.start = thread_start
                return mock_thread

            mock_thread_class.side_effect = thread_init

            transport2._connect("wss://another-secure.example.com", {})

            # Verify SSL options structure exists and maintains security
            assert "sslopt" in thread_kwargs_captured
            assert "cert_reqs" in thread_kwargs_captured["sslopt"]
            # Ensure SSL verification remains enabled
            assert thread_kwargs_captured["sslopt"]["cert_reqs"] == 2

    @patch("websocket.WebSocketApp")
    def test_ping_settings(self, mock_ws_class):
        """Test custom ping interval and timeout settings."""
        transport = WebSocketTransport(ping_interval=60, ping_timeout=20)
        mock_ws = Mock()
        mock_ws_class.return_value = mock_ws

        thread_kwargs_captured = {}

        # Mock threading.Thread to capture kwargs and simulate connection
        with patch("threading.Thread") as mock_thread_class:

            def thread_init(target=None, kwargs=None, daemon=None):
                # Capture the kwargs passed to Thread
                thread_kwargs_captured.update(kwargs or {})

                # Create a mock thread that sets connection flag when started
                mock_thread = Mock()

                def thread_start():
                    transport._is_connected = True

                mock_thread.start = thread_start
                return mock_thread

            mock_thread_class.side_effect = thread_init

            transport._connect("wss://example.com", {})

            # Verify ping settings
            assert thread_kwargs_captured["ping_interval"] == 60
            assert thread_kwargs_captured["ping_timeout"] == 20

    def test_disconnect_cleanup(self, transport):
        """Test disconnect properly cleans up resources."""
        # Set up connection state
        mock_ws = Mock()
        transport._ws = mock_ws
        transport._is_connected = True
        transport._message_queue.put("test_message")
        transport._response_queue.put("test_response")

        # Disconnect
        transport._disconnect()

        # Verify cleanup
        mock_ws.close.assert_called_once()
        assert transport._is_connected is False
        assert transport._ws is None
        assert transport._message_queue.empty()
        assert transport._response_queue.empty()

    def test_disconnect_when_not_connected(self, transport):
        """Test disconnect is safe when not connected."""
        transport._is_connected = False
        transport._ws = None

        # Should not raise any errors
        transport._disconnect()

        assert transport._is_connected is False

    def test_disconnect_with_close_error(self, transport):
        """Test disconnect handles errors during close."""
        mock_ws = Mock()
        mock_ws.close.side_effect = Exception("Close failed")
        transport._ws = mock_ws
        transport._is_connected = True

        # Should not raise error
        transport._disconnect()

        # Should still clean up state
        assert transport._is_connected is False
        assert transport._ws is None
