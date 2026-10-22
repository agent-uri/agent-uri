"""
Tests for HTTPHandler and WebSocketHandler.

Aligned with draft-narvaneni-agent-uri-03.
"""

import pytest

from ..exceptions import (
    AuthenticationError,
    HandlerError,
    InvalidInputError,
    SkillNotFoundError,
)
from ..handler import BaseHandler, HTTPHandler, WebSocketHandler
from ..skill import Skill, SkillMetadata


def _mk_skill(
    id_: str = "echo", *, streaming: bool = False, auth_required: bool = False
) -> Skill:
    async def handler(**kwargs):
        return {"id": id_, "kwargs": list(kwargs.keys())}

    metadata = SkillMetadata(
        id=id_,
        name=id_,
        description=f"Skill {id_}",
        streaming=streaming,
        auth_required=auth_required,
    )
    return Skill(handler, metadata=metadata)


def _mk_streaming_skill(id_: str = "stream") -> Skill:
    async def handler(**kwargs):
        async def gen():
            for i in range(3):
                yield {"chunk": i}

        return gen()

    metadata = SkillMetadata(
        id=id_,
        name=id_,
        description=f"Stream {id_}",
        streaming=True,
        streaming_format="ndjson",
    )
    return Skill(handler, metadata=metadata)


def _mk_raising_skill(exc: Exception) -> Skill:
    async def handler(**kwargs):
        raise exc

    metadata = SkillMetadata(id="bad", name="bad", description="bad")
    return Skill(handler, metadata=metadata)


# --------------------------------------------------------------------------
# BaseHandler lookup + authenticate
# --------------------------------------------------------------------------


class TestBaseHandler:
    def test_register_and_get_skill(self):
        h = HTTPHandler()
        s = _mk_skill("echo")
        h.register_skill("echo", s)
        assert h.get_skill("echo") is s
        # Leading/trailing slashes normalised.
        assert h.get_skill("/echo/") is s

    def test_prefix_match_falls_back_to_parent(self):
        h = HTTPHandler()
        s = _mk_skill("parent")
        h.register_skill("a/b", s)
        assert h.get_skill("a/b/c/d") is s

    def test_skill_not_found_raises(self):
        h = HTTPHandler()
        with pytest.raises(SkillNotFoundError):
            h.get_skill("nope")

    @pytest.mark.asyncio
    async def test_authenticate_defaults_to_true(self):
        h = HTTPHandler()
        assert await h.authenticate({}) is True

    @pytest.mark.asyncio
    async def test_authenticate_calls_sync_authenticator(self):
        h = HTTPHandler()

        def auth(data):
            return data.get("token") == "valid"

        h.register_authenticator(auth)
        assert await h.authenticate({"token": "valid"}) is True
        assert await h.authenticate({"token": "bad"}) is False

    @pytest.mark.asyncio
    async def test_authenticate_calls_async_authenticator(self):
        h = HTTPHandler()

        async def auth(data):
            return {"user": "alice"}

        h.register_authenticator(auth)
        result = await h.authenticate({})
        assert result == {"user": "alice"}

    @pytest.mark.asyncio
    async def test_authenticate_wraps_exceptions(self):
        h = HTTPHandler()

        def auth(data):
            raise RuntimeError("boom")

        h.register_authenticator(auth)
        with pytest.raises(AuthenticationError):
            await h.authenticate({})

    def test_base_handler_is_abstract(self):
        # Can't instantiate BaseHandler directly because handle_request
        # is abstract.
        with pytest.raises(TypeError):
            BaseHandler()  # type: ignore[abstract]


# --------------------------------------------------------------------------
# HTTPHandler
# --------------------------------------------------------------------------


