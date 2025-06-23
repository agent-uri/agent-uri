"""
Tests for the capability module.

This module tests the capability class and decorator for registering
agent capabilities.
"""

import asyncio
import uuid
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from ..capability import Capability, CapabilityMetadata, capability
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

    def test_decorator_with_explicit_metadata(self) -> None:
        """Test decorator using explicit CapabilityMetadata."""
        metadata = CapabilityMetadata(
            name="explicit_test",
            description="Explicit metadata test",
            version="3.0.0",
            tags=["explicit"],
            memory_enabled=True,
        )

        @capability()
        def test_func():
            """Original docstring"""
            return {"result": "test"}

        cap = Capability(func=test_func, metadata=metadata)
        assert cap.metadata.name == "explicit_test"
        assert cap.metadata.description == "Explicit metadata test"
        assert cap.metadata.version == "3.0.0"
        assert cap.metadata.tags == ["explicit"]
        assert cap.metadata.memory_enabled is True

    def test_decorator_default_description_for_echo(self) -> None:
        """Test that echo functions get default descriptions."""

        @capability()
        def my_echo_function():
            pass

        cap = my_echo_function._capability
        assert cap.metadata.description == "Echo back the input text."

        @capability()
        def echo_test():
            pass

        cap2 = echo_test._capability
        assert cap2.metadata.description == "Echo back the input text."

    def test_decorator_preserves_function_docstring(self) -> None:
        """Test that decorator preserves function docstring."""

        @capability()
        def documented_func():
            """This function has documentation."""
            return {"result": "documented"}

        cap = documented_func._capability
        assert cap.metadata.description == "This function has documentation."

    def test_decorator_explicit_description_overrides_docstring(self) -> None:
        """Test that explicit description overrides function docstring."""

        @capability(description="Explicit description")
        def documented_func():
            """This docstring should be ignored."""
            return {"result": "test"}

        cap = documented_func._capability
        assert cap.metadata.description == "Explicit description"

    def test_decorator_all_parameters(self) -> None:
        """Test decorator with all possible parameters."""

        @capability(
            name="full_test",
            description="Full parameter test",
            version="4.0.0",
            tags=["comprehensive", "test"],
            input_schema={
                "type": "object",
                "properties": {"input": {"type": "string"}},
            },
            output_schema={
                "type": "object",
                "properties": {"output": {"type": "string"}},
            },
            is_deterministic=True,
            expected_output_variability="low",
            requires_context=True,
            memory_enabled=True,
            response_latency="high",
            confidence_estimation=True,
            content_types={
                "inputFormat": ["application/json"],
                "outputFormat": ["application/xml"],
            },
            interaction_model="agent2agent",
            streaming=True,
            auth_required=True,
            public=False,
        )
        def comprehensive_func():
            return {"output": "comprehensive"}

        cap = comprehensive_func._capability
        assert cap.metadata.name == "full_test"
        assert cap.metadata.description == "Full parameter test"
        assert cap.metadata.version == "4.0.0"
        assert cap.metadata.tags == ["comprehensive", "test"]
        assert cap.metadata.is_deterministic is True
        assert cap.metadata.expected_output_variability == "low"
        assert cap.metadata.requires_context is True
        assert cap.metadata.memory_enabled is True
        assert cap.metadata.response_latency == "high"
        assert cap.metadata.confidence_estimation is True
        assert cap.metadata.interaction_model == "agent2agent"
        assert cap.metadata.streaming is True
        assert cap.metadata.auth_required is True
        assert cap.metadata.public is False


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


