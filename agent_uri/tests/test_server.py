"""
Tests for the server module.

This module contains comprehensive tests for the agent server implementations.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ..capability import Capability, CapabilityMetadata
from ..exceptions import CapabilityNotFoundError, ConfigurationError, HandlerError
from ..server import FASTAPI_AVAILABLE, AgentServer

try:
    from ..server import FastAPIAgentServer
except ImportError:
    FastAPIAgentServer = None  # type: ignore


class TestAgentServerBase:
    """Test the abstract AgentServer base class."""

    class ConcreteAgentServer(AgentServer):
        """Concrete implementation for testing."""

        async def handle_http_request(self, path, params, headers=None, **kwargs):
            """Mock HTTP request handler."""
            return {"path": path, "params": params, "headers": headers}

        async def handle_websocket_request(self, path, params, headers=None, **kwargs):
            """Mock WebSocket request handler."""
            yield {"path": path, "params": params, "headers": headers}

    def test_agent_server_initialization(self):
        """Test AgentServer initialization with required parameters."""
        server = self.ConcreteAgentServer(
            name="test-agent", version="1.0.0", description="Test agent"
        )

        assert server.name == "test-agent"
        assert server.version == "1.0.0"
        assert server.description == "Test agent"
        assert server._capabilities == {}
        assert server._authenticator is None

    def test_agent_server_initialization_with_optional_params(self):
        """Test AgentServer initialization with all optional parameters."""
        provider = {"name": "Test Provider", "url": "https://example.com"}
        auth_schemes = ["bearer", "apikey"]
        skills = [{"name": "skill1", "description": "Test skill"}]

        server = self.ConcreteAgentServer(
            name="test-agent",
            version="1.0.0",
            description="Test agent",
            provider=provider,
            documentation_url="https://docs.example.com",
            interaction_model="request-response",
            auth_schemes=auth_schemes,
            skills=skills,
            server_url="https://agent.example.com",
        )

        assert server.name == "test-agent"
        assert server.version == "1.0.0"
        assert server.description == "Test agent"

    def test_register_capability(self):
        """Test capability registration."""
        server = self.ConcreteAgentServer("test-agent", "1.0.0")

        # Create a test capability
        metadata = CapabilityMetadata(
            name="echo",
            description="Echo capability",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
            },
        )

        async def echo_handler(message: str = "Hello") -> str:
            return f"Echo: {message}"

        capability = Capability(echo_handler, metadata)

        # Register capability
        server.register_capability("/echo", capability)

        # Verify registration
        assert "/echo" in server._capabilities
        assert server._capabilities["/echo"] == capability

    def test_register_capabilities_from_module(self):
        """Test registering capabilities from a module."""
        server = self.ConcreteAgentServer("test-agent", "1.0.0")

        # Create a mock module with capabilities
        mock_module = Mock()

        # Create test capability
        metadata = CapabilityMetadata(
            name="test_func",
            description="Test function",
            input_schema={"type": "object", "properties": {}},
        )

        async def test_func():
            return "test result"

        capability = Capability(test_func, metadata)
        test_func._capability = capability

        # Mock dir() to return our function
        mock_module.__dict__ = {"test_func": test_func, "_private": "ignore"}

        with patch("builtins.dir", return_value=["test_func", "_private"]):
            count = server.register_capabilities_from_module(mock_module)

        assert count == 1
        assert "test_func" in server._capabilities

    def test_register_capabilities_from_object(self):
        """Test registering capabilities from an object."""
        server = self.ConcreteAgentServer("test-agent", "1.0.0")

        # Create a mock object with capabilities
        obj = Mock()

        # Create a mock function that can have attributes
        def test_method():
            return "test result"

        def _private_method():
            return "private"

        # Create test capability
        metadata = CapabilityMetadata(
            name="test_method",
            description="Test method",
            input_schema={"type": "object", "properties": {}},
        )

        capability = Capability(test_method, metadata)
        test_method._capability = capability

        # Mock dir() to return our function names
        obj.__dict__ = {"test_method": test_method, "_private_method": _private_method}

        with patch("builtins.dir", return_value=["test_method", "_private_method"]):
            count = server.register_capabilities_from_object(obj)

        assert count == 1
        assert "test_method" in server._capabilities

    def test_register_authenticator(self):
        """Test authenticator registration."""
        server = self.ConcreteAgentServer("test-agent", "1.0.0")

        def auth_func(credentials):
            return credentials.get("token") == "valid"

        server.register_authenticator(auth_func)

        assert server._authenticator == auth_func

    def test_get_agent_descriptor(self):
        """Test agent descriptor generation."""
        server = self.ConcreteAgentServer("test-agent", "1.0.0", "Test description")

        descriptor = server.get_agent_descriptor()

        assert descriptor["name"] == "test-agent"
        assert descriptor["version"] == "1.0.0"
        assert descriptor["description"] == "Test description"
        assert "capabilities" in descriptor

    def test_save_agent_descriptor(self):
        """Test saving agent descriptor to file."""
        server = self.ConcreteAgentServer("test-agent", "1.0.0")

        with patch.object(server.descriptor_generator, "save") as mock_save:
            server.save_agent_descriptor("/path/to/agent.json")
            mock_save.assert_called_once_with("/path/to/agent.json")

    @pytest.mark.asyncio
    async def test_concrete_http_request_handler(self):
        """Test the concrete HTTP request handler."""
        server = self.ConcreteAgentServer("test-agent", "1.0.0")

        result = await server.handle_http_request(
            path="/test",
            params={"param": "value"},
            headers={"Content-Type": "application/json"},
        )

        assert result["path"] == "/test"
        assert result["params"] == {"param": "value"}
        assert result["headers"]["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_concrete_websocket_request_handler(self):
        """Test the concrete WebSocket request handler."""
        server = self.ConcreteAgentServer("test-agent", "1.0.0")

        chunks = []
        async for chunk in server.handle_websocket_request(
            path="/test",
            params={"param": "value"},
            headers={"Authorization": "Bearer token"},
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["path"] == "/test"
        assert chunks[0]["params"] == {"param": "value"}


class TestAbstractMethods:
    """Test that abstract methods raise NotImplementedError."""

    def test_abstract_server_cannot_be_instantiated(self):
        """Test that AgentServer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AgentServer("test", "1.0.0")


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIAgentServer:
    """Test the FastAPI agent server implementation."""

    def test_fastapi_server_initialization(self):
        """Test FastAPIAgentServer initialization."""
        server = FastAPIAgentServer(
            name="test-agent", version="1.0.0", description="Test FastAPI agent"
        )

        assert server.name == "test-agent"
        assert server.version == "1.0.0"
        assert server.description == "Test FastAPI agent"
        assert server.app is not None
        assert server.router is not None

    def test_fastapi_server_with_custom_settings(self):
        """Test FastAPIAgentServer with custom settings."""
        server = FastAPIAgentServer(
            name="test-agent",
            version="1.0.0",
            prefix="/api/v1",
            enable_cors=False,
            enable_docs=False,
            enable_agent_json=False,
        )

        assert server.prefix == "/api/v1"
        assert server.enable_cors is False
        assert server.enable_docs is False
        assert server.enable_agent_json is False

    def test_fastapi_server_with_existing_app(self):
        """Test FastAPIAgentServer with existing FastAPI app."""
        from fastapi import FastAPI

        existing_app = FastAPI()
        server = FastAPIAgentServer(
            name="test-agent", version="1.0.0", app=existing_app
        )

        assert server.app is existing_app

    @pytest.mark.asyncio
    async def test_get_agent_json_endpoint(self):
        """Test the agent.json endpoint."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        response = await server._get_agent_json()

        assert response.status_code == 200
        assert response.media_type == "application/json"
        # The content should be the agent descriptor
        content = json.loads(response.body)
        assert content["name"] == "test-agent"

    @pytest.mark.asyncio
    async def test_handle_http_request_get(self):
        """Test HTTP GET request handling."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Mock the HTTP handler
        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"result": "success"}

            result = await server.handle_http_request(
                path="/test",
                params={"param": "value"},
                headers={"Content-Type": "application/json"},
            )

            assert result == {"result": "success"}
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_websocket_request(self):
        """Test WebSocket request handling."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Mock the WebSocket handler
        async def mock_chunks():
            yield {"chunk": 1}
            yield {"chunk": 2}

        with patch.object(
            server._handlers["websocket"], "handle_request", return_value=mock_chunks()
        ):
            chunks = []
            async for chunk in server.handle_websocket_request(
                path="/test", params={"param": "value"}
            ):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == {"chunk": 1}
            assert chunks[1] == {"chunk": 2}

    @pytest.mark.asyncio
    async def test_http_request_error_handling(self):
        """Test HTTP request error handling."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Test CapabilityNotFoundError
        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = CapabilityNotFoundError("Capability not found")

            with pytest.raises(CapabilityNotFoundError):
                await server.handle_http_request("/nonexistent", {})

    @pytest.mark.asyncio
    async def test_websocket_request_error_handling(self):
        """Test WebSocket request error handling."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Test error in WebSocket handler
        async def mock_error_handler(*args, **kwargs):
            raise HandlerError("Handler error")
            yield  # This makes it an async generator

        with patch.object(
            server._handlers["websocket"],
            "handle_request",
            return_value=mock_error_handler(),
        ):
            with pytest.raises(HandlerError):
                chunks = []
                async for chunk in server.handle_websocket_request("/test", {}):
                    chunks.append(chunk)


@pytest.mark.skipif(FASTAPI_AVAILABLE, reason="Testing when FastAPI is not available")
class TestFastAPIUnavailable:
    """Test behavior when FastAPI is not available."""

    def test_fastapi_server_import_error(self):
        """Test FastAPIAgentServer raises ImportError when FastAPI is not available."""
        with pytest.raises(ImportError, match="FastAPI is not installed"):
            FastAPIAgentServer("test", "1.0.0")


class TestServerIntegration:
    """Test server integration scenarios."""

    class MockCapabilityHandler:
        """Mock capability handler for testing."""

        def __init__(self):
            self.call_count = 0

        async def __call__(self, message: str = "Hello") -> str:
            self.call_count += 1
            return f"Mock response: {message}"

    def test_end_to_end_capability_registration_and_execution(self):
        """Test end-to-end capability registration and execution."""
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")

        # Create and register a capability
        handler = self.MockCapabilityHandler()
        metadata = CapabilityMetadata(
            name="mock",
            description="Mock capability",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
            },
        )

        capability = Capability(handler, metadata)
        server.register_capability("/mock", capability)

        # Verify capability is registered
        assert "/mock" in server._capabilities
        assert server._capabilities["/mock"].func == handler

        # Verify descriptor includes the capability
        descriptor = server.get_agent_descriptor()
        assert "capabilities" in descriptor

    def test_multiple_capability_registration(self):
        """Test registering multiple capabilities."""
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")

        # Register multiple capabilities
        for i in range(3):
            metadata = CapabilityMetadata(
                name=f"capability_{i}",
                description=f"Test capability {i}",
                input_schema={"type": "object", "properties": {}},
            )

            async def handler(index=i):
                return f"result_{index}"

            capability = Capability(handler, metadata)
            server.register_capability(f"/capability_{i}", capability)

        # Verify all capabilities are registered
        assert len(server._capabilities) == 3
        for i in range(3):
            assert f"/capability_{i}" in server._capabilities

    def test_authenticator_registration_and_propagation(self):
        """Test that authenticator is propagated to all handlers."""
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")

        def auth_func(credentials):
            return True

        # Mock handler registration
        with patch.object(
            server._handlers["http"], "register_authenticator"
        ) as mock_http_auth:
            with patch.object(
                server._handlers["websocket"], "register_authenticator"
            ) as mock_ws_auth:
                server.register_authenticator(auth_func)

                # Verify authenticator was registered with all handlers
                mock_http_auth.assert_called_once_with(auth_func)
                mock_ws_auth.assert_called_once_with(auth_func)

    def test_capability_registration_with_handlers(self):
        """Test that capability registration propagates to handlers."""
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")

        metadata = CapabilityMetadata(
            name="test",
            description="Test capability",
            input_schema={"type": "object", "properties": {}},
        )

        capability = Capability(lambda: "test", metadata)

        # Mock handler registration
        with patch.object(
            server._handlers["http"], "register_capability"
        ) as mock_http_cap:
            with patch.object(
                server._handlers["websocket"], "register_capability"
            ) as mock_ws_cap:
                server.register_capability("/test", capability)

                # Verify capability was registered with all handlers
                mock_http_cap.assert_called_once_with("/test", capability)
                mock_ws_cap.assert_called_once_with("/test", capability)


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_missing_handler_configuration_error(self):
        """Test ConfigurationError when handler is missing."""

        class BrokenServer(AgentServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Remove handlers to simulate missing configuration
                self._handlers = {}

            async def handle_http_request(self, *args, **kwargs):
                # This should raise ConfigurationError
                handler = self._handlers.get("http")
                if not handler:
                    raise ConfigurationError("No HTTP handler registered")
                return await handler.handle_request(*args, **kwargs)

            async def handle_websocket_request(self, *args, **kwargs):
                handler = self._handlers.get("websocket")
                if not handler:
                    raise ConfigurationError("No WebSocket handler registered")
                async for chunk in handler.handle_request(*args, **kwargs):
                    yield chunk

        server = BrokenServer("test-agent", "1.0.0")

        # Test HTTP handler error
        with pytest.raises(ConfigurationError, match="No HTTP handler registered"):
            asyncio.run(server.handle_http_request("/test", {}))

    def test_invalid_capability_module_registration(self):
        """Test handling of invalid module during capability registration."""
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")

        # Create a module with no capabilities
        mock_module = Mock()
        mock_module.__dict__ = {"regular_func": lambda: "test", "_private": "ignore"}

        with patch("builtins.dir", return_value=["regular_func", "_private"]):
            count = server.register_capabilities_from_module(mock_module)

        # Should register 0 capabilities since regular_func has no _capability attribute
        assert count == 0
        assert len(server._capabilities) == 0
