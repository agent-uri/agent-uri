"""
Tests for the capability module.

This module tests the capability class and decorator for registering
agent capabilities.
"""

from typing import Any, Dict

import pytest

from ..capability import Capability, capability
from ..exceptions import CapabilityError, InvalidInputError


# Test functions to use as capabilities
async def async_echo(text: str) -> Dict[str, Any]:
    """Echo the input text."""
    return {"text": text}


def sync_echo(text: str) -> Dict[str, Any]:
    """Echo the input text."""
    return {"text": text}


# Test capability classes
@pytest.fixture
def simple_capability() -> Capability:
    """Create a simple capability for testing."""
    return Capability(
        func=async_echo, name="echo", description="Echo the input text", version="1.0.0"
    )


@pytest.fixture
def schema_capability() -> Capability:
    """Create a capability with input schema for testing."""
    return Capability(
        func=async_echo,
        name="echo",
        description="Echo the input text",
        version="1.0.0",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )


@pytest.fixture
def stateful_capability() -> Capability:
    """Create a stateful capability for testing."""
    return Capability(
        func=async_echo,
        name="echo",
        description="Echo the input text",
        version="1.0.0",
        memory_enabled=True,
    )


class TestCapability:
    """Tests for the Capability class."""

    def test_init(self, simple_capability: Capability) -> None:
        """Test capability initialization."""
        assert simple_capability.func == async_echo
        assert simple_capability.metadata.name == "echo"
        assert simple_capability.metadata.description == "Echo the input text"
        assert simple_capability.metadata.version == "1.0.0"
        assert simple_capability.is_async is True
        assert simple_capability.input_model is None
        assert simple_capability.sessions is None

    def test_init_with_sync_function(self) -> None:
        """Test capability initialization with a synchronous function."""
        cap = Capability(func=sync_echo)
        assert cap.func == sync_echo
        assert cap.is_async is False

    def test_metadata_to_dict(self, simple_capability: Capability) -> None:
        """Test converting metadata to dictionary."""
        metadata_dict = simple_capability.metadata.to_dict()
        assert metadata_dict["name"] == "echo"
        assert metadata_dict["version"] == "1.0.0"
        assert metadata_dict["description"] == "Echo the input text"

    @pytest.mark.asyncio
    async def test_invoke(self, simple_capability: Capability) -> None:
        """Test invoking a capability."""
        result = await simple_capability.invoke({"text": "Hello"})
        assert result == {"text": "Hello"}

    @pytest.mark.asyncio
    async def test_invoke_with_validation(self, schema_capability: Capability) -> None:
        """Test invoking a capability with input validation."""
        result = await schema_capability.invoke({"text": "Hello"})
        assert result == {"text": "Hello"}

        # Test with invalid input
        with pytest.raises(InvalidInputError):
            await schema_capability.invoke({"not_text": "Hello"})

    @pytest.mark.asyncio
    async def test_stateful_capability(self, stateful_capability: Capability) -> None:
        """Test invoking a stateful capability."""
        # Initial check: no sessions
        assert isinstance(stateful_capability.sessions, dict)
        assert len(stateful_capability.sessions) == 0

        # Invoke with session ID
        session_id = "test-session"
        result = await stateful_capability.invoke(
            {"text": "Hello"}, session_id=session_id
        )
        assert result == {"text": "Hello"}

        # Check that session was created
        assert session_id in stateful_capability.sessions
        assert "created_at" in stateful_capability.sessions[session_id]


class TestCapabilityDecorator:
    """Tests for the capability decorator."""

    def test_decorator(self) -> None:
        """Test the capability decorator."""

        @capability(
            name="test-echo",
            description="Test echo capability",
            version="1.0.0",
            tags=["test", "echo"],
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )
        async def test_echo(text: str) -> Dict[str, Any]:
            return {"text": text}

        # Check that the decorator attached metadata
        assert hasattr(test_echo, "_capability")
        cap = test_echo._capability
        assert isinstance(cap, Capability)
        assert cap.metadata.name == "test-echo"
        assert cap.metadata.description == "Test echo capability"
        assert cap.metadata.version == "1.0.0"
        assert "test" in cap.metadata.tags
        assert "echo" in cap.metadata.tags

    @pytest.mark.asyncio
    async def test_decorated_function_invocation(self) -> None:
        """Test invoking a decorated function."""

        @capability()
        async def default_echo(text: str) -> Dict[str, Any]:
            return {"text": text}

        # Check default values
        cap = default_echo._capability
        assert cap.metadata.name == "default_echo"
        assert cap.metadata.description == "Echo back the input text."

        # Test invocation
        assert await default_echo("Hello") == {"text": "Hello"}

        # Test invocation through capability
        result = await cap.invoke({"text": "Hello"})
        assert result == {"text": "Hello"}


@pytest.mark.asyncio
async def test_capability_error_handling(simple_capability: Capability) -> None:
    """Test error handling in capabilities."""

    # Create a capability that raises an exception
    async def faulty_func(**kwargs):
        raise ValueError("Test error")

    cap = Capability(func=faulty_func, name="faulty")

    # Test that the error is properly wrapped
    with pytest.raises(CapabilityError) as exc_info:
        await cap.invoke({})

    assert "Error invoking capability" in str(exc_info.value)
    assert "Test error" in str(exc_info.value)