class TestCapabilityMetadata:
    """Tests for the CapabilityMetadata class."""

    def test_init_defaults(self) -> None:
        """Test metadata initialization with defaults."""
        metadata = CapabilityMetadata(name="test")
        assert metadata.name == "test"
        assert metadata.description == ""
        assert metadata.version == "1.0.0"
        assert metadata.tags == []
        assert metadata.input_schema is None
        assert metadata.output_schema is None
        assert metadata.is_deterministic is False
        assert metadata.expected_output_variability == "medium"
        assert metadata.requires_context is False
        assert metadata.memory_enabled is False
        assert metadata.response_latency == "medium"
        assert metadata.confidence_estimation is False
        assert metadata.content_types == {
            "inputFormat": ["application/json"],
            "outputFormat": ["application/json"],
        }
        assert metadata.interaction_model is None
        assert metadata.streaming is False
        assert metadata.auth_required is False
        assert metadata.public is True

    def test_init_with_all_params(self) -> None:
        """Test metadata initialization with all parameters."""
        metadata = CapabilityMetadata(
            name="advanced_test",
            description="Advanced test capability",
            version="2.1.0",
            tags=["advanced", "testing"],
            input_schema={
                "type": "object",
                "properties": {"input": {"type": "string"}},
            },
            output_schema={
                "type": "object",
                "properties": {"output": {"type": "string"}},
            },
            is_deterministic=True,
            expected_output_variability="low",
            requires_context=True,
            memory_enabled=True,
            response_latency="high",
            confidence_estimation=True,
            content_types={
                "inputFormat": ["application/json", "text/plain"],
                "outputFormat": ["application/json", "application/xml"],
            },
            interaction_model="agent2agent",
            streaming=True,
            auth_required=True,
            public=False,
        )

        assert metadata.name == "advanced_test"
        assert metadata.description == "Advanced test capability"
        assert metadata.version == "2.1.0"
        assert metadata.tags == ["advanced", "testing"]
        assert metadata.input_schema == {
            "type": "object",
            "properties": {"input": {"type": "string"}},
        }
        assert metadata.output_schema == {
            "type": "object",
            "properties": {"output": {"type": "string"}},
        }
        assert metadata.is_deterministic is True
        assert metadata.expected_output_variability == "low"
        assert metadata.requires_context is True
        assert metadata.memory_enabled is True
        assert metadata.response_latency == "high"
        assert metadata.confidence_estimation is True
        assert metadata.content_types == {
            "inputFormat": ["application/json", "text/plain"],
            "outputFormat": ["application/json", "application/xml"],
        }
        assert metadata.interaction_model == "agent2agent"
        assert metadata.streaming is True
        assert metadata.auth_required is True
        assert metadata.public is False

    def test_to_dict_minimal(self) -> None:
        """Test to_dict with minimal metadata."""
        metadata = CapabilityMetadata(name="minimal")
        result = metadata.to_dict()

        # Check required fields are present
        assert result["name"] == "minimal"
        assert result["version"] == "1.0.0"
        assert result["description"] == ""
        assert result["contentTypes"] == {
            "inputFormat": ["application/json"],
            "outputFormat": ["application/json"],
        }
        # Behavioral metadata should be included with default values
        assert result["isDeterministic"] is False
        assert result["expectedOutputVariability"] == "medium"
        assert result["requiresContext"] is False
        assert result["memoryEnabled"] is False
        assert result["responseLatency"] == "medium"
        assert result["confidenceEstimation"] is False

    def test_to_dict_with_tags(self) -> None:
        """Test to_dict with tags included."""
        metadata = CapabilityMetadata(name="tagged", tags=["tag1", "tag2"])
        result = metadata.to_dict()

        assert "tags" in result
        assert result["tags"] == ["tag1", "tag2"]

    def test_to_dict_with_schemas(self) -> None:
        """Test to_dict with input and output schemas."""
        input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}
        output_schema = {"type": "object", "properties": {"result": {"type": "string"}}}

        metadata = CapabilityMetadata(
            name="with_schemas",
            input_schema=input_schema,
            output_schema=output_schema,
        )
        result = metadata.to_dict()

        assert "input" in result
        assert result["input"] == input_schema
        assert "output" in result
        assert result["output"] == output_schema

    def test_to_dict_behavioral_metadata(self) -> None:
        """Test to_dict with all behavioral metadata."""
        metadata = CapabilityMetadata(
            name="behavioral",
            is_deterministic=True,
            expected_output_variability="low",
            requires_context=True,
            memory_enabled=True,
            response_latency="high",
            confidence_estimation=True,
        )
        result = metadata.to_dict()

        assert result["isDeterministic"] is True
        assert result["expectedOutputVariability"] == "low"
        assert result["requiresContext"] is True
        assert result["memoryEnabled"] is True
        assert result["responseLatency"] == "high"
        assert result["confidenceEstimation"] is True

    def test_to_dict_with_interaction_model(self) -> None:
        """Test to_dict with interaction model."""
        metadata = CapabilityMetadata(
            name="interactive",
            interaction_model="agent2agent",
        )
        result = metadata.to_dict()

        assert "interactionModel" in result
        assert result["interactionModel"] == "agent2agent"

    def test_to_dict_with_streaming(self) -> None:
        """Test to_dict with streaming enabled."""
        metadata = CapabilityMetadata(name="streaming", streaming=True)
        result = metadata.to_dict()

        assert "streaming" in result
        assert result["streaming"] is True

    def test_to_dict_with_auth_required(self) -> None:
        """Test to_dict with authentication required."""
        metadata = CapabilityMetadata(name="secure", auth_required=True)
        result = metadata.to_dict()

        assert "authRequired" in result
        assert result["authRequired"] is True

    def test_to_dict_excludes_false_streaming(self) -> None:
        """Test that streaming=False is not included in dict."""
        metadata = CapabilityMetadata(name="no_streaming", streaming=False)
        result = metadata.to_dict()

        assert "streaming" not in result

    def test_to_dict_excludes_false_auth(self) -> None:
        """Test that auth_required=False is not included in dict."""
        metadata = CapabilityMetadata(name="no_auth", auth_required=False)
        result = metadata.to_dict()

        assert "authRequired" not in result

    def test_to_dict_custom_content_types(self) -> None:
        """Test to_dict with custom content types."""
        custom_types = {
            "inputFormat": ["text/plain", "application/xml"],
            "outputFormat": ["application/json", "text/csv"],
        }
        metadata = CapabilityMetadata(name="custom", content_types=custom_types)
        result = metadata.to_dict()

        assert result["contentTypes"] == custom_types


