"""
Detailed tests for FastAPI server module functionality.

Aligned with draft-narvaneni-agent-uri-03. Error responses use
RFC 9457 problem-details JSON with an ``errorCode`` field.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ..exceptions import (
    AuthenticationError,
    ConfigurationError,
    HandlerError,
    InvalidInputError,
    SkillNotFoundError,
)
from ..server import FASTAPI_AVAILABLE

if FASTAPI_AVAILABLE:
    from fastapi import Request, WebSocket
    from fastapi.responses import JSONResponse

    from ..server import FastAPIAgentServer
else:
    FastAPIAgentServer = None
    Request = None
    WebSocket = None
    JSONResponse = None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIRequestHandling:
    @pytest.fixture
    def server(self):
        return FastAPIAgentServer(
            name="test-agent",
            version="1.0.0",
            description="Test server for detailed testing",
        )

    @pytest.mark.asyncio
    async def test_handle_http_request_get_with_query_params(self, server):
        req = Mock(spec=Request)
        req.method = "GET"
        req.query_params = {"param1": "value1", "param2": "value2"}
        req.headers = {"Content-Type": "application/json"}
        req.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"result": "success"}
            response = await server._handle_http_request(req, "/test")

            assert isinstance(response, JSONResponse)
            assert response.status_code == 200
            assert json.loads(response.body)["result"] == "success"

            call_kwargs = mock_handler.call_args.kwargs
            assert call_kwargs["path"] == "/test"
            assert call_kwargs["params"]["param1"] == "value1"

    @pytest.mark.asyncio
    async def test_handle_http_request_post_with_json_body(self, server):
        req = Mock(spec=Request)
        req.method = "POST"
        req.query_params = {}
        req.headers = {"Content-Type": "application/json"}
        req.body = AsyncMock(
            return_value=json.dumps(
                {"message": "test message", "data": {"nested": "value"}}
            ).encode()
        )

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"processed": True}
            await server._handle_http_request(req, "/process")

            params = mock_handler.call_args.kwargs["params"]
            assert params["message"] == "test message"
            assert params["data"]["nested"] == "value"

    @pytest.mark.asyncio
    async def test_handle_http_request_post_with_raw_body(self, server):
        req = Mock(spec=Request)
        req.method = "POST"
        req.query_params = {}
        req.headers = {"Content-Type": "text/plain"}
        req.body = AsyncMock(return_value=b"raw text data")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"received_raw": True}
            await server._handle_http_request(req, "/raw")
            params = mock_handler.call_args.kwargs["params"]
            assert params["body"] == "raw text data"

    @pytest.mark.asyncio
    async def test_handle_http_request_with_baggage_session(self, server):
        """Session id comes from W3C Baggage header, not custom header."""
        req = Mock(spec=Request)
        req.method = "GET"
        req.query_params = {}
        req.headers = {
            "Content-Type": "application/json",
            "baggage": "session.id=abc-123",
        }
        req.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {}
            await server._handle_http_request(req, "/session")
            meta = mock_handler.call_args.kwargs["session_metadata"]
            assert meta["session_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_handle_http_request_legacy_session_header(self, server):
        """Legacy X-Session-ID still read during transition."""
        req = Mock(spec=Request)
        req.method = "GET"
        req.query_params = {}
        req.headers = {"X-Session-ID": "session-12345"}
        req.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {}
            await server._handle_http_request(req, "/session")
            meta = mock_handler.call_args.kwargs["session_metadata"]
            assert meta["session_id"] == "session-12345"

    @pytest.mark.asyncio
    async def test_handle_http_request_skill_not_found_returns_problem(self, server):
        req = Mock(spec=Request)
        req.method = "GET"
        req.query_params = {}
        req.headers = {}
        req.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = SkillNotFoundError("echo")
            response = await server._handle_http_request(req, "/nonexistent")
            assert response.status_code == 404
            body = json.loads(response.body)
            assert body["status"] == 404
            assert body["errorCode"] == "4041"

    @pytest.mark.asyncio
    async def test_handle_http_request_authentication_error(self, server):
        req = Mock(spec=Request)
        req.method = "GET"
        req.query_params = {}
        req.headers = {}
        req.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = AuthenticationError("Invalid token")
            response = await server._handle_http_request(req, "/secure")
            assert response.status_code == 401
            body = json.loads(response.body)
            assert body["errorCode"] == "4011"

    @pytest.mark.asyncio
    async def test_handle_http_request_invalid_input_error(self, server):
        req = Mock(spec=Request)
        req.method = "GET"
        req.query_params = {}
        req.headers = {}
        req.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = InvalidInputError("bad input")
            response = await server._handle_http_request(req, "/validate")
            assert response.status_code == 400
            assert json.loads(response.body)["errorCode"] == "4006"

    @pytest.mark.asyncio
    async def test_handle_http_request_handler_error(self, server):
        req = Mock(spec=Request)
        req.method = "GET"
        req.query_params = {}
        req.headers = {}
        req.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = HandlerError("boom")
            response = await server._handle_http_request(req, "/err")
            assert response.status_code == 500
            assert json.loads(response.body)["errorCode"] == "5002"

    @pytest.mark.asyncio
    async def test_handle_http_request_unexpected_error(self, server):
        req = Mock(spec=Request)
        req.method = "GET"
        req.query_params = {}
        req.headers = {}
        req.body = AsyncMock(return_value=b"")

        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = ValueError("unexpected")
            response = await server._handle_http_request(req, "/x")
            assert response.status_code == 500
            body = json.loads(response.body)
            assert body["title"] == "Internal Server Error"


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIWebSocketHandling:
    @pytest.fixture
    def server(self):
        return FastAPIAgentServer(
            name="websocket-agent",
            version="1.0.0",
            description="WS test server",
        )

    @pytest.mark.asyncio
    async def test_basic_connection(self, server):
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(
            return_value='{"message": "test", "session_id": "ws-123"}'
        )
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        async def stream():
            yield {"chunk": 1}
            yield {"chunk": 2}

        with patch.object(server, "handle_websocket_request", return_value=stream()):
            await server._handle_websocket_connection(ws, "/stream")
            ws.accept.assert_called_once()
            assert ws.send_text.call_count == 2
            sent = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
            assert sent == [{"chunk": 1}, {"chunk": 2}]

    @pytest.mark.asyncio
    async def test_session_metadata_from_params(self, server):
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(
            return_value='{"param": "value", "session_id": "ws-456"}'
        )
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        async def stream():
            yield {"ok": True}

        with patch.object(
            server, "handle_websocket_request", return_value=stream()
        ) as mock_handler:
            await server._handle_websocket_connection(ws, "/t")
            meta = mock_handler.call_args.kwargs["session_metadata"]
            assert meta["session_id"] == "ws-456"

    @pytest.mark.asyncio
    async def test_different_data_types(self, server):
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(return_value='{"test": "data"}')
        ws.send_text = AsyncMock()
        ws.send_bytes = AsyncMock()
        ws.close = AsyncMock()

        async def stream():
            yield {"dict": "data"}
            yield "string data"
            yield b"byte data"
            yield 42

        with patch.object(server, "handle_websocket_request", return_value=stream()):
            await server._handle_websocket_connection(ws, "/types")
            assert ws.send_text.call_count == 3
            assert ws.send_bytes.call_count == 1
            texts = [c.args[0] for c in ws.send_text.call_args_list]
            assert json.loads(texts[0]) == {"dict": "data"}
            assert texts[1] == "string data"
            assert texts[2] == "42"
            assert ws.send_bytes.call_args_list[0].args[0] == b"byte data"

    @pytest.mark.asyncio
    async def test_skill_not_found(self, server):
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(return_value='{"test": "data"}')
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=SkillNotFoundError("missing"),
        ):
            await server._handle_websocket_connection(ws, "/missing")
            payload = json.loads(ws.send_text.call_args.args[0])
            assert payload["error"] == "SkillNotFound"
            assert payload["errorCode"] == "4041"

    @pytest.mark.asyncio
    async def test_authentication_error(self, server):
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(return_value='{"test": "data"}')
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=AuthenticationError("bad token"),
        ):
            await server._handle_websocket_connection(ws, "/secure")
            payload = json.loads(ws.send_text.call_args.args[0])
            assert payload["error"] == "AuthenticationError"

    @pytest.mark.asyncio
    async def test_invalid_input_error(self, server):
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(return_value='{"test": "data"}')
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=InvalidInputError("bad"),
        ):
            await server._handle_websocket_connection(ws, "/validate")
            payload = json.loads(ws.send_text.call_args.args[0])
            assert payload["error"] == "InvalidInput"

    @pytest.mark.asyncio
    async def test_handler_error(self, server):
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(return_value='{"test": "data"}')
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        with patch.object(
            server,
            "handle_websocket_request",
            side_effect=HandlerError("failed"),
        ):
            await server._handle_websocket_connection(ws, "/err")
            payload = json.loads(ws.send_text.call_args.args[0])
            assert payload["error"] == "HandlerError"

    @pytest.mark.asyncio
    async def test_cleanup_closes_ws(self, server):
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(return_value='{"test": "data"}')
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        async def stream():
            yield {"success": True}

        with patch.object(server, "handle_websocket_request", return_value=stream()):
            await server._handle_websocket_connection(ws, "/cleanup")
            ws.close.assert_called_once()


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIConfigurationEdgeCases:
    @pytest.mark.asyncio
    async def test_no_http_handler(self):
        server = FastAPIAgentServer("test-agent", "1.0.0")
        del server._handlers["http"]
        with pytest.raises(ConfigurationError, match="No HTTP handler"):
            await server.handle_http_request("/test", {})

    @pytest.mark.asyncio
    async def test_no_websocket_handler(self):
        server = FastAPIAgentServer("test-agent", "1.0.0")
        del server._handlers["websocket"]
        with pytest.raises(ConfigurationError, match="No WebSocket handler"):
            async for _ in server.handle_websocket_request("/test", {}):
                pass

    @pytest.mark.asyncio
    async def test_http_handler_returns_non_coroutine(self):
        server = FastAPIAgentServer("test-agent", "1.0.0")
        with patch.object(
            server._handlers["http"], "handle_request", return_value="not_a_coroutine"
        ):
            with pytest.raises(
                ConfigurationError, match="HTTP handler returned unexpected"
            ):
                await server.handle_http_request("/test", {})

    @pytest.mark.asyncio
    async def test_websocket_non_async_iterable_single_response(self):
        server = FastAPIAgentServer("test-agent", "1.0.0")

        async def mock_single_result():
            return {"single": "response"}

        with patch.object(
            server._handlers["websocket"],
            "handle_request",
            return_value=mock_single_result(),
        ):
            chunks = []
            async for chunk in server.handle_websocket_request("/test", {}):
                chunks.append(chunk)
            assert chunks == [{"single": "response"}]


@pytest.mark.skipif(FASTAPI_AVAILABLE, reason="Testing when FastAPI is not available")
class TestFastAPIImportHandling:
    def test_placeholder_raises(self):
        from ..server import FastAPIAgentServer as Placeholder

        with pytest.raises(ImportError, match="FastAPI is not installed"):
            Placeholder("test", "1.0.0")

    def test_placeholder_methods_present(self):
        from ..server import FastAPIAgentServer as Placeholder

        assert hasattr(Placeholder, "handle_http_request")
        assert hasattr(Placeholder, "handle_websocket_request")
