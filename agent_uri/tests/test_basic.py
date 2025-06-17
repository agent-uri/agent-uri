"""
Basic tests to verify that the server package is working correctly.

This file contains simple tests to verify that the server package
is installed correctly and can be imported and used.
"""

import pytest

from ..capability import Capability


def test_import():
    """Test that the package can be imported correctly."""
    import agent_uri

    assert agent_uri is not None


def test_capability_creation():
    """Test that a capability can be created."""

    async def echo(text: str):
        return {"text": text}

    cap = Capability(
        func=echo, name="echo", description="Echo the input text", version="1.0.0"
    )

    assert cap.metadata.name == "echo"
    assert cap.metadata.description == "Echo the input text"
    assert cap.metadata.version == "1.0.0"


@pytest.mark.asyncio
async def test_capability_invocation():
    """Test that a capability can be invoked."""

    async def echo(text: str):
        return {"text": text}

    cap = Capability(
        func=echo, name="echo", description="Echo the input text", version="1.0.0"
    )

    result = await cap.invoke({"text": "Hello, world!"})
    assert result == {"text": "Hello, world!"}
