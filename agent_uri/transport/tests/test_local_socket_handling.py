"""
Tests for local transport socket handling and client communication.

This module tests the socket-based communication, streaming, and error
handling that were not covered in the existing test suites.
"""

import json
import socket
import tempfile
import threading
import time
from unittest.mock import Mock, patch

import pytest

from ..base import TransportError
from ..transports.local import LocalAgentRegistry, LocalTransport


class TestLocalTransportSocketHandling:
    """Tests for socket-based communication in local transport."""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Reset registry state before each test."""
        LocalAgentRegistry._instance = None
        yield
        if LocalAgentRegistry._instance:
            registry = LocalAgentRegistry.get_instance()
            registry.stop()
            LocalAgentRegistry._instance = None

    @pytest.fixture
    def registry(self):
        """Get a clean registry instance."""
        return LocalAgentRegistry.get_instance()

    @pytest.fixture
    def transport(self):
        """Get a clean transport instance."""
        return LocalTransport()

    def test_handle_client_basic_request(self, registry):
        """Test _handle_client with a basic request."""
        # Create a mock handler
        mock_handler = Mock(return_value={"result": "success"})
        registry.register_agent("test-agent", mock_handler)

        # Create mock sockets
        client_socket = Mock()
        client_socket.recv.side_effect = [
            json.dumps(
                {
                    "capability": "test-cap",
                    "params": {"param1": "value1"},
                    "id": "test-123",
                    "streaming": False,
                }
            ).encode("utf-8")
            + b"\n",
            b"",  # End of data
        ]

        # Call _handle_client
        registry._handle_client("test-agent", client_socket)

        # Verify handler was called
        mock_handler.assert_called_once_with("test-cap", {"param1": "value1"})

        # Verify response was sent
        client_socket.sendall.assert_called()
        sent_data = client_socket.sendall.call_args[0][0]
        response = json.loads(sent_data.decode("utf-8").strip())
        assert response["result"] == {"result": "success"}
        assert response["id"] == "test-123"

    def test_handle_client_streaming_request(self, registry):
        """Test _handle_client with streaming request."""

        # Create a mock handler that yields data
        def mock_handler(capability, params):
            yield {"chunk": 1}
            yield {"chunk": 2}
            yield {"chunk": 3}

        registry.register_agent("stream-agent", mock_handler)

        # Create mock sockets
        client_socket = Mock()
        client_socket.recv.side_effect = [
            json.dumps(
                {
                    "capability": "stream-cap",
                    "params": {},
                    "id": "stream-123",
                    "streaming": True,
                }
            ).encode("utf-8")
            + b"\n",
            b"",
        ]

        # Call _handle_client
        registry._handle_client("stream-agent", client_socket)

        # Verify streaming responses
        calls = client_socket.sendall.call_args_list
        assert len(calls) >= 4  # Initial ack + 3 chunks + complete

        # Check initial ack
        ack_data = json.loads(calls[0][0][0].decode("utf-8").strip())
        assert ack_data["status"] == "streaming"
        assert ack_data["id"] == "stream-123"

        # Check chunks
        for i in range(1, 4):
            chunk_data = json.loads(calls[i][0][0].decode("utf-8").strip())
            assert chunk_data["chunk"] == {"chunk": i}
            assert chunk_data["id"] == "stream-123"

        # Check completion
        complete_data = json.loads(calls[4][0][0].decode("utf-8").strip())
        assert complete_data["complete"] is True
        assert complete_data["id"] == "stream-123"

    def test_handle_client_code_paths(self, registry):
        """Test various code paths in _handle_client method."""
        # Test 1: Agent not found case
        client_socket1 = Mock()
        client_socket1.recv.side_effect = [
            json.dumps({"capability": "test", "params": {}, "id": "404"}).encode(
                "utf-8"
            )
            + b"\n",
            b"",
        ]

        # Call with non-existent agent - covers line 298-300
        registry._handle_client("non-existent", client_socket1)
        client_socket1.close.assert_called()

        # Test 2: Socket timeout case
        client_socket2 = Mock()
        client_socket2.settimeout.return_value = None
        client_socket2.recv.side_effect = socket.timeout("timeout")

        # Should handle timeout gracefully
        registry._handle_client("any-agent", client_socket2)
        client_socket2.close.assert_called()

    def test_handle_client_handler_exception(self, registry):
        """Test _handle_client when handler raises exception."""

        # Create a handler that raises exception
        def failing_handler(capability, params):
            raise ValueError("Handler error")

        registry.register_agent("failing-agent", failing_handler)

        client_socket = Mock()
        client_socket.recv.side_effect = [
            json.dumps({"capability": "fail", "params": {}, "id": "error-test"}).encode(
                "utf-8"
            )
            + b"\n",
            b"",
        ]

        # Call _handle_client
        registry._handle_client("failing-agent", client_socket)

        # Verify error response
        sent_data = client_socket.sendall.call_args[0][0]
        response = json.loads(sent_data.decode("utf-8").strip())
        assert "error" in response
        assert "Handler error" in response["error"]
        assert response["code"] == 500
        assert response["id"] == "error-test"

    def test_handle_client_generator_conversion(self, registry):
        """Test _handle_client converts generator to list for non-streaming."""

        # Create a handler that returns a generator
        def gen_handler(capability, params):
            yield 1
            yield 2
            yield 3

        registry.register_agent("gen-agent", gen_handler)

        client_socket = Mock()
        client_socket.recv.side_effect = [
            json.dumps(
                {
                    "capability": "gen",
                    "params": {},
                    "id": "gen-test",
                    "streaming": False,
                }
            ).encode("utf-8")
            + b"\n",
            b"",
        ]

        # Call _handle_client
        registry._handle_client("gen-agent", client_socket)

        # Verify response contains list
        sent_data = client_socket.sendall.call_args[0][0]
        response = json.loads(sent_data.decode("utf-8").strip())
        assert response["result"] == [1, 2, 3]
        assert response["id"] == "gen-test"

    def test_handle_client_empty_request(self, registry):
        """Test _handle_client with empty request data."""
        client_socket = Mock()
        client_socket.recv.return_value = b""  # Empty data

        # Call _handle_client - should return early
        registry._handle_client("test-agent", client_socket)

        # Verify no response was sent
        client_socket.sendall.assert_not_called()

    def test_handle_client_invalid_json(self, registry):
        """Test _handle_client with invalid JSON request."""
        client_socket = Mock()
        client_socket.recv.side_effect = [b"invalid json data\n", b""]

        # Call _handle_client - should handle exception
        registry._handle_client("test-agent", client_socket)

        # Socket should be closed
        client_socket.close.assert_called()

    def test_handle_client_socket_timeout(self, registry):
        """Test _handle_client with socket timeout."""
        mock_handler = Mock(return_value={"result": "ok"})
        registry.register_agent("timeout-agent", mock_handler)

        client_socket = Mock()
        # Simulate timeout on recv
        client_socket.recv.side_effect = socket.timeout("timed out")

        # Call _handle_client
        registry._handle_client("timeout-agent", client_socket)

        # Socket should be closed
        client_socket.close.assert_called()

    def test_agent_server_loop_timeout_handling(self, registry):
        """Test _agent_server_loop handles socket timeout correctly."""
        server_socket = Mock()
        server_socket.accept.side_effect = socket.timeout("accept timeout")

        # Register an agent
        registry.register_agent("test", lambda c, p: {})
        registry._running = True

        # Run server loop in thread briefly
        thread = threading.Thread(
            target=registry._agent_server_loop, args=("test", server_socket)
        )
        thread.start()

        # Let it run briefly
        time.sleep(0.1)
        registry._running = False
        thread.join(timeout=1)

        # Should have called settimeout
        server_socket.settimeout.assert_called_with(1.0)

    def test_agent_server_loop_error_handling(self, registry):
        """Test _agent_server_loop handles errors gracefully."""
        server_socket = Mock()
        # First accept succeeds, then error
        server_socket.accept.side_effect = [(Mock(), None), Exception("Server error")]

        registry.register_agent("error-test", lambda c, p: {})
        registry._running = True

        # Run server loop
        with patch("agent_uri.transport.transports.local.logger") as mock_logger:
            thread = threading.Thread(
                target=registry._agent_server_loop, args=("error-test", server_socket)
            )
            thread.start()

            time.sleep(0.2)
            registry._running = False
            thread.join(timeout=1)

            # Should have logged error
            mock_logger.error.assert_called()

    def test_stream_request_basic(self, transport):
        """Test _stream_request method basic functionality."""
        # Mock socket
        mock_socket = Mock()

        # Simulate streaming responses
        responses = [
            json.dumps({"chunk": "data1", "id": "test-123"}).encode("utf-8") + b"\n",
            json.dumps({"chunk": "data2", "id": "test-123"}).encode("utf-8") + b"\n",
            json.dumps({"complete": True, "id": "test-123"}).encode("utf-8") + b"\n",
        ]

        # recv returns data in chunks
        mock_socket.recv.side_effect = [
            responses[0],
            responses[1],
            responses[2],
            b"",  # End
        ]

        with patch("socket.socket", return_value=mock_socket):
            # Call _stream_request
            chunks = list(
                transport._stream_request(
                    "test.sock",
                    "stream-cap",
                    {"param": "value"},
                    timeout=30,
                    request_id="test-123",
                )
            )

            # Verify chunks
            assert chunks == ["data1", "data2"]

            # Verify request was sent
            mock_socket.sendall.assert_called_once()
            sent_data = json.loads(
                mock_socket.sendall.call_args[0][0].decode("utf-8").strip()
            )
            assert sent_data["capability"] == "stream-cap"
            assert sent_data["params"] == {"param": "value"}
            assert sent_data["streaming"] is True

    def test_stream_request_tcp_socket(self, transport):
        """Test _stream_request with TCP socket."""
        mock_socket = Mock()
        mock_socket.recv.side_effect = [
            json.dumps({"complete": True, "id": "tcp-123"}).encode("utf-8") + b"\n",
            b"",
        ]

        with patch("socket.socket", return_value=mock_socket) as mock_socket_class:
            # Call with TCP address
            list(
                transport._stream_request(
                    "127.0.0.1:8080", "tcp-cap", {}, request_id="tcp-123"
                )
            )

            # Verify TCP socket was created
            mock_socket_class.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)
            mock_socket.connect.assert_called_with(("127.0.0.1", 8080))

    def test_stream_request_unix_socket(self, transport):
        """Test _stream_request with Unix domain socket."""
        mock_socket = Mock()
        mock_socket.recv.side_effect = [
            json.dumps({"complete": True, "id": "unix-123"}).encode("utf-8") + b"\n",
            b"",
        ]

        with patch("socket.socket", return_value=mock_socket) as mock_socket_class:
            # Call with Unix socket path
            list(
                transport._stream_request(
                    "/tmp/test.sock", "unix-cap", {}, request_id="unix-123"
                )
            )

            # Verify Unix socket was created
            mock_socket_class.assert_called_with(socket.AF_UNIX, socket.SOCK_STREAM)
            mock_socket.connect.assert_called_with("/tmp/test.sock")

    def test_stream_request_error_response(self, transport):
        """Test _stream_request handles error responses."""
        mock_socket = Mock()
        mock_socket.recv.side_effect = [
            json.dumps({"error": "Stream error", "id": "error-123"}).encode("utf-8")
            + b"\n",
            b"",
        ]

        with patch("socket.socket", return_value=mock_socket):
            # Should raise TransportError
            with pytest.raises(TransportError) as exc_info:
                list(
                    transport._stream_request(
                        "test.sock", "error-cap", {}, request_id="error-123"
                    )
                )

            assert "Stream error" in str(exc_info.value)

    def test_stream_request_invalid_json(self, transport):
        """Test _stream_request handles invalid JSON gracefully."""
        mock_socket = Mock()
        mock_socket.recv.side_effect = [
            b"invalid json\n",
            json.dumps({"chunk": "valid", "id": "test"}).encode("utf-8") + b"\n",
            json.dumps({"complete": True, "id": "test"}).encode("utf-8") + b"\n",
            b"",
        ]

        with patch("socket.socket", return_value=mock_socket):
            # Should skip invalid JSON and continue
            chunks = list(
                transport._stream_request("test.sock", "cap", {}, request_id="test")
            )

            assert chunks == ["valid"]

    def test_stream_request_partial_messages(self, transport):
        """Test _stream_request handles partial messages correctly."""
        mock_socket = Mock()

        # Simulate data coming in partial chunks
        mock_socket.recv.side_effect = [
            b'{"chunk": "da',  # Partial
            b'ta1", "id": "test"}\n{"chunk": "data2"',  # Complete first, partial second
            b', "id": "test"}\n',  # Complete second
            json.dumps({"complete": True, "id": "test"}).encode("utf-8") + b"\n",
            b"",
        ]

        with patch("socket.socket", return_value=mock_socket):
            chunks = list(
                transport._stream_request("test.sock", "cap", {}, request_id="test")
            )

            assert chunks == ["data1", "data2"]

    def test_stream_request_socket_cleanup(self, transport):
        """Test _stream_request cleans up socket on error."""
        mock_socket = Mock()
        mock_socket.recv.side_effect = Exception("Socket error")

        with patch("socket.socket", return_value=mock_socket):
            # The error will be wrapped in TransportError by the caller
            # but _stream_request itself will raise the original exception
            try:
                list(transport._stream_request("test.sock", "cap", {}))
            except Exception:
                pass  # Expected

            # Socket should be closed
            mock_socket.close.assert_called()

    def test_send_request_no_response(self, transport):
        """Test _send_request when no response is received."""
        mock_socket = Mock()
        mock_socket.recv.return_value = b""  # No data

        with patch("socket.socket", return_value=mock_socket):
            with pytest.raises(TransportError) as exc_info:
                transport._send_request("test.sock", "cap", {})

            assert "No response received" in str(exc_info.value)

    def test_send_request_error_response(self, transport):
        """Test _send_request handles error responses."""
        mock_socket = Mock()
        mock_socket.recv.side_effect = [
            json.dumps({"error": "Agent error", "code": 500}).encode("utf-8") + b"\n",
            b"",
        ]

        with patch("socket.socket", return_value=mock_socket):
            with pytest.raises(TransportError) as exc_info:
                transport._send_request("test.sock", "cap", {})

            assert "Agent error" in str(exc_info.value)

    def test_registry_start_already_running(self, registry):
        """Test registry.start() when already running."""
        registry._running = True

        # Should return early without starting servers
        with patch.object(registry, "_start_agent_server") as mock_start:
            registry.start()
            mock_start.assert_not_called()

    def test_registry_stop_cleanup_errors(self, registry):
        """Test registry.stop() handles cleanup errors gracefully."""
        # Set up registry with mocked components
        registry._running = True

        # Add mock socket that raises on close
        mock_socket = Mock()
        mock_socket.close.side_effect = Exception("Close error")
        registry._server_sockets["test"] = mock_socket

        # Add mock thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        registry._server_threads["test"] = mock_thread

        # Add socket path
        registry._socket_paths["test"] = "/tmp/test.sock"

        # Stop should handle errors gracefully
        registry.stop()

        assert registry._running is False
        assert len(registry._server_sockets) == 0
        assert len(registry._server_threads) == 0

    def test_start_agent_server_already_exists(self, registry):
        """Test _start_agent_server when server already exists."""
        # Register agent
        registry.register_agent("existing", lambda c, p: {})

        # Add to server sockets
        registry._server_sockets["existing"] = Mock()

        # Should return early
        with patch("socket.socket") as mock_socket:
            registry._start_agent_server("existing")
            mock_socket.assert_not_called()

    def test_start_agent_server_tcp_windows(self, registry):
        """Test _start_agent_server creates TCP socket on Windows."""
        # Register agent with TCP socket path
        registry._socket_paths["tcp-agent"] = "127.0.0.1:9999"
        registry._agents["tcp-agent"] = lambda c, p: {}

        mock_socket = Mock()

        with patch("socket.socket", return_value=mock_socket):
            registry._start_agent_server("tcp-agent")

            # Verify TCP socket setup
            mock_socket.setsockopt.assert_called_with(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
            mock_socket.bind.assert_called_with(("127.0.0.1", 9999))
            mock_socket.listen.assert_called_with(5)

    def test_start_agent_server_unix_cleanup(self, registry):
        """Test _start_agent_server cleans up Unix socket with secure permissions."""
        # Create a temporary socket file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            socket_path = tmp.name

        registry._socket_paths["unix-agent"] = socket_path
        registry._agents["unix-agent"] = lambda c, p: {}

        mock_socket = Mock()

        with patch("socket.socket", return_value=mock_socket):
            with patch("os.path.exists", return_value=True):
                with patch("os.unlink") as mock_unlink:
                    with patch("os.chmod") as mock_chmod:
                        with patch("os.umask") as mock_umask:
                            # Mock umask returns original umask value
                            mock_umask.return_value = 0o022

                            registry._start_agent_server("unix-agent")

                            # Should unlink existing file
                            mock_unlink.assert_called_with(socket_path)
                            # Should set restrictive umask before socket creation
                            mock_umask.assert_any_call(0o077)
                            # Should restore original umask after socket creation
                            mock_umask.assert_any_call(0o022)
                            # Should set explicit permissions
                            mock_chmod.assert_called_with(socket_path, 0o700)

    def test_unregister_agent_socket_close_error(self, registry):
        """Test unregister_agent handles socket close errors."""
        # Register agent
        registry.register_agent("test", lambda c, p: {})

        # Add mock socket that fails to close
        mock_socket = Mock()
        mock_socket.close.side_effect = Exception("Close failed")
        registry._server_sockets["test"] = mock_socket

        # Add thread
        registry._server_threads["test"] = Mock()

        # Should still unregister successfully
        result = registry.unregister_agent("test")
        assert result is True
        assert "test" not in registry._agents

    def test_unregister_agent_unix_socket_cleanup_error(self, registry):
        """Test unregister_agent handles Unix socket cleanup errors."""
        # Register agent with Unix socket
        registry.register_agent("unix-test", lambda c, p: {})
        registry._socket_paths["unix-test"] = "/tmp/test.sock"

        with patch("os.path.exists", return_value=True):
            with patch("os.unlink", side_effect=Exception("Unlink failed")):
                # Should still unregister successfully
                result = registry.unregister_agent("unix-test")
                assert result is True
                assert "unix-test" not in registry._agents
