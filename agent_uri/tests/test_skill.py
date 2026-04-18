"""
Tests for the Skill runtime and the ``@skill`` decorator.

Aligned with draft-narvaneni-agent-uri-03.
"""

import pytest

from ..exceptions import InvalidInputError
from ..skill import Skill, SkillMetadata, skill

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


async def async_echo(text: str):
    return {"text": text}


def sync_echo(text: str):
    return {"text": text}


@pytest.fixture
def simple_skill() -> Skill:
    return Skill(
        func=async_echo,
        id="echo",
        name="echo",
        description="Echo the input text",
        version="1.0.0",
    )


@pytest.fixture
def schema_skill() -> Skill:
    return Skill(
        func=async_echo,
        id="schema-echo",
        name="schema-echo",
        description="Echo with schema",
        version="1.0.0",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )


@pytest.fixture
def stateful_skill() -> Skill:
    async def stateful_echo(text: str, session_id=None, context=None):
        return {"text": text, "context": {"last": text}}

    return Skill(
        func=stateful_echo,
        id="stateful",
        name="stateful",
        description="Stateful echo",
        memory_enabled=True,
    )


# --------------------------------------------------------------------------
# Skill
# --------------------------------------------------------------------------


class TestSkill:
    def test_init(self, simple_skill: Skill) -> None:
        assert simple_skill.func is async_echo
        assert simple_skill.metadata.id == "echo"
        assert simple_skill.metadata.name == "echo"
        assert simple_skill.metadata.description == "Echo the input text"
        assert simple_skill.metadata.version == "1.0.0"
        assert simple_skill.is_async is True
        assert simple_skill.input_model is None
        assert simple_skill.sessions is None

    def test_sync_func(self) -> None:
        s = Skill(func=sync_echo, id="e", name="e", description="e")
        assert s.is_async is False

    def test_metadata_to_dict(self, simple_skill: Skill) -> None:
        d = simple_skill.metadata.to_dict()
        assert d["id"] == "echo"
        assert d["name"] == "echo"
        assert d["description"] == "Echo the input text"
        assert d["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_invoke(self, simple_skill: Skill) -> None:
        assert await simple_skill.invoke({"text": "Hi"}) == {"text": "Hi"}

    @pytest.mark.asyncio
    async def test_invoke_with_validation(self, schema_skill: Skill) -> None:
        assert await schema_skill.invoke({"text": "Hi"}) == {"text": "Hi"}
        with pytest.raises(InvalidInputError):
            await schema_skill.invoke({"not_text": "Hi"})

    @pytest.mark.asyncio
    async def test_stateful_skill(self, stateful_skill: Skill) -> None:
        assert stateful_skill.metadata.memory_enabled is True
        assert isinstance(stateful_skill.sessions, dict)
        assert len(stateful_skill.sessions) == 0

        session_id = "s-1"
        result = await stateful_skill.invoke({"text": "hi"}, session_id=session_id)
        assert result["text"] == "hi"
        assert session_id in stateful_skill.sessions
        assert "created_at" in stateful_skill.sessions[session_id]


# --------------------------------------------------------------------------
# @skill decorator
# --------------------------------------------------------------------------


class TestSkillDecorator:
    def test_decorator_basic(self) -> None:
        @skill(id="test-echo", name="test-echo", description="Test echo")
        async def test_echo(text: str):
            return {"text": text}

        assert hasattr(test_echo, "_skill")
        s = test_echo._skill  # type: ignore[attr-defined]
        assert isinstance(s, Skill)
        assert s.metadata.id == "test-echo"
        assert s.metadata.name == "test-echo"

    def test_decorator_defaults_to_func_name(self) -> None:
        @skill(description="implicit id/name")
        async def default_echo(text: str):
            return {"text": text}

        s = default_echo._skill  # type: ignore[attr-defined]
        assert s.metadata.id == "default_echo"
        assert s.metadata.name == "default_echo"
        assert s.metadata.description == "implicit id/name"

    def test_decorator_uses_docstring(self) -> None:
        @skill()
        async def doc_echo(text: str):
            """Docstring description."""
            return {"text": text}

        s = doc_echo._skill  # type: ignore[attr-defined]
        assert s.metadata.description == "Docstring description."

    def test_decorator_explicit_metadata(self) -> None:
        meta = SkillMetadata(
            id="m", name="meta-echo", description="explicit meta", version="2.0.0"
        )

        async def test_func(text: str):
            return {"text": text}

        s = Skill(func=test_func, metadata=meta)
        assert s.metadata.id == "m"
        assert s.metadata.version == "2.0.0"