class TestHTTPHandler:
    @pytest.mark.asyncio
    async def test_handle_request_invokes_skill(self):
        h = HTTPHandler()
        h.register_skill("echo", _mk_skill("echo"))
        result = await h.handle_request("echo", {"a": 1})
        assert result["id"] == "echo"

    @pytest.mark.asyncio
    async def test_handle_request_skill_not_found(self):
        h = HTTPHandler()
        with pytest.raises(SkillNotFoundError):
            await h.handle_request("missing", {})

    @pytest.mark.asyncio
    async def test_handle_request_auth_required_passes(self):
        h = HTTPHandler()
        h.register_skill("secure", _mk_skill("secure", auth_required=True))
        h.register_authenticator(lambda d: {"user": "alice"})
        result = await h.handle_request("secure", {}, auth={"token": "t"})
        assert result["id"] == "secure"
        # auth_metadata is injected as a kwarg via handler forwarding.
        assert "auth_metadata" in result["kwargs"]

    @pytest.mark.asyncio
    async def test_handle_request_auth_required_fails(self):
        h = HTTPHandler()
        h.register_skill("secure", _mk_skill("secure", auth_required=True))
        h.register_authenticator(lambda d: False)
        with pytest.raises(AuthenticationError):
            await h.handle_request("secure", {})

    @pytest.mark.asyncio
    async def test_handle_request_invalid_input_propagates(self):
        h = HTTPHandler()
        h.register_skill("bad", _mk_raising_skill(InvalidInputError("bad")))
        with pytest.raises(InvalidInputError):
            await h.handle_request("bad", {})

    @pytest.mark.asyncio
    async def test_handle_request_wraps_other_errors(self):
        async def raises(**kwargs):
            raise RuntimeError("boom")

        # Wrap directly — don't use skill.invoke's SkillError.
        class RawSkill:
            def __init__(self):
                self.metadata = SkillMetadata(id="r", name="r", description="r")

            async def invoke(self, **kwargs):
                raise RuntimeError("boom")

        h = HTTPHandler()
        h._skills["r"] = RawSkill()  # type: ignore[assignment]
        with pytest.raises(HandlerError):
            await h.handle_request("r", {})

    @pytest.mark.asyncio
    async def test_handle_request_forwards_session_metadata(self):
        h = HTTPHandler()
        h.register_skill("s", _mk_skill("s"))
        result = await h.handle_request("s", {}, session_metadata={"session_id": "abc"})
        assert result["id"] == "s"


# --------------------------------------------------------------------------
# WebSocketHandler
# --------------------------------------------------------------------------


class TestWebSocketHandler:
    @pytest.mark.asyncio
    async def test_non_streaming_skill_yields_single_result(self):
        h = WebSocketHandler()
        h.register_skill("echo", _mk_skill("echo"))
        chunks = [c async for c in h.handle_request("echo", {})]
        assert len(chunks) == 1
        assert chunks[0]["id"] == "echo"

    @pytest.mark.asyncio
    async def test_streaming_skill_yields_chunks(self):
        h = WebSocketHandler()
        h.register_skill("stream", _mk_streaming_skill("stream"))
        chunks = [c async for c in h.handle_request("stream", {})]
        assert chunks == [{"chunk": 0}, {"chunk": 1}, {"chunk": 2}]

    @pytest.mark.asyncio
    async def test_streaming_auth_required_fails(self):
        h = WebSocketHandler()
        s = _mk_streaming_skill("stream")
        s.metadata.auth_required = True
        h.register_skill("stream", s)
        h.register_authenticator(lambda d: False)

        async def collect():
            [c async for c in h.handle_request("stream", {})]

        with pytest.raises(AuthenticationError):
            await collect()

    @pytest.mark.asyncio
    async def test_streaming_auth_required_passes(self):
        h = WebSocketHandler()
        s = _mk_streaming_skill("stream")
        s.metadata.auth_required = True
        h.register_skill("stream", s)
        h.register_authenticator(lambda d: {"user": "alice"})
        chunks = [c async for c in h.handle_request("stream", {})]
        assert len(chunks) == 3

    @pytest.mark.asyncio
    async def test_skill_not_found(self):
        h = WebSocketHandler()

        async def collect():
            [c async for c in h.handle_request("nope", {})]

        with pytest.raises(SkillNotFoundError):
            await collect()

    @pytest.mark.asyncio
    async def test_iterable_result_yields_each(self):
        """A streaming skill returning a plain iterable is yielded per item."""

        class IterSkill:
            def __init__(self):
                self.metadata = SkillMetadata(
                    id="i", name="i", description="i", streaming=True
                )

            async def invoke(self, **kwargs):
                return [{"a": 1}, {"a": 2}]

        h = WebSocketHandler()
        h._skills["i"] = IterSkill()  # type: ignore[assignment]
        chunks = [c async for c in h.handle_request("i", {})]
        assert chunks == [{"a": 1}, {"a": 2}]

    @pytest.mark.asyncio
    async def test_wraps_unexpected_error(self):
        class RawSkill:
            def __init__(self):
                self.metadata = SkillMetadata(
                    id="r", name="r", description="r", streaming=True
                )

            async def invoke(self, **kwargs):
                raise RuntimeError("boom")

        h = WebSocketHandler()
        h._skills["r"] = RawSkill()  # type: ignore[assignment]

        async def collect():
            [c async for c in h.handle_request("r", {})]

        with pytest.raises(HandlerError):
            await collect()
