"""
Tests for the local transport implementation.

This module contains comprehensive tests for the LocalTransport class
and LocalAgentRegistry.
"""

import json
import threading
import time
from unittest.mock import Mock, patch

import pytest

from ..base import TransportError, TransportTimeoutError
from ..transports.local import LocalAgentRegistry, LocalTransport


class TestLocalAgentRegistry:
    """Tests for the LocalAgentRegistry class."""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Reset registry state before each test."""
        # Clear singleton instance to ensure clean state
        LocalAgentRegistry._instance = None
        yield
        # Clean up after test
        if LocalAgentRegistry._instance:
            registry = LocalAgentRegistry.get_instance()
            registry.stop()
            LocalAgentRegistry._instance = None

    def test_singleton_instance(self):
        """Test that registry is a singleton."""
        registry1 = LocalAgentRegistry.get_instance()
        registry2 = LocalAgentRegistry.get_instance()
        assert registry1 is registry2

    def test_register_agent_basic(self):
        """Test basic agent registration."""
        registry = LocalAgentRegistry.get_instance()

        def mock_handler(capability, params):
            return {"capability": capability, "params": params}

        socket_path = registry.register_agent("test-agent", mock_handler)

        assert "test-agent" in registry._agents
        assert registry._agents["test-agent"] is mock_handler
        assert socket_path is not None
        assert isinstance(socket_path, str)

    def test_register_agent_custom_socket_path(self):
        """Test agent registration with custom socket path."""
        registry = LocalAgentRegistry.get_instance()

        def mock_handler(capability, params):
            return {"result": "success"}

        custom_path = "127.0.0.1:9999"
        socket_path = registry.register_agent("test-agent", mock_handler, custom_path)

        assert socket_path == custom_path
        assert registry.get_socket_path("test-agent") == custom_path

    @patch("sys.platform", "win32")
    def test_register_agent_windows_socket_path(self):
        """Test agent registration on Windows creates TCP socket."""
        registry = LocalAgentRegistry.get_instance()

        def mock_handler(capability, params):
            return {"result": "success"}

        with patch.object(registry, "_find_free_port", return_value=12345):
            socket_path = registry.register_agent("test-agent", mock_handler)
            assert socket_path == "127.0.0.1:12345"

    @patch("sys.platform", "linux")
    def test_register_agent_unix_socket_path(self):
        """Test agent registration on Unix creates domain socket."""
        registry = LocalAgentRegistry.get_instance()

        def mock_handler(capability, params):
            return {"result": "success"}

        socket_path = registry.register_agent("test-agent", mock_handler)
        assert socket_path.endswith(".sock")
        assert "/tmp/" in socket_path or "/var/folders/" in socket_path

    def test_unregister_agent_success(self):
        """Test successful agent unregistration."""
        registry = LocalAgentRegistry.get_instance()

        def mock_handler(capability, params):
            return {"result": "success"}

        registry.register_agent("test-agent", mock_handler)
        assert registry.unregister_agent("test-agent") is True
        assert "test-agent" not in registry._agents
        assert registry.get_agent("test-agent") is None

    def test_unregister_agent_not_found(self):
        """Test unregistering non-existent agent."""
        registry = LocalAgentRegistry.get_instance()
        assert registry.unregister_agent("nonexistent") is False

    def test_get_agent(self):
        """Test getting registered agent."""
        registry = LocalAgentRegistry.get_instance()

        def mock_handler(capability, params):
            return {"result": "success"}

        registry.register_agent("test-agent", mock_handler)
        retrieved_handler = registry.get_agent("test-agent")
        assert retrieved_handler is mock_handler

    def test_get_agent_not_found(self):
        """Test getting non-existent agent."""
        registry = LocalAgentRegistry.get_instance()
        assert registry.get_agent("nonexistent") is None

    def test_get_socket_path(self):
        """Test getting socket path for agent."""
        registry = LocalAgentRegistry.get_instance()

        def mock_handler(capability, params):
            return {"result": "success"}

        socket_path = registry.register_agent("test-agent", mock_handler)
        retrieved_path = registry.get_socket_path("test-agent")
        assert retrieved_path == socket_path

    def test_get_socket_path_not_found(self):
        """Test getting socket path for non-existent agent."""
        registry = LocalAgentRegistry.get_instance()
        assert registry.get_socket_path("nonexistent") is None

    def test_list_agents(self):
        """Test listing all registered agents."""
        registry = LocalAgentRegistry.get_instance()

        def handler1(capability, params):
            return {"agent": "1"}

        def handler2(capability, params):
            return {"agent": "2"}

        path1 = registry.register_agent("agent1", handler1)
        path2 = registry.register_agent("agent2", handler2)

        agents = registry.list_agents()
        assert isinstance(agents, dict)
        assert agents["agent1"] == path1
        assert agents["agent2"] == path2

    def test_start_stop_registry(self):
        """Test starting and stopping the registry."""
        registry = LocalAgentRegistry.get_instance()

        def mock_handler(capability, params):
            return {"result": "success"}

        # Register agent before starting
        registry.register_agent("test-agent", mock_handler)

        # Start registry
        registry.start()
        assert registry._running is True

        # Stop registry
        registry.stop()
        assert registry._running is False

    def test_find_free_port(self):
        """Test finding a free port."""
        registry = LocalAgentRegistry.get_instance()
        port = registry._find_free_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535


class TestLocalTransport:
    """Tests for the LocalTransport class."""

    @pytest.fixture(autouse=True)
    def setup_transport(self):
        """Setup clean transport for each test."""
        # Clear singleton instance
        LocalAgentRegistry._instance = None
        yield
        # Cleanup
        if LocalAgentRegistry._instance:
            registry = LocalAgentRegistry.get_instance()
            registry.stop()
            LocalAgentRegistry._instance = None

    def test_transport_initialization(self):
        """Test transport initialization."""
        transport = LocalTransport()
        assert transport.protocol == "local"
        assert transport._registry is not None

    def test_invoke_direct_handler(self):
        """Test invoking capability with direct handler."""
        transport = LocalTransport()

        def test_handler(capability, params):
            return {"capability": capability, "params": params, "result": "success"}

        # Register agent
        transport._registry.register_agent("test-agent", test_handler)

        # Invoke capability
        result = transport.invoke("test-agent", "echo", {"message": "hello"})

        assert result["capability"] == "echo"
        assert result["params"]["message"] == "hello"
        assert result["result"] == "success"

    def test_invoke_generator_result(self):
        """Test invoking capability that returns a generator."""
        transport = LocalTransport()

        def generator_handler(capability, params):
            for i in range(3):
                yield {"item": i, "message": params.get("message", "")}

        transport._registry.register_agent("test-agent", generator_handler)

        result = transport.invoke("test-agent", "stream", {"message": "test"})

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["item"] == 0
        assert result[0]["message"] == "test"

    def test_invoke_handler_exception(self):
        """Test invoking capability that raises an exception."""
        transport = LocalTransport()

        def error_handler(capability, params):
            raise ValueError("Test error")

        transport._registry.register_agent("test-agent", error_handler)

        with pytest.raises(TransportError) as excinfo:
            transport.invoke("test-agent", "error", {})

        assert "Test error" in str(excinfo.value)

    def test_invoke_timeout_parameter(self):
        """Test invoke with custom timeout."""
        transport = LocalTransport()

        def slow_handler(capability, params):
            time.sleep(0.1)  # Small delay
            return {"result": "success"}

        transport._registry.register_agent("test-agent", slow_handler)

        # Should succeed with sufficient timeout
        result = transport.invoke("test-agent", "slow", {}, timeout=1)
        assert result["result"] == "success"

    def test_invoke_default_timeout(self):
        """Test invoke uses default timeout when none specified."""
        transport = LocalTransport()

        def quick_handler(capability, params):
            return {"result": "success"}

        transport._registry.register_agent("test-agent", quick_handler)

        # Should use default timeout (60 seconds)
        result = transport.invoke("test-agent", "quick", {})
        assert result["result"] == "success"

    def test_invoke_agent_not_in_registry(self):
        """Test invoking agent not in registry falls back to socket."""
        transport = LocalTransport()

        # Mock the _send_request method to avoid actual socket communication
        with patch.object(transport, "_send_request") as mock_send:
            mock_send.return_value = {"result": "socket_success"}

            result = transport.invoke("nonexistent-agent", "test", {})
            assert result["result"] == "socket_success"
            mock_send.assert_called_once()

    def test_invoke_socket_timeout(self):
        """Test socket communication timeout."""
        transport = LocalTransport()

        with patch.object(transport, "_send_request") as mock_send:
            mock_send.side_effect = TimeoutError("Request timed out")

            with pytest.raises(TransportTimeoutError) as excinfo:
                transport.invoke("nonexistent-agent", "test", {}, timeout=1)

            assert "timed out after 1 seconds" in str(excinfo.value)

    def test_invoke_socket_error(self):
        """Test socket communication error."""
        transport = LocalTransport()

        with patch.object(transport, "_send_request") as mock_send:
            mock_send.side_effect = ConnectionError("Connection failed")

            with pytest.raises(TransportError) as excinfo:
                transport.invoke("nonexistent-agent", "test", {})

            assert "Connection failed" in str(excinfo.value)

    def test_stream_direct_handler(self):
        """Test streaming with direct handler."""
        transport = LocalTransport()

        def stream_handler(capability, params):
            for i in range(3):
                yield {"chunk": i, "data": params.get("data", "")}

        transport._registry.register_agent("test-agent", stream_handler)

        results = list(transport.stream("test-agent", "stream", {"data": "test"}))

        assert len(results) == 3
        assert results[0]["chunk"] == 0
        assert results[0]["data"] == "test"

    def test_stream_non_generator_handler(self):
        """Test streaming with non-generator handler."""
        transport = LocalTransport()

        def non_stream_handler(capability, params):
            # For streaming, even non-generator handlers should yield
            return [{"result": "single_response"}]

        transport._registry.register_agent("test-agent", non_stream_handler)

        # When the handler returns a list, stream should iterate over it
        results = list(transport.stream("test-agent", "test", {}))

        assert len(results) == 1
        assert results[0]["result"] == "single_response"

    def test_stream_handler_exception(self):
        """Test streaming with handler that raises exception."""
        transport = LocalTransport()

        def error_handler(capability, params):
            raise RuntimeError("Stream error")

        transport._registry.register_agent("test-agent", error_handler)

        with pytest.raises(TransportError) as excinfo:
            list(transport.stream("test-agent", "error", {}))

        assert "Stream error" in str(excinfo.value)

    def test_stream_agent_not_in_registry(self):
        """Test streaming with agent not in registry."""
        transport = LocalTransport()

        with patch.object(transport, "_stream_request") as mock_stream:
            mock_stream.return_value = iter([{"chunk": 1}, {"chunk": 2}])

            results = list(transport.stream("nonexistent-agent", "test", {}))
            assert len(results) == 2
            mock_stream.assert_called_once()

    def test_stream_timeout(self):
        """Test streaming timeout."""
        transport = LocalTransport()

        with patch.object(transport, "_stream_request") as mock_stream:
            mock_stream.side_effect = TimeoutError("Stream timed out")

            with pytest.raises(TransportTimeoutError):
                list(transport.stream("nonexistent-agent", "test", {}, timeout=1))

    def test_parse_endpoint(self):
        """Test endpoint parsing in transport."""
        transport = LocalTransport()

        # Test simple agent name
        assert transport._parse_endpoint("agent-name") == "agent-name"

        # Test local:// URL
        assert transport._parse_endpoint("local://agent-name") == "agent-name"

        # Test agent+local:// URL
        assert transport._parse_endpoint("agent+local://agent-name") == "agent-name"

        # Test with path components (should only return first part)
        assert transport._parse_endpoint("agent-name/capability") == "agent-name"
        assert (
            transport._parse_endpoint("local://agent-name/capability") == "agent-name"
        )

    def test_send_request_structure(self):
        """Test that _send_request builds correct request structure."""
        transport = LocalTransport()

        # We'll test this by mocking the socket operations
        # since _send_request internally builds the request structure
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket

            # Capture what gets sent
            sent_data = []

            def capture_send(data):
                sent_data.append(data)

            mock_socket.sendall.side_effect = capture_send

            # Mock response - return data with newline and then empty to signal end
            response_data = json.dumps({"result": "success"}).encode() + b"\n"
            mock_socket.recv.side_effect = [response_data, b""]

            # Make request
            transport._send_request(
                "127.0.0.1:8000",
                "test-capability",
                {"param": "value"},
                timeout=5,
                request_id="test-123",
            )

            # Verify request structure
            assert len(sent_data) == 1
            request_data = json.loads(sent_data[0].decode().strip())
            assert request_data["capability"] == "test-capability"
            assert request_data["params"]["param"] == "value"
            assert request_data["id"] == "test-123"
            assert request_data["streaming"] is False

    def test_send_request_mock(self):
        """Test _send_request with mocked socket operations."""
        transport = LocalTransport()

        # Mock socket operations
        mock_socket = Mock()

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            # Mock response properly
            response_data = json.dumps({"result": "success"}).encode() + b"\n"
            mock_socket.recv.side_effect = [response_data, b""]

            result = transport._send_request(
                "127.0.0.1:8000",
                "test",
                {"param": "value"},
                timeout=5,
                request_id="test-123",
            )

            assert result == "success"  # _send_request returns response.get("result")

    def test_registry_cleanup(self):
        """Test that registry can be properly cleaned up."""
        transport = LocalTransport()

        # Register an agent to create some state
        def test_handler(capability, params):
            return {"result": "success"}

        transport._registry.register_agent("test-agent", test_handler)

        # Stop the registry
        transport._registry.stop()

        # Registry should be stopped
        assert not transport._registry._running


class TestLocalTransportIntegration:
    """Integration tests for local transport."""

    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup for integration tests."""
        LocalAgentRegistry._instance = None
        yield
        if LocalAgentRegistry._instance:
            registry = LocalAgentRegistry.get_instance()
            registry.stop()
            LocalAgentRegistry._instance = None

    def test_full_agent_communication_cycle(self):
        """Test complete agent registration and communication cycle."""
        transport = LocalTransport()

        # Define streaming handler separately to avoid generator issue
        def stream_handler(params):
            for i in range(params.get("count", 3)):
                yield {"item": i, "data": params.get("data", "")}

        # Define a comprehensive test agent
        def comprehensive_handler(capability, params):
            if capability == "echo":
                return {"echo": params.get("message", "")}
            elif capability == "add":
                return {"result": params.get("a", 0) + params.get("b", 0)}
            elif capability == "stream":
                # Return the generator, don't use yield here
                return stream_handler(params)
            else:
                raise ValueError(f"Unknown capability: {capability}")

        # Register agent
        socket_path = transport._registry.register_agent(
            "comprehensive-agent", comprehensive_handler
        )

        # Test echo capability
        result = transport.invoke("comprehensive-agent", "echo", {"message": "hello"})
        assert isinstance(result, dict)
        assert result.get("echo") == "hello"

        # Test add capability
        result = transport.invoke("comprehensive-agent", "add", {"a": 5, "b": 3})
        assert isinstance(result, dict)
        assert result.get("result") == 8

        # Test streaming capability
        results = list(
            transport.stream(
                "comprehensive-agent", "stream", {"count": 2, "data": "test"}
            )
        )
        assert len(results) == 2
        assert results[0]["item"] == 0
        assert results[1]["data"] == "test"

        # Test error handling
        with pytest.raises(TransportError):
            transport.invoke("comprehensive-agent", "nonexistent", {})

        # Verify agent is in registry
        agents = transport._registry.list_agents()
        assert "comprehensive-agent" in agents
        assert agents["comprehensive-agent"] == socket_path

    def test_multiple_agents_isolation(self):
        """Test that multiple agents work independently."""
        transport = LocalTransport()

        def agent1_handler(capability, params):
            return {"agent": "1", "capability": capability, "params": params}

        def agent2_handler(capability, params):
            return {"agent": "2", "capability": capability, "params": params}

        # Register multiple agents
        transport._registry.register_agent("agent1", agent1_handler)
        transport._registry.register_agent("agent2", agent2_handler)

        # Test both agents
        result1 = transport.invoke("agent1", "test", {"data": "for_agent1"})
        result2 = transport.invoke("agent2", "test", {"data": "for_agent2"})

        assert result1["agent"] == "1"
        assert result1["params"]["data"] == "for_agent1"
        assert result2["agent"] == "2"
        assert result2["params"]["data"] == "for_agent2"

    @pytest.mark.slow
    def test_concurrent_requests(self):
        """Test concurrent requests to the same agent."""
        transport = LocalTransport()

        def slow_handler(capability, params):
            # Small delay to test concurrency
            time.sleep(0.01)
            return {"request_id": params.get("request_id"), "result": "success"}

        transport._registry.register_agent("slow-agent", slow_handler)

        results = []
        threads = []

        def make_request(req_id):
            result = transport.invoke("slow-agent", "test", {"request_id": req_id})
            results.append(result)

        # Start multiple concurrent requests
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(f"req_{i}",))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join(timeout=5)

        # Verify all requests completed successfully
        assert len(results) == 5
        request_ids = {r["request_id"] for r in results}
        assert len(request_ids) == 5  # All unique
