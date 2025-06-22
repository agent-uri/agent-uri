"""
Tests for local transport agent registration and handling functionality.

This module tests agent registration, handler invocation, capability routing,
and error handling for the local transport implementation.
"""

import sys

import pytest

from agent_uri.transport.base import TransportError
from agent_uri.transport.transports.local import LocalTransport


class TestLocalTransportAgentHandling:
    """Test local transport agent registration and handling."""

    @pytest.fixture
    def transport(self):
        """Create a LocalTransport instance."""
        return LocalTransport()

    def test_register_agent_basic(self, transport):
        """Test basic agent registration."""

        def simple_handler(capability: str, params: dict):
            return f"handled {capability} with {params}"

        socket_path = transport.register_agent("test_agent", simple_handler)
        assert socket_path is not None
        assert isinstance(socket_path, str)

        # Verify agent is registered
        agents = transport.list_local_agents()
        assert "test_agent" in agents

        # Clean up
        transport.unregister_agent("test_agent")

    def test_register_agent_with_custom_socket_path(self, transport):
        """Test agent registration with custom socket path."""

        def handler(capability: str, params: dict):
            return {"capability": capability, "params": params}

        custom_path = (
            "/tmp/test_agent.sock"
            if not sys.platform.startswith("win")
            else "127.0.0.1:9999"
        )
        socket_path = transport.register_agent("test_agent", handler, custom_path)

        if not sys.platform.startswith("win"):
            assert socket_path == custom_path
        else:
            assert socket_path.startswith("127.0.0.1:")

        transport.unregister_agent("test_agent")

    def test_unregister_agent_success(self, transport):
        """Test successful agent unregistration."""

        def handler(capability: str, params: dict):
            return "test result"

        transport.register_agent("test_agent", handler)

        # Verify agent is registered
        agents = transport.list_local_agents()
        assert "test_agent" in agents

        # Unregister and verify
        result = transport.unregister_agent("test_agent")
        assert result is True

        agents = transport.list_local_agents()
        assert "test_agent" not in agents

    def test_unregister_nonexistent_agent(self, transport):
        """Test unregistering non-existent agent."""
        result = transport.unregister_agent("nonexistent_agent")
        assert result is False

    def test_parse_endpoint_with_protocol(self, transport):
        """Test endpoint parsing with protocol prefix."""
        # Test local:// protocol
        agent_name = transport._parse_endpoint("local://my_agent")
        assert agent_name == "my_agent"

        # Test agent+local:// protocol
        agent_name = transport._parse_endpoint("agent+local://my_agent")
        assert agent_name == "my_agent"

    def test_parse_endpoint_without_protocol(self, transport):
        """Test endpoint parsing without protocol prefix."""
        agent_name = transport._parse_endpoint("my_agent")
        assert agent_name == "my_agent"

        # Test with path components
        agent_name = transport._parse_endpoint("my_agent/some/path")
        assert agent_name == "my_agent"

    def test_invoke_registered_agent(self, transport):
        """Test invoking a registered agent."""

        def math_handler(capability: str, params: dict):
            if capability == "add":
                return params["a"] + params["b"]
            elif capability == "multiply":
                return params["a"] * params["b"]
            else:
                raise ValueError(f"Unknown capability: {capability}")

        transport.register_agent("math_agent", math_handler)

        # Test addition
        result = transport.invoke("math_agent", "add", {"a": 5, "b": 3})
        assert result == 8

        # Test multiplication
        result = transport.invoke("math_agent", "multiply", {"a": 4, "b": 6})
        assert result == 24

        transport.unregister_agent("math_agent")

    def test_invoke_nonexistent_agent(self, transport):
        """Test invoking a non-existent agent."""
        with pytest.raises(TransportError):
            transport.invoke("nonexistent_agent", "test", {})

    def test_agent_handler_exception(self, transport):
        """Test handling exceptions from agent handlers."""

        def failing_handler(capability: str, params: dict):
            raise ValueError("Handler intentionally failed")

        transport.register_agent("failing_agent", failing_handler)

        with pytest.raises(TransportError) as excinfo:
            transport.invoke("failing_agent", "test", {})

        assert "Handler intentionally failed" in str(excinfo.value)
        transport.unregister_agent("failing_agent")

    def test_stream_from_registered_agent(self, transport):
        """Test streaming from a registered agent."""

        def streaming_handler(capability: str, params: dict):
            if capability == "count":
                count = params.get("count", 5)
                for i in range(count):
                    yield {"number": i, "square": i * i}
            else:
                raise ValueError(f"Unknown capability: {capability}")

        transport.register_agent("stream_agent", streaming_handler)

        results = list(transport.stream("stream_agent", "count", {"count": 3}))
        assert len(results) == 3
        assert results[0] == {"number": 0, "square": 0}
        assert results[2] == {"number": 2, "square": 4}

        transport.unregister_agent("stream_agent")

    def test_agent_with_complex_parameters(self, transport):
        """Test agent handling complex parameter structures."""

        def complex_handler(capability: str, params: dict):
            if capability == "process_data":
                data = params["data"]
                filters = params.get("filters", [])
                options = params.get("options", {})

                result = (
                    [item for item in data if any(f in str(item) for f in filters)]
                    if filters
                    else data
                )
                if options.get("sort", False):
                    result = sorted(result)

                return {
                    "processed_count": len(result),
                    "data": result,
                    "filters_applied": filters,
                    "sorted": options.get("sort", False),
                }
            else:
                raise ValueError(f"Unknown capability: {capability}")

        transport.register_agent("data_processor", complex_handler)

        result = transport.invoke(
            "data_processor",
            "process_data",
            {
                "data": ["apple", "banana", "cherry", "date"],
                "filters": ["a", "e"],
                "options": {"sort": True},
            },
        )

        assert result["processed_count"] == 4  # All items match "a" or "e" filter
        assert "apple" in result["data"]
        assert "cherry" in result["data"]
        assert "date" in result["data"]
        assert "banana" in result["data"]  # "banana" contains "a"
        assert result["sorted"] is True

        transport.unregister_agent("data_processor")

    def test_multiple_agents_registration(self, transport):
        """Test registering multiple agents simultaneously."""

        def agent1_handler(capability: str, params: dict):
            return f"agent1 handled {capability}"

        def agent2_handler(capability: str, params: dict):
            return f"agent2 handled {capability}"

        def agent3_handler(capability: str, params: dict):
            return f"agent3 handled {capability}"

        # Register multiple agents
        transport.register_agent("agent1", agent1_handler)
        transport.register_agent("agent2", agent2_handler)
        transport.register_agent("agent3", agent3_handler)

        # Verify all are registered
        agents = transport.list_local_agents()
        assert "agent1" in agents
        assert "agent2" in agents
        assert "agent3" in agents

        # Test each agent works
        assert transport.invoke("agent1", "test", {}) == "agent1 handled test"
        assert transport.invoke("agent2", "test", {}) == "agent2 handled test"
        assert transport.invoke("agent3", "test", {}) == "agent3 handled test"

        # Clean up
        transport.unregister_agent("agent1")
        transport.unregister_agent("agent2")
        transport.unregister_agent("agent3")

    def test_agent_timeout_handling(self, transport):
        """Test agent invocation with timeout."""
        import time

        def slow_handler(capability: str, params: dict):
            delay = params.get("delay", 0.1)
            time.sleep(delay)
            return f"completed after {delay}s"

        transport.register_agent("slow_agent", slow_handler)

        # Test with sufficient timeout
        result = transport.invoke("slow_agent", "test", {"delay": 0.05}, timeout=1)
        assert "completed after 0.05s" in result

        transport.unregister_agent("slow_agent")

    def test_agent_with_generator_response(self, transport):
        """Test agent that returns generator for streaming."""

        def generator_handler(capability: str, params: dict):
            if capability == "fibonacci":

                def fibonacci_generator():
                    n = params.get("count", 5)
                    a, b = 0, 1
                    for _ in range(n):
                        yield {"value": a}
                        a, b = b, a + b

                return fibonacci_generator()
            else:
                return "non-streaming response"

        transport.register_agent("generator_agent", generator_handler)

        # Test streaming capability
        results = list(transport.stream("generator_agent", "fibonacci", {"count": 4}))
        assert len(results) == 4
        assert results[0] == {"value": 0}
        assert results[1] == {"value": 1}
        assert results[2] == {"value": 1}
        assert results[3] == {"value": 2}

        # Test non-streaming capability
        result = transport.invoke("generator_agent", "other", {})
        assert result == "non-streaming response"

        transport.unregister_agent("generator_agent")

    def test_agent_state_isolation(self, transport):
        """Test that different agents have isolated state."""

        # Create handlers with internal state
        def counter1_handler(capability: str, params: dict):
            if not hasattr(counter1_handler, "count"):
                counter1_handler.count = 0
            counter1_handler.count += params.get("increment", 1)
            return {"agent": "counter1", "count": counter1_handler.count}

        def counter2_handler(capability: str, params: dict):
            if not hasattr(counter2_handler, "count"):
                counter2_handler.count = 0
            counter2_handler.count += params.get("increment", 1)
            return {"agent": "counter2", "count": counter2_handler.count}

        transport.register_agent("counter1", counter1_handler)
        transport.register_agent("counter2", counter2_handler)

        # Test that counters are isolated
        result1 = transport.invoke("counter1", "increment", {"increment": 5})
        result2 = transport.invoke("counter2", "increment", {"increment": 3})
        result1_again = transport.invoke("counter1", "increment", {"increment": 2})

        assert result1["count"] == 5
        assert result2["count"] == 3
        assert result1_again["count"] == 7  # 5 + 2

        transport.unregister_agent("counter1")
        transport.unregister_agent("counter2")

    def test_agent_capability_routing(self, transport):
        """Test that agents can handle different capabilities differently."""

        def service_handler(capability: str, params: dict):
            if capability == "status":
                return {"status": "running", "uptime": "1h 30m"}
            elif capability == "config":
                return {"config": params.get("key", "default_value")}
            elif capability == "restart":
                return {"action": "restart", "success": True}
            else:
                return {"error": f"Unknown capability: {capability}"}

        transport.register_agent("service", service_handler)

        # Test different capabilities
        status_result = transport.invoke("service", "status", {})
        assert status_result["status"] == "running"

        config_result = transport.invoke("service", "config", {"key": "timeout"})
        assert config_result["config"] == "timeout"

        restart_result = transport.invoke("service", "restart", {})
        assert restart_result["success"] is True

        error_result = transport.invoke("service", "unknown", {})
        assert "Unknown capability" in error_result["error"]

        transport.unregister_agent("service")

    def test_agent_with_custom_socket_path_per_platform(self, transport):
        """Test agent registration with platform-specific socket paths."""

        def test_handler(capability: str, params: dict):
            return {"platform": sys.platform, "capability": capability}

        # Register agent with platform-appropriate socket path
        if sys.platform.startswith("win"):
            custom_path = "127.0.0.1:9998"
        else:
            custom_path = "/tmp/platform_test_agent.sock"

        transport.register_agent("platform_agent", test_handler, custom_path)

        # Verify agent works
        result = transport.invoke("platform_agent", "platform_test", {})
        assert result["capability"] == "platform_test"
        assert "platform" in result

        transport.unregister_agent("platform_agent")

    def test_list_agents_empty(self, transport):
        """Test listing agents when none are registered."""
        agents = transport.list_local_agents()
        assert isinstance(agents, dict)
        # May have some default agents, so just check it's a dict

    def test_agent_registry_singleton(self, transport):
        """Test that the agent registry is a singleton."""
        # Create another transport instance
        transport2 = LocalTransport()

        # Register agent with first transport
        def shared_handler(capability: str, params: dict):
            return "shared response"

        transport.register_agent("shared_agent", shared_handler)

        # Should be visible from second transport (singleton registry)
        agents1 = transport.list_local_agents()
        agents2 = transport2.list_local_agents()

        assert "shared_agent" in agents1
        assert "shared_agent" in agents2

        # Both should be able to invoke the agent
        result1 = transport.invoke("shared_agent", "test", {})
        result2 = transport2.invoke("shared_agent", "test", {})

        assert result1 == "shared response"
        assert result2 == "shared response"

        # Clean up
        transport.unregister_agent("shared_agent")

    def test_agent_endpoint_parsing_edge_cases(self, transport):
        """Test edge cases in endpoint parsing."""
        # Test empty string
        result = transport._parse_endpoint("")
        assert result == ""

        # Test with multiple slashes
        result = transport._parse_endpoint("agent://my_agent/path/to/resource")
        assert result == "my_agent"

        # Test with query parameters (should be ignored)
        result = transport._parse_endpoint("my_agent?param=value")
        assert result == "my_agent"

    def test_concurrent_agent_access(self, transport):
        """Test concurrent access to the same agent."""
        import threading
        import time

        results = []

        def concurrent_handler(capability: str, params: dict):
            thread_id = threading.current_thread().ident
            time.sleep(0.01)  # Small delay to test concurrency
            return {"thread_id": thread_id, "request_id": params.get("request_id")}

        transport.register_agent("concurrent_agent", concurrent_handler)

        def make_request(request_id):
            result = transport.invoke(
                "concurrent_agent", "test", {"request_id": request_id}
            )
            results.append(result)

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all requests completed
        assert len(results) == 3
        request_ids = [r["request_id"] for r in results]
        assert set(request_ids) == {0, 1, 2}

        transport.unregister_agent("concurrent_agent")

    def test_agent_error_handling(self, transport):
        """Test comprehensive error handling in agent operations."""
        # Test invoking with invalid agent name
        with pytest.raises(TransportError):
            transport.invoke("", "test", {})