class TestCapabilityAdvanced:
    """Advanced tests for Capability class covering edge cases."""

    def test_init_from_kwargs(self) -> None:
        """Test creating capability from kwargs instead of explicit metadata."""
        cap = Capability(
            func=sync_echo,
            name="kwargs_echo",
            description="Echo via kwargs",
            version="2.0.0",
            tags=["test"],
            memory_enabled=True,
        )

        assert cap.metadata.name == "kwargs_echo"
        assert cap.metadata.description == "Echo via kwargs"
        assert cap.metadata.version == "2.0.0"
        assert cap.metadata.tags == ["test"]
        assert cap.metadata.memory_enabled is True
        assert cap.sessions is not None

    def test_init_defaults_from_function(self) -> None:
        """Test that name and description default to function attributes."""

        def documented_func():
            """This is a documented function."""
            pass

        cap = Capability(func=documented_func)
        assert cap.metadata.name == "documented_func"
        assert cap.metadata.description == "This is a documented function."

        def undocumented_func():
            pass

        cap2 = Capability(func=undocumented_func)
        assert cap2.metadata.name == "undocumented_func"
        assert cap2.metadata.description == ""

    @pytest.mark.asyncio
    async def test_invoke_sync_capability(self) -> None:
        """Test invoking a synchronous capability."""
        cap = Capability(func=sync_echo)
        result = await cap.invoke({"text": "Hello"})
        assert result == {"text": "Hello"}

    def test_input_model_creation(self) -> None:
        """Test input model creation from schema."""
        schema = {
            "type": "object",
            "properties": {
                "required_field": {"type": "string"},
                "optional_field": {"type": "integer", "default": 42},
                "boolean_field": {"type": "boolean"},
                "array_field": {"type": "array"},
                "object_field": {"type": "object"},
                "number_field": {"type": "number"},
                "null_field": {"type": "null"},
                "unknown_field": {"type": "unknown_type"},
            },
            "required": ["required_field"],
        }

        cap = Capability(func=sync_echo, input_schema=schema)
        assert cap.input_model is not None

        # Test valid input
        valid_data = {"required_field": "test"}
        validated = cap.validate_input(valid_data)
        assert validated["required_field"] == "test"
        assert validated["optional_field"] == 42  # Default value

        # Test missing required field
        with pytest.raises(InvalidInputError):
            cap.validate_input({"optional_field": 123})

    def test_input_model_creation_failure(self) -> None:
        """Test handling of input model creation failures."""
        # Test with None schema
        cap1 = Capability(func=sync_echo, input_schema=None)
        assert cap1.input_model is None

        # Test with malformed schema that should cause creation to fail
        with patch("agent_uri.capability.create_model") as mock_create:
            mock_create.side_effect = Exception("Schema error")

            cap2 = Capability(
                func=sync_echo,
                input_schema={
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                },
            )
            assert cap2.input_model is None

    def test_validate_input_without_model(self) -> None:
        """Test input validation when no model is created."""
        cap = Capability(func=sync_echo)  # No input_schema
        data = {"any": "data"}
        result = cap.validate_input(data)
        assert result == data  # Should return unchanged

    def test_validate_input_with_validation_error(self) -> None:
        """Test input validation with pydantic ValidationError."""
        schema = {
            "type": "object",
            "properties": {"number": {"type": "integer"}},
            "required": ["number"],
        }

        cap = Capability(func=sync_echo, input_schema=schema)

        # Test with string instead of integer
        with pytest.raises(InvalidInputError) as exc_info:
            cap.validate_input({"number": "not_a_number"})

        assert "Input validation failed" in str(exc_info.value)

    def test_validate_input_with_general_error(self) -> None:
        """Test input validation with general exception."""
        cap = Capability(func=sync_echo, input_schema={"type": "object"})

        # Mock the input_model to raise a general exception
        with patch.object(cap, "input_model") as mock_model:
            mock_model.side_effect = RuntimeError("General error")

            with pytest.raises(InvalidInputError) as exc_info:
                cap.validate_input({"test": "data"})

            assert "Input validation error" in str(exc_info.value)

    def test_schema_type_to_python(self) -> None:
        """Test schema type to Python type conversion."""
        cap = Capability(func=sync_echo)

        assert cap._schema_type_to_python("string") == str
        assert cap._schema_type_to_python("integer") == int
        assert cap._schema_type_to_python("number") == float
        assert cap._schema_type_to_python("boolean") == bool
        assert cap._schema_type_to_python("array") == list
        assert cap._schema_type_to_python("object") == dict
        assert cap._schema_type_to_python("null") is type(None)
        # Unknown type should return Any
        unknown_type = cap._schema_type_to_python("unknown")
        assert unknown_type is not None

    @pytest.mark.asyncio
    async def test_session_management_detailed(self) -> None:
        """Test detailed session management functionality."""

        # Function that expects session_id and context
        async def session_aware_func(
            text: str, session_id: str, context: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Function that uses session data."""
            return {
                "text": text,
                "session_id": session_id,
                "received_context": context,
                "context": {"last_input": text},  # Return new context
            }

        cap = Capability(func=session_aware_func, memory_enabled=True)
        session_id = "test-session-123"

        # First invocation - creates session
        result1 = await cap.invoke(
            {"text": "first"}, session_id=session_id, context={"initial": "data"}
        )

        assert result1["text"] == "first"
        assert result1["session_id"] == session_id
        assert session_id in cap.sessions

        # Check session was updated with context from result
        assert cap.sessions[session_id]["last_input"] == "first"
        assert cap.sessions[session_id]["initial"] == "data"

    @pytest.mark.asyncio
    async def test_session_id_parameter_handling(self) -> None:
        """Test session_id parameter handling in capabilities."""

        async def session_func(text: str, session_id: str) -> Dict[str, Any]:
            return {"text": text, "session_id": session_id}

        cap = Capability(func=session_func, memory_enabled=True)

        # Test normal session ID passing
        result = await cap.invoke({"text": "test"}, session_id="main-session")
        assert result["session_id"] == "main-session"

    @pytest.mark.asyncio
    async def test_session_context_without_session_id(self) -> None:
        """Test context handling without session_id parameter in function."""

        async def context_func(text: str, context: Dict[str, Any]) -> Dict[str, Any]:
            return {"text": text, "received_context": context}

        cap = Capability(func=context_func, memory_enabled=True)
        session_id = "context-session"

        # First call
        await cap.invoke({"text": "first"}, session_id=session_id)

        # Second call with additional context
        result = await cap.invoke(
            {"text": "second"}, session_id=session_id, context={"new": "context"}
        )

        # Should receive merged context
        received_context = result["received_context"]
        assert "created_at" in received_context  # From session creation
        assert received_context["new"] == "context"  # From this call

    @pytest.mark.asyncio
    async def test_memory_disabled_no_sessions(self) -> None:
        """Test that sessions are not created when memory is disabled."""
        cap = Capability(func=async_echo, memory_enabled=False)
        assert cap.sessions is None

        result = await cap.invoke({"text": "test"}, session_id="should-be-ignored")
        assert result == {"text": "test"}
        assert cap.sessions is None

    @pytest.mark.asyncio
    async def test_result_context_update_edge_cases(self) -> None:
        """Test edge cases in result context updating."""

        async def context_returning_func(text: str) -> Dict[str, Any]:
            return {"text": text, "context": {"response_data": "important"}}

        cap = Capability(func=context_returning_func, memory_enabled=True)
        session_id = "context-update-session"

        # Call that returns context
        await cap.invoke({"text": "test"}, session_id=session_id)

        # Check that session was updated with returned context
        assert session_id in cap.sessions
        assert cap.sessions[session_id]["response_data"] == "important"

        # Test with non-dict result (should not cause errors)
        async def string_return_func(text: str) -> str:
            return text

        cap2 = Capability(func=string_return_func, memory_enabled=True)
        await cap2.invoke({"text": "test"}, session_id="string-session")
        # Session should still be created but not updated
        assert "string-session" in cap2.sessions

    @pytest.mark.asyncio
    async def test_input_validation_preserves_input_errors(self) -> None:
        """Test that InvalidInputError is re-raised without wrapping."""
        schema = {
            "type": "object",
            "properties": {"required_field": {"type": "string"}},
            "required": ["required_field"],
        }

        cap = Capability(func=sync_echo, input_schema=schema)

        # Should re-raise InvalidInputError directly
        with pytest.raises(InvalidInputError):
            await cap.invoke({"wrong_field": "value"})


class TestCapabilityConcurrency:
    """Tests for capability concurrency and threading."""

    @pytest.mark.asyncio
    async def test_concurrent_invocations(self) -> None:
        """Test concurrent capability invocations."""

        async def slow_echo(text: str, delay: float = 0.1) -> Dict[str, Any]:
            await asyncio.sleep(delay)
            return {"text": text, "timestamp": uuid.uuid4().hex}

        cap = Capability(func=slow_echo)

        # Start multiple concurrent invocations
        tasks = [cap.invoke({"text": f"test_{i}", "delay": 0.05}) for i in range(5)]

        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["text"] == f"test_{i}"
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_concurrent_session_management(self) -> None:
        """Test concurrent access to session management."""

        async def session_counter(
            session_id: str, context: Dict[str, Any]
        ) -> Dict[str, Any]:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            count = context.get("count", 0) + 1
            return {"count": count, "context": {"count": count}}

        cap = Capability(func=session_counter, memory_enabled=True)
        session_id = "concurrent-session"

        # Start multiple concurrent session operations
        tasks = [cap.invoke({}, session_id=session_id) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Check that all completed and session was properly managed
        assert len(results) == 10
        assert session_id in cap.sessions

        # At least one should have incremented the counter
        counts = [result["count"] for result in results]
        assert max(counts) > 1

    @pytest.mark.asyncio
    async def test_multiple_sessions_concurrent(self) -> None:
        """Test concurrent operations across multiple sessions."""

        async def session_echo(text: str, session_id: str) -> Dict[str, Any]:
            await asyncio.sleep(0.01)
            return {"text": text, "session": session_id}

        cap = Capability(func=session_echo, memory_enabled=True)

        # Create tasks for different sessions
        tasks = []
        session_ids = [f"session_{i}" for i in range(5)]

        for session_id in session_ids:
            for j in range(3):
                tasks.append(
                    cap.invoke(
                        {"text": f"{session_id}_message_{j}"}, session_id=session_id
                    )
                )

        results = await asyncio.gather(*tasks)

        # All sessions should be created
        assert len(cap.sessions) == 5
        for session_id in session_ids:
            assert session_id in cap.sessions

        # All invocations should complete
        assert len(results) == 15

    def test_thread_safety_session_creation(self) -> None:
        """Test thread safety of session creation."""
        import threading
        import time

        def sync_session_func(text: str, session_id: str) -> Dict[str, Any]:
            time.sleep(0.01)  # Simulate work
            return {"text": text, "session": session_id}

        cap = Capability(func=sync_session_func, memory_enabled=True)
        results = []
        errors = []

        def worker(session_id: str, message_id: int):
            try:
                # Use asyncio.run in thread for async invoke
                import asyncio

                result = asyncio.run(
                    cap.invoke({"text": f"message_{message_id}"}, session_id=session_id)
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads accessing same session
        threads = []
        session_id = "thread-safe-session"

        for i in range(5):
            thread = threading.Thread(target=worker, args=(session_id, i))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        assert session_id in cap.sessions


class TestCapabilityIntegration:
    """Integration tests for capabilities with other components."""

    def test_capability_with_complex_schemas(self) -> None:
        """Test capability with complex nested schemas."""
        complex_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                        "preferences": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name"],
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string"},
                        "version": {"type": "number", "default": 1.0},
                    },
                },
            },
            "required": ["user"],
        }

        async def complex_processor(
            user: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            return {
                "processed_user": user,
                "metadata": metadata or {},
                "status": "processed",
            }

        cap = Capability(func=complex_processor, input_schema=complex_schema)

        # Test valid complex input
        valid_input = {
            "user": {"name": "Alice", "age": 30, "preferences": ["reading", "coding"]},
            "metadata": {"timestamp": "2023-01-01T00:00:00Z"},
        }

        validated = cap.validate_input(valid_input)
        assert validated["user"]["name"] == "Alice"
        # Note: default values from schema may not be applied during validation
        assert "metadata" in validated

    @pytest.mark.asyncio
    async def test_capability_streaming_metadata(self) -> None:
        """Test capability with streaming metadata set."""

        @capability(
            name="streaming_test",
            streaming=True,
            response_latency="low",
            confidence_estimation=True,
        )
        async def streaming_func(text: str) -> Dict[str, Any]:
            return {"text": text, "confidence": 0.95, "streaming": True}

        cap = streaming_func._capability
        assert cap.metadata.streaming is True
        assert cap.metadata.response_latency == "low"
        assert cap.metadata.confidence_estimation is True

        # Test that metadata appears in dict
        metadata_dict = cap.metadata.to_dict()
        assert metadata_dict["streaming"] is True
        assert metadata_dict["responseLatency"] == "low"
        assert metadata_dict["confidenceEstimation"] is True

    @pytest.mark.asyncio
    async def test_capability_with_auth_and_privacy(self) -> None:
        """Test capability with authentication and privacy settings."""

        @capability(
            name="secure_func",
            auth_required=True,
            public=False,
            tags=["secure", "private"],
        )
        async def secure_func(secret_data: str) -> Dict[str, Any]:
            return {"processed": True, "length": len(secret_data)}

        cap = secure_func._capability
        assert cap.metadata.auth_required is True
        assert cap.metadata.public is False
        assert "secure" in cap.metadata.tags
        assert "private" in cap.metadata.tags

        # Test metadata dict
        metadata_dict = cap.metadata.to_dict()
        assert metadata_dict["authRequired"] is True
        # public=False should not appear (only True values are included)
        assert "public" not in metadata_dict

    def test_edge_case_empty_properties_schema(self) -> None:
        """Test schema with empty properties."""
        empty_schema = {"type": "object", "properties": {}, "required": []}

        cap = Capability(func=sync_echo, input_schema=empty_schema)
        assert cap.input_model is not None

        # Should validate empty dict
        result = cap.validate_input({})
        assert result == {}

    def test_edge_case_no_properties_in_schema(self) -> None:
        """Test schema without properties field."""
        minimal_schema = {"type": "object"}

        cap = Capability(func=sync_echo, input_schema=minimal_schema)
        assert cap.input_model is not None

        # Schema with no properties should validate but may return empty dict
        result = cap.validate_input({"anything": "goes"})
        assert isinstance(result, dict)  # Should return a dict

    @pytest.mark.asyncio
    async def test_capability_error_propagation(self) -> None:
        """Test that different types of errors are properly propagated."""

        # Test InvalidInputError propagation
        async def validation_error_func(**kwargs):
            raise InvalidInputError("Custom validation error")

        cap1 = Capability(func=validation_error_func)
        with pytest.raises(InvalidInputError) as exc_info:
            await cap1.invoke({})
        assert "Custom validation error" in str(exc_info.value)

        # Test general error wrapping
        async def general_error_func(**kwargs):
            raise RuntimeError("General runtime error")

        cap2 = Capability(func=general_error_func)
        with pytest.raises(CapabilityError) as exc_info:
            await cap2.invoke({})
        assert "Error invoking capability" in str(exc_info.value)
        assert "General runtime error" in str(exc_info.value)

    def test_capability_function_signature_introspection(self) -> None:
        """Test that capability properly introspects function signatures."""

        def func_with_session_id(text: str, session_id: str) -> str:
            return f"{text} from {session_id}"

        def func_with_context(text: str, context: Dict[str, Any]) -> str:
            return f"{text} with context"

        def func_with_both(text: str, session_id: str, context: Dict[str, Any]) -> str:
            return f"{text} from {session_id} with context"

        def func_with_neither(text: str) -> str:
            return text

        # Test signature detection
        cap1 = Capability(func=func_with_session_id, memory_enabled=True)
        cap2 = Capability(func=func_with_context, memory_enabled=True)
        cap3 = Capability(func=func_with_both, memory_enabled=True)
        cap4 = Capability(func=func_with_neither, memory_enabled=True)

        # All should be created successfully
        assert cap1.metadata.memory_enabled is True
        assert cap2.metadata.memory_enabled is True
        assert cap3.metadata.memory_enabled is True
        assert cap4.metadata.memory_enabled is True
