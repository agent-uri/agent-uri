"""
Tests for the agent server module.

Aligned with draft-narvaneni-agent-uri-03: uses Skill terminology.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from ..exceptions import (
    ConfigurationError,
    HandlerError,
    SkillNotFoundError,
)
from ..server import FASTAPI_AVAILABLE, AgentServer
from ..skill import Skill, SkillMetadata

try:
    from ..server import FastAPIAgentServer
except ImportError:
    FastAPIAgentServer = None  # type: ignore


def _make_skill(id_: str = "echo") -> Skill:
    async def handler(message: str = "hi") -> str:
        return f"echo: {message}"

    metadata = SkillMetadata(
        id=id_,
        name=id_,
        description=f"Skill {id_}",
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
        },
    )
    return Skill(handler, metadata=metadata)


class TestAgentServerBase:
    class ConcreteAgentServer(AgentServer):
        async def handle_http_request(self, path, params, headers=None, **kwargs):
            return {"path": path, "params": params, "headers": headers}

        async def handle_websocket_request(self, path, params, headers=None, **kwargs):
            yield {"path": path, "params": params, "headers": headers}

    def test_initialization(self):
        server = self.ConcreteAgentServer(
            name="test-agent", version="1.0.0", description="Test agent"
        )
        assert server.name == "test-agent"
        assert server.version == "1.0.0"
        assert server.description == "Test agent"
        assert server._skills == {}
        assert server._authenticator is None

    def test_initialization_with_optional_params(self):
        server = self.ConcreteAgentServer(
            name="test-agent",
            version="1.0.0",
            description="Test agent",
            provider={"organization": "Test Inc"},
            documentation_url="https://docs.example.com",
            interaction_model=["agent2agent"],
            auth={"schemes": ["bearer"]},
            server_url="https://agent.example.com",
            conformance_level=2,
        )
        assert server.descriptor_generator.conformance_level == 2

    def test_register_skill(self):
        server = self.ConcreteAgentServer("test-agent", "1.0.0")
        s = _make_skill("echo")
        server.register_skill("/echo", s)
        assert "/echo" in server._skills
        assert server._skills["/echo"] is s

    def test_register_skills_from_module(self):
        from types import SimpleNamespace

        s = _make_skill("test_func")

        def test_func():
            return "test result"

        test_func._skill = s
        module = SimpleNamespace(test_func=test_func, _private="ignore")

        server = self.ConcreteAgentServer("test-agent", "1.0.0")
        count = server.register_skills_from_module(module)
        assert count == 1
        assert "test_func" in server._skills

    def test_register_skills_from_object(self):
        class Obj:
            pass

        s = _make_skill("test_method")

        def test_method():
            return "ok"

        test_method._skill = s

        obj = Obj()
        obj.test_method = test_method

        server = self.ConcreteAgentServer("test-agent", "1.0.0")
        count = server.register_skills_from_object(obj)
        assert count == 1
        assert "test_method" in server._skills

    def test_register_authenticator(self):
        server = self.ConcreteAgentServer("test-agent", "1.0.0")

        def auth_func(credentials):
            return credentials.get("token") == "valid"

        server.register_authenticator(auth_func)
        assert server._authenticator == auth_func

    def test_get_agent_descriptor(self):
        server = self.ConcreteAgentServer("test-agent", "1.0.0", "Test description")
        descriptor = server.get_agent_descriptor()
        assert descriptor["name"] == "test-agent"
        assert descriptor["version"] == "1.0.0"
        assert descriptor["description"] == "Test description"
        assert "skills" in descriptor

    def test_save_agent_descriptor(self):
        server = self.ConcreteAgentServer("test-agent", "1.0.0")
        with patch.object(server.descriptor_generator, "save") as mock_save:
            server.save_agent_descriptor("/path/to/agent.json")
            mock_save.assert_called_once_with("/path/to/agent.json")

    @pytest.mark.asyncio
    async def test_concrete_http_request_handler(self):
        server = self.ConcreteAgentServer("test-agent", "1.0.0")
        result = await server.handle_http_request(
            path="/test",
            params={"param": "value"},
            headers={"Content-Type": "application/json"},
        )
        assert result["path"] == "/test"
        assert result["params"] == {"param": "value"}

    @pytest.mark.asyncio
    async def test_concrete_websocket_request_handler(self):
        server = self.ConcreteAgentServer("test-agent", "1.0.0")
        chunks = []
        async for chunk in server.handle_websocket_request(
            path="/test", params={"param": "value"}
        ):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0]["path"] == "/test"


class TestAbstractMethods:
    def test_abstract_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            AgentServer("test", "1.0.0")


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFastAPIAgentServer:
    def test_initialization(self):
        server = FastAPIAgentServer(
            name="test-agent", version="1.0.0", description="Test"
        )
        assert server.name == "test-agent"
        assert server.app is not None
        assert server.router is not None

    def test_custom_settings(self):
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

    def test_with_existing_app(self):
        from fastapi import FastAPI

        existing = FastAPI()
        server = FastAPIAgentServer(name="t", version="1.0.0", app=existing)
        assert server.app is existing

    @pytest.mark.asyncio
    async def test_get_agent_json_endpoint(self):
        server = FastAPIAgentServer("test-agent", "1.0.0")
        # Descriptor requires >= 1 skill.
        server.register_skill("/echo", _make_skill("echo"))
        response = await server._get_agent_json()
        assert response.status_code == 200
        content = json.loads(response.body)
        assert content["name"] == "test-agent"
        assert content["skills"][0]["id"] == "echo"

    @pytest.mark.asyncio
    async def test_handle_http_request(self):
        server = FastAPIAgentServer("test-agent", "1.0.0")
        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = {"result": "success"}
            result = await server.handle_http_request(
                path="/test", params={"p": "v"}, headers={}
            )
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_handle_websocket_request(self):
        server = FastAPIAgentServer("test-agent", "1.0.0")

        async def mock_chunks():
            yield {"chunk": 1}
            yield {"chunk": 2}

        with patch.object(
            server._handlers["websocket"],
            "handle_request",
            return_value=mock_chunks(),
        ):
            chunks = []
            async for chunk in server.handle_websocket_request("/t", {}):
                chunks.append(chunk)
            assert chunks == [{"chunk": 1}, {"chunk": 2}]

    @pytest.mark.asyncio
    async def test_http_skill_not_found_propagates(self):
        server = FastAPIAgentServer("test-agent", "1.0.0")
        with patch.object(
            server._handlers["http"], "handle_request", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.side_effect = SkillNotFoundError("unknown")
            with pytest.raises(SkillNotFoundError):
                await server.handle_http_request("/nonexistent", {})


@pytest.mark.skipif(FASTAPI_AVAILABLE, reason="FastAPI unavailable scenario")
class TestFastAPIUnavailable:
    def test_import_error(self):
        with pytest.raises(ImportError, match="FastAPI is not installed"):
            FastAPIAgentServer("test", "1.0.0")


class TestServerIntegration:
    def test_end_to_end_registration(self):
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")
        s = _make_skill("mock")
        server.register_skill("/mock", s)
        assert "/mock" in server._skills
        descriptor = server.get_agent_descriptor()
        assert "skills" in descriptor
        assert any(sk["id"] == "mock" for sk in descriptor["skills"])

    def test_multiple_skill_registration(self):
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")
        for i in range(3):
            server.register_skill(f"/skill_{i}", _make_skill(f"skill_{i}"))
        assert len(server._skills) == 3

    def test_authenticator_propagation(self):
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")

        def auth_func(c):
            return True

        with (
            patch.object(server._handlers["http"], "register_authenticator") as http_m,
            patch.object(
                server._handlers["websocket"], "register_authenticator"
            ) as ws_m,
        ):
            server.register_authenticator(auth_func)
            http_m.assert_called_once_with(auth_func)
            ws_m.assert_called_once_with(auth_func)

    def test_skill_registration_propagates_to_handlers(self):
        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")
        s = _make_skill("test")
        with (
            patch.object(server._handlers["http"], "register_skill") as http_m,
            patch.object(server._handlers["websocket"], "register_skill") as ws_m,
        ):
            server.register_skill("/test", s)
            http_m.assert_called_once_with("/test", s)
            ws_m.assert_called_once_with("/test", s)


class TestErrorHandling:
    def test_missing_handler_configuration_error(self):
        class BrokenServer(AgentServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._handlers = {}

            async def handle_http_request(self, *args, **kwargs):
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
        with pytest.raises(ConfigurationError, match="No HTTP handler"):
            asyncio.run(server.handle_http_request("/test", {}))

    def test_invalid_module_registration(self):
        from types import SimpleNamespace

        server = TestAgentServerBase.ConcreteAgentServer("test-agent", "1.0.0")
        module = SimpleNamespace(regular_func=lambda: "t", _private="i")
        count = server.register_skills_from_module(module)
        assert count == 0
