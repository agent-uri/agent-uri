"""
Smoke tests: verify the package imports and core types round-trip.

Aligned with draft-narvaneni-agent-uri-03. Use ``Skill`` (not the
legacy ``Capability``).
"""

import pytest

from ..skill import Skill


def test_import() -> None:
    import agent_uri

    assert agent_uri.__version__ == "0.5.0"


def test_skill_creation() -> None:
    async def echo(text: str):
        return {"text": text}

    s = Skill(
        func=echo,
        id="echo",
        name="echo",
        description="Echo the input text",
        version="1.0.0",
    )

    assert s.metadata.id == "echo"
    assert s.metadata.name == "echo"
    assert s.metadata.description == "Echo the input text"
    assert s.metadata.version == "1.0.0"


@pytest.mark.asyncio
async def test_skill_invocation() -> None:
    async def echo(text: str):
        return {"text": text}

    s = Skill(
        func=echo,
        id="echo",
        name="echo",
        description="Echo the input text",
        version="1.0.0",
    )

    result = await s.invoke({"text": "Hello, world!"})
    assert result == {"text": "Hello, world!"}
