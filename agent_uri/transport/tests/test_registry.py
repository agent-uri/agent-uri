"""
Tests for the transport registry.

This module contains tests for the TransportRegistry class.
"""

import pytest

from ..base import AgentTransport, TransportNotSupportedError
from ..registry import TransportRegistry


class MockTransport(AgentTransport):
    """Mock transport implementation for testing."""

    def __init__(self, protocol_name="mock"):
        self._protocol_name = protocol_name

    @property
    def protocol(self):
        return self._protocol_name

    def invoke(
        self, endpoint, capability, params=None, headers=None, timeout=None, **kwargs
    ):
        return {"status": "success", "endpoint": endpoint, "capability": capability}

    def stream(
        self, endpoint, capability, params=None, headers=None, timeout=None, **kwargs
    ):
        yield {"status": "streaming", "endpoint": endpoint}
        yield {"status": "complete"}


class TestTransportRegistry:
    """Tests for the TransportRegistry class."""

    def test_register_transport(self):
        """Test registering a transport."""
        registry = TransportRegistry()
        registry.register_transport(MockTransport)

        assert "mock" in registry._transports
        assert isinstance(registry._transports["mock"], type)
        assert registry._transports["mock"] == MockTransport

    def test_unregister_transport(self):
        """Test unregistering a transport."""
        registry = TransportRegistry()
        registry.register_transport(MockTransport)

        # First unregister should succeed
        assert registry.unregister_transport("mock") is True
        assert "mock" not in registry._transports

        # Second unregister should fail
        assert registry.unregister_transport("mock") is False

    def test_get_transport(self):
        """Test getting a transport."""
        registry = TransportRegistry()
        registry.register_transport(MockTransport)

        transport = registry.get_transport("mock")
        assert isinstance(transport, MockTransport)
        assert transport.protocol == "mock"

        # Should return the same instance for the same protocol
        transport2 = registry.get_transport("mock")
        assert transport is transport2

    def test_get_transport_not_found(self):
        """Test getting a non-existent transport."""
        registry = TransportRegistry()

        with pytest.raises(TransportNotSupportedError):
            registry.get_transport("nonexistent")

    def test_fallback_to_https(self):
        """Test fallback to HTTPS transport for 'agent' protocol."""
        registry = TransportRegistry()
        https_transport = MockTransport("https")
        registry._transports["https"] = lambda: https_transport

        # Should use HTTPS transport for 'agent' protocol
        transport = registry.get_transport("agent")
        assert transport is https_transport

    def test_is_protocol_supported(self):
        """Test checking if a protocol is supported."""
        registry = TransportRegistry()
        registry.register_transport(MockTransport)
        registry.register_transport(lambda: MockTransport("https"))

        assert registry.is_protocol_supported("mock") is True
        assert registry.is_protocol_supported("nonexistent") is False
        assert registry.is_protocol_supported("agent") is True  # Due to https fallback

    def test_list_supported_protocols(self):
        """Test listing supported protocols."""
        registry = TransportRegistry()
        registry.register_transport(MockTransport)
        registry.register_transport(lambda: MockTransport("https"))
        registry.register_transport(lambda: MockTransport("wss"))

        protocols = registry.list_supported_protocols()
        assert isinstance(protocols, set)
        assert "mock" in protocols
        assert "https" in protocols
        assert "wss" in protocols
        assert len(protocols) == 3
