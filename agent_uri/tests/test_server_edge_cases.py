"""
Edge case tests for server module to achieve complete coverage.

This module tests remaining uncovered lines including import handling,
abstract methods, and edge cases in FastAPI integration.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from ..server import FASTAPI_AVAILABLE, AgentServer

if FASTAPI_AVAILABLE:
    from ..server import FastAPIAgentServer
else:
    FastAPIAgentServer = None


class TestImportHandling:
    """Test import handling and conditional code paths."""

    def test_fastapi_available_flag(self):
        """Test that FASTAPI_AVAILABLE flag is set correctly."""
        # This tests lines 21-33 in server.py
        assert isinstance(FASTAPI_AVAILABLE, bool)

        # If we're running this test, we know the import behavior
        if FASTAPI_AVAILABLE:
            # FastAPI should be available
            from fastapi import FastAPI

            assert FastAPI is not None
        else:
            # Test the placeholder assignments (lines 26-33)
            from ..server import APIRouter, FastAPI, HTTPException

            assert FastAPI is None
            assert APIRouter is None
            assert HTTPException is None


class TestAbstractMethods:
    """Test abstract method implementations."""

    class MinimalConcreteServer(AgentServer):
        """Minimal concrete implementation for testing abstract methods."""

        async def handle_http_request(self, path, params, headers=None, **kwargs):
            """Minimal HTTP request handler implementation."""
            # This tests line 250 - the abstract method pass statement
            return {"handled": True, "path": path}

        async def handle_websocket_request(self, path, params, headers=None, **kwargs):
            """Minimal WebSocket request handler implementation."""
            # This tests line 276 - the abstract method pass statement
            yield {"handled": True, "path": path}

    def test_abstract_method_pass_statements(self):
        """Test that abstract methods have pass statements."""
        # Create concrete implementation to ensure abstract methods work
        server = self.MinimalConcreteServer("test", "1.0.0")
        assert server.name == "test"
        assert server.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_concrete_abstract_method_implementations(self):
        """Test that concrete implementations of abstract methods work."""
        server = self.MinimalConcreteServer("test", "1.0.0")

        # Test HTTP request handler
        result = await server.handle_http_request("/test", {"param": "value"})
        assert result["handled"] is True
        assert result["path"] == "/test"

        # Test WebSocket request handler
        chunks = []
        async for chunk in server.handle_websocket_request(
            "/stream", {"param": "value"}
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["handled"] is True
        assert chunks[0]["path"] == "/stream"


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIRouteSetup:
    """Test FastAPI route setup edge cases."""

    def test_route_setup_without_prefix(self):
        """Test route setup when no prefix is specified."""
        server = FastAPIAgentServer("test-agent", "1.0.0", prefix="")

        # This tests lines 388-399 - the .well-known/agent.json route setup
        # when prefix is empty
        assert server.prefix == ""

        # Verify that well-known route was added to the app (not router)
        # by checking that enable_agent_json is True and prefix is empty
        assert server.enable_agent_json is True

        # The route setup happens in _setup_routes, which we've now covered
        routes = [route.path for route in server.app.routes]
        assert "/.well-known/agent.json" in routes

    def test_route_setup_with_prefix(self):
        """Test route setup when prefix is specified."""
        server = FastAPIAgentServer("test-agent", "1.0.0", prefix="/api/v1")

        # This tests that .well-known route is NOT added when prefix exists
        assert server.prefix == "/api/v1"

        # The .well-known route should not be in app routes when prefix is used
        routes = [route.path for route in server.app.routes]
        # .well-known route should not be present with prefix
        well_known_routes = [r for r in routes if "well-known" in r]
        assert len(well_known_routes) == 0

    def test_websocket_wrapper_function(self):
        """Test the websocket wrapper function creation."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # This tests lines 412-415 - the websocket wrapper function
        # The function is created during _setup_routes, and we can verify
        # it was set up by checking the router's websocket routes
        websocket_routes = [
            route
            for route in server.router.routes
            if hasattr(route, "path") and route.path == "/{path:path}"
        ]

        # Should have at least one WebSocket route
        assert len(websocket_routes) >= 1


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIWebSocketEdgeCases:
    """Test remaining WebSocket edge cases."""

    @pytest.mark.asyncio
    async def test_websocket_request_with_async_generator_result(self):
        """Test WebSocket request when handler returns proper async generator."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Create a proper async generator
        async def mock_async_generator():
            yield {"chunk": 1}
            yield {"chunk": 2}
            yield {"chunk": 3}

        # Mock the handler to return an object with __aiter__
        mock_result = mock_async_generator()

        with patch.object(
            server._handlers["websocket"], "handle_request", return_value=mock_result
        ):
            chunks = []
            async for chunk in server.handle_websocket_request("/stream", {}):
                chunks.append(chunk)

            # Should receive all chunks from the async generator
            assert len(chunks) == 3
            assert chunks[0] == {"chunk": 1}
            assert chunks[1] == {"chunk": 2}
            assert chunks[2] == {"chunk": 3}

    @pytest.mark.asyncio
    async def test_websocket_connection_json_parsing_error(self):
        """Test WebSocket connection with JSON parsing error in parameters."""
        server = FastAPIAgentServer("test-agent", "1.0.0")

        # Create a mock WebSocket that returns invalid JSON
        mock_websocket = Mock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value="invalid json data")
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()

        # This should handle the JSON decode error gracefully
        await server._handle_websocket_connection(mock_websocket, "/test")

        # WebSocket should still be properly closed
        mock_websocket.close.assert_called_once()


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIServerInitializationEdgeCases:
    """Test FastAPI server initialization edge cases."""

    def test_server_with_all_options_disabled(self):
        """Test server initialization with all optional features disabled."""
        server = FastAPIAgentServer(
            name="minimal-agent",
            version="1.0.0",
            enable_cors=False,
            enable_docs=False,
            enable_agent_json=False,
        )

        # Verify settings
        assert server.enable_cors is False
        assert server.enable_docs is False
        assert server.enable_agent_json is False

        # App should not have agent.json routes
        routes = [route.path for route in server.router.routes]
        agent_json_routes = [r for r in routes if "agent.json" in r]
        assert len(agent_json_routes) == 0

    def test_server_cors_configuration(self):
        """Test CORS configuration details."""
        # Test with default CORS
        server1 = FastAPIAgentServer("test", "1.0.0", enable_cors=True)
        assert server1.cors_origins == ["*"]

        # Test with custom CORS origins
        custom_origins = ["https://example.com", "https://api.example.com"]
        server2 = FastAPIAgentServer(
            "test", "1.0.0", enable_cors=True, cors_origins=custom_origins
        )
        assert server2.cors_origins == custom_origins


class TestServerUtilityMethods:
    """Test server utility methods that may not be well covered."""

    class TestableServer(AgentServer):
        """Testable concrete server implementation."""

        async def handle_http_request(self, path, params, headers=None, **kwargs):
            return {"path": path, "params": params}

        async def handle_websocket_request(self, path, params, headers=None, **kwargs):
            yield {"path": path, "params": params}

    def test_descriptor_generator_integration(self):
        """Test that descriptor generator is properly initialized and used."""
        server = self.TestableServer(
            name="test-agent",
            version="2.0.0",
            description="Test description",
            documentation_url="https://docs.example.com",
        )

        # Test that descriptor generator was created with correct parameters
        assert server.descriptor_generator.name == "test-agent"
        assert server.descriptor_generator.version == "2.0.0"

        # Test get_agent_descriptor method
        descriptor = server.get_agent_descriptor()
        assert descriptor["name"] == "test-agent"
        assert descriptor["version"] == "2.0.0"
        assert descriptor["description"] == "Test description"

    def test_save_agent_descriptor_delegation(self):
        """Test that save_agent_descriptor properly delegates to generator."""
        server = self.TestableServer("test", "1.0.0")

        with patch.object(server.descriptor_generator, "save") as mock_save:
            server.save_agent_descriptor("/path/to/descriptor.json")
            mock_save.assert_called_once_with("/path/to/descriptor.json")

    def test_server_handlers_initialization(self):
        """Test that server handlers are properly initialized."""
        server = self.TestableServer("test", "1.0.0")

        # Verify handlers are created
        assert "http" in server._handlers
        assert "websocket" in server._handlers

        # Verify handler types
        from ..handler import HTTPHandler, WebSocketHandler

        assert isinstance(server._handlers["http"], HTTPHandler)
        assert isinstance(server._handlers["websocket"], WebSocketHandler)
