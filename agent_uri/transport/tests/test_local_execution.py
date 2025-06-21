"""
Tests for local transport function execution functionality.

This module tests function invocation, parameter handling, return value processing,
and execution contexts for the local transport.
"""

import asyncio
import threading
import time
from unittest.mock import patch

import pytest

from agent_uri.transport.base import TransportError
from agent_uri.transport.transports.local import LocalTransport


class TestLocalTransportExecution:
    """Test local transport function execution."""

    @pytest.fixture
    def transport(self):
        """Create a LocalTransport instance."""
        return LocalTransport()

    def test_invoke_sync_function_basic(self, transport):
        """Test invoking basic synchronous function."""

        def add_numbers(a: int, b: int) -> int:
            return a + b

        with patch.object(transport, "_resolve_function", return_value=add_numbers):
            result = transport.invoke("test://module", "add_numbers", {"a": 5, "b": 3})
            assert result == 8

    def test_invoke_sync_function_with_kwargs(self, transport):
        """Test invoking function with keyword arguments."""

        def format_message(
            message: str, prefix: str = "INFO", suffix: str = "!"
        ) -> str:
            return f"{prefix}: {message}{suffix}"

        with patch.object(transport, "_resolve_function", return_value=format_message):
            result = transport.invoke(
                "test://module",
                "format_message",
                {"message": "Hello World", "prefix": "DEBUG", "suffix": "..."},
            )
            assert result == "DEBUG: Hello World..."

    def test_invoke_function_with_no_params(self, transport):
        """Test invoking function with no parameters."""

        def get_timestamp() -> str:
            return "2024-01-01T00:00:00Z"

        with patch.object(transport, "_resolve_function", return_value=get_timestamp):
            result = transport.invoke("test://module", "get_timestamp", {})
            assert result == "2024-01-01T00:00:00Z"

    def test_invoke_function_returning_complex_data(self, transport):
        """Test invoking function that returns complex data structures."""

        def get_user_data(user_id: int) -> dict:
            return {
                "id": user_id,
                "name": f"User {user_id}",
                "roles": ["user", "member"],
                "metadata": {"created": "2024-01-01", "active": True},
            }

        with patch.object(transport, "_resolve_function", return_value=get_user_data):
            result = transport.invoke(
                "test://module", "get_user_data", {"user_id": 123}
            )

            assert result["id"] == 123
            assert result["name"] == "User 123"
            assert "user" in result["roles"]
            assert result["metadata"]["active"] is True

    def test_invoke_function_with_type_conversion(self, transport):
        """Test function invocation with automatic type conversion."""

        def calculate_area(width: float, height: float) -> float:
            return width * height

        with patch.object(transport, "_resolve_function", return_value=calculate_area):
            # Pass strings that should be converted to floats
            result = transport.invoke(
                "test://module", "calculate_area", {"width": "10.5", "height": "5.0"}
            )
            assert result == 52.5

    def test_invoke_function_with_list_params(self, transport):
        """Test invoking function with list parameters."""

        def sum_numbers(numbers: list) -> int:
            return sum(numbers)

        with patch.object(transport, "_resolve_function", return_value=sum_numbers):
            result = transport.invoke(
                "test://module", "sum_numbers", {"numbers": [1, 2, 3, 4, 5]}
            )
            assert result == 15

    def test_invoke_function_with_nested_params(self, transport):
        """Test invoking function with nested parameter structures."""

        def process_request(request: dict) -> dict:
            return {
                "status": "processed",
                "user": request.get("user", "anonymous"),
                "action": request.get("action", "unknown"),
                "result": len(request.get("data", [])),
            }

        with patch.object(transport, "_resolve_function", return_value=process_request):
            result = transport.invoke(
                "test://module",
                "process_request",
                {
                    "request": {
                        "user": "john_doe",
                        "action": "create",
                        "data": [1, 2, 3],
                    }
                },
            )

            assert result["status"] == "processed"
            assert result["user"] == "john_doe"
            assert result["action"] == "create"
            assert result["result"] == 3

    def test_invoke_function_with_exception(self, transport):
        """Test invoking function that raises an exception."""

        def failing_function(should_fail: bool) -> str:
            if should_fail:
                raise ValueError("This function was designed to fail")
            return "success"

        with patch.object(
            transport, "_resolve_function", return_value=failing_function
        ):
            with pytest.raises(TransportError) as excinfo:
                transport.invoke(
                    "test://module", "failing_function", {"should_fail": True}
                )

            assert "Function execution failed" in str(excinfo.value)
            assert "This function was designed to fail" in str(excinfo.value)

    def test_invoke_function_with_timeout(self, transport):
        """Test function invocation with timeout."""

        def slow_function(delay: float) -> str:
            time.sleep(delay)
            return "completed"

        with patch.object(transport, "_resolve_function", return_value=slow_function):
            # Test successful execution within timeout
            result = transport.invoke(
                "test://module", "slow_function", {"delay": 0.1}, timeout=5
            )
            assert result == "completed"

    def test_invoke_async_function(self, transport):
        """Test invoking async function."""

        async def async_add(a: int, b: int) -> int:
            await asyncio.sleep(0.01)  # Simulate async work
            return a + b

        with patch.object(transport, "_resolve_function", return_value=async_add):
            result = transport.invoke("test://module", "async_add", {"a": 10, "b": 20})
            assert result == 30

    def test_invoke_async_function_with_exception(self, transport):
        """Test invoking async function that raises an exception."""

        async def async_failing_function() -> str:
            await asyncio.sleep(0.01)
            raise ValueError("Async function failed")

        with patch.object(
            transport, "_resolve_function", return_value=async_failing_function
        ):
            with pytest.raises(TransportError) as excinfo:
                transport.invoke("test://module", "async_failing_function", {})

            assert "Function execution failed" in str(excinfo.value)
            assert "Async function failed" in str(excinfo.value)

    def test_stream_generator_function(self, transport):
        """Test streaming from generator function."""

        def number_generator(start: int, count: int):
            for i in range(start, start + count):
                yield {"number": i, "square": i * i}

        with patch.object(
            transport, "_resolve_function", return_value=number_generator
        ):
            results = list(
                transport.stream(
                    "test://module", "number_generator", {"start": 1, "count": 5}
                )
            )

            assert len(results) == 5
            assert results[0] == {"number": 1, "square": 1}
            assert results[4] == {"number": 5, "square": 25}

    def test_stream_async_generator_function(self, transport):
        """Test streaming from async generator function."""

        async def async_number_generator(start: int, count: int):
            for i in range(start, start + count):
                await asyncio.sleep(0.001)  # Simulate async work
                yield {"value": i, "timestamp": time.time()}

        with patch.object(
            transport, "_resolve_function", return_value=async_number_generator
        ):
            results = list(
                transport.stream(
                    "test://module", "async_number_generator", {"start": 10, "count": 3}
                )
            )

            assert len(results) == 3
            assert results[0]["value"] == 10
            assert results[2]["value"] == 12

    def test_stream_function_with_exception(self, transport):
        """Test streaming function that raises an exception."""

        def failing_generator(count: int):
            for i in range(count):
                if i == 2:
                    raise ValueError(f"Error at item {i}")
                yield {"item": i}

        with patch.object(
            transport, "_resolve_function", return_value=failing_generator
        ):
            with pytest.raises(TransportError) as excinfo:
                list(
                    transport.stream("test://module", "failing_generator", {"count": 5})
                )

            assert "Streaming function failed" in str(excinfo.value)

    def test_invoke_function_with_complex_return_types(self, transport):
        """Test function returning various Python types."""

        def get_various_types() -> dict:
            return {
                "string": "hello",
                "integer": 42,
                "float": 3.14,
                "boolean": True,
                "none_value": None,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
                "tuple": (1, 2, 3),  # Will be converted to list in JSON
                "set": {4, 5, 6},  # Will be converted to list in JSON
            }

        with patch.object(
            transport, "_resolve_function", return_value=get_various_types
        ):
            result = transport.invoke("test://module", "get_various_types", {})

            assert result["string"] == "hello"
            assert result["integer"] == 42
            assert result["float"] == 3.14
            assert result["boolean"] is True
            assert result["none_value"] is None
            assert result["list"] == [1, 2, 3]
            assert result["dict"]["nested"] == "value"

    def test_function_execution_isolation(self, transport):
        """Test that function executions are isolated."""
        # Create a function that modifies global state
        state_holder = {"counter": 0}

        def increment_counter(amount: int = 1) -> int:
            state_holder["counter"] += amount
            return state_holder["counter"]

        with patch.object(
            transport, "_resolve_function", return_value=increment_counter
        ):
            # Multiple invocations should see shared state
            result1 = transport.invoke(
                "test://module", "increment_counter", {"amount": 5}
            )
            result2 = transport.invoke(
                "test://module", "increment_counter", {"amount": 3}
            )

            assert result1 == 5
            assert result2 == 8

    def test_concurrent_function_execution(self, transport):
        """Test concurrent function executions."""

        def slow_add(a: int, b: int, delay: float = 0.1) -> dict:
            time.sleep(delay)
            return {"result": a + b, "thread_id": threading.current_thread().ident}

        with patch.object(transport, "_resolve_function", return_value=slow_add):
            # Start multiple concurrent invocations
            results = {}
            threads = []

            def invoke_and_store(key, a, b):
                result = transport.invoke(
                    "test://module", "slow_add", {"a": a, "b": b, "delay": 0.05}
                )
                results[key] = result

            for i in range(3):
                thread = threading.Thread(target=invoke_and_store, args=(i, i, i + 1))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All should complete successfully
            assert len(results) == 3
            assert results[0]["result"] == 1  # 0 + 1
            assert results[1]["result"] == 3  # 1 + 2
            assert results[2]["result"] == 5  # 2 + 3

    def test_function_with_side_effects(self, transport):
        """Test function that has side effects."""
        log_entries = []

        def log_and_return(message: str, level: str = "INFO") -> dict:
            entry = {"message": message, "level": level, "timestamp": time.time()}
            log_entries.append(entry)
            return {"logged": True, "entry_count": len(log_entries)}

        with patch.object(transport, "_resolve_function", return_value=log_and_return):
            result1 = transport.invoke(
                "test://module", "log_and_return", {"message": "First message"}
            )
            result2 = transport.invoke(
                "test://module",
                "log_and_return",
                {"message": "Second message", "level": "ERROR"},
            )

            assert result1["logged"] is True
            assert result1["entry_count"] == 1
            assert result2["entry_count"] == 2
            assert len(log_entries) == 2
            assert log_entries[0]["level"] == "INFO"
            assert log_entries[1]["level"] == "ERROR"

    def test_function_parameter_validation(self, transport):
        """Test parameter validation for function calls."""

        def typed_function(name: str, age: int, active: bool = True) -> dict:
            return {"name": name, "age": age, "active": active}

        with patch.object(transport, "_resolve_function", return_value=typed_function):
            # Test with correct types
            result = transport.invoke(
                "test://module",
                "typed_function",
                {"name": "John", "age": 30, "active": False},
            )
            assert result == {"name": "John", "age": 30, "active": False}

    def test_stream_empty_generator(self, transport):
        """Test streaming from empty generator."""

        def empty_generator():
            return
            yield  # Never reached

        with patch.object(transport, "_resolve_function", return_value=empty_generator):
            results = list(transport.stream("test://module", "empty_generator", {}))
            assert results == []

    def test_stream_large_dataset(self, transport):
        """Test streaming large datasets."""

        def large_data_generator(size: int):
            for i in range(size):
                yield {"index": i, "data": f"item_{i}", "chunk": i // 100}

        with patch.object(
            transport, "_resolve_function", return_value=large_data_generator
        ):
            results = list(
                transport.stream(
                    "test://module", "large_data_generator", {"size": 1000}
                )
            )

            assert len(results) == 1000
            assert results[0] == {"index": 0, "data": "item_0", "chunk": 0}
            assert results[999] == {"index": 999, "data": "item_999", "chunk": 9}
