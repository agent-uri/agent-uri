"""
Tests for WebSocket message formatting and parsing functionality.

This module tests message formatting, JSON handling, response parsing,
and data serialization/deserialization.
"""

import json

import pytest

from agent_uri.transport.transports.websocket import WebSocketTransport


class TestWebSocketMessageFormatting:
    """Test message formatting and parsing capabilities."""

    @pytest.fixture
    def transport(self):
        """Create a WebSocketTransport instance."""
        return WebSocketTransport()

    def test_format_body_with_dict(self, transport):
        """Test formatting complex dictionary structures."""
        body = {
            "query": {
                "filters": [
                    {"field": "status", "value": "active"},
                    {"field": "tags", "value": ["ai", "agent", "protocol"]},
                ],
                "sort": {"field": "created", "order": "desc"},
                "pagination": {"page": 1, "size": 20},
            },
            "metadata": {"timestamp": "2024-01-01T00:00:00Z", "version": "1.0.0"},
        }
        formatted = transport.format_body(body)

        # Should produce pretty-printed JSON
        assert isinstance(formatted, str)
        assert "filters" in formatted
        assert "  " in formatted  # Check for indentation

        # Should be valid JSON
        parsed = json.loads(formatted)
        assert parsed == body

    def test_format_body_with_string(self, transport):
        """Test formatting string bodies."""
        body = "This is a plain text message"
        formatted = transport.format_body(body)
        assert formatted == body

    def test_format_body_with_list(self, transport):
        """Test formatting list structures."""
        body = [
            {"id": 1, "name": "First item"},
            {"id": 2, "name": "Second item"},
            {"id": 3, "data": [1, 2, 3, 4, 5]},
        ]
        formatted = transport.format_body(body)

        # Should be pretty-printed JSON
        assert isinstance(formatted, str)
        assert "  " in formatted

        # Should preserve structure
        parsed = json.loads(formatted)
        assert parsed == body

    def test_format_body_with_special_characters(self, transport):
        """Test formatting with unicode and special characters."""
        body = {
            "message": "Hello 世界! 🌍",
            "data": 'Special chars: \n\t\r\\"',
            "emoji": "🚀 🎉 💎",
            "unicode": "café naïve résumé",
        }
        formatted = transport.format_body(body)

        # Should handle unicode correctly
        parsed = json.loads(formatted)
        assert parsed["message"] == "Hello 世界! 🌍"
        assert parsed["emoji"] == "🚀 🎉 💎"
        assert parsed["unicode"] == "café naïve résumé"

    def test_format_body_with_none_values(self, transport):
        """Test formatting with None values."""
        body = {
            "required": "value",
            "optional": None,
            "nested": {"present": 42, "missing": None},
        }
        formatted = transport.format_body(body)

        parsed = json.loads(formatted)
        assert parsed["optional"] is None
        assert parsed["nested"]["missing"] is None

    def test_parse_response_with_dict(self, transport):
        """Test parsing response that's already a dictionary."""
        response = {"status": "ok", "data": [1, 2, 3], "metadata": {"count": 3}}
        parsed = transport.parse_response(response)
        assert parsed == response
        assert parsed is response  # Should be same object

    def test_parse_response_with_json_string(self, transport):
        """Test parsing JSON string responses."""
        response_data = {"status": "success", "result": {"value": 42}}
        response = json.dumps(response_data)
        parsed = transport.parse_response(response)
        assert parsed == response_data

    def test_parse_response_with_plain_string(self, transport):
        """Test parsing plain text responses."""
        response = "This is a plain text response"
        parsed = transport.parse_response(response)
        assert parsed == response

    def test_parse_response_with_malformed_json(self, transport):
        """Test parsing handles malformed JSON gracefully."""
        malformed_cases = [
            '{"incomplete": "json"',  # Missing closing brace
            '{"invalid": json}',  # Unquoted value
            "",  # Empty string
            "not json at all",  # Plain text
        ]

        # Test truly malformed cases
        for malformed in malformed_cases:
            parsed = transport.parse_response(malformed)
            assert parsed == malformed  # Should return as-is when not valid JSON

        # Test valid JSON with duplicate keys (should parse successfully)
        duplicate_key_json = '{"duplicate": 1, "duplicate": 2}'
        parsed = transport.parse_response(duplicate_key_json)
        assert parsed == {"duplicate": 2}  # Should keep last value

    def test_parse_response_with_json_arrays(self, transport):
        """Test parsing JSON array responses."""
        response_data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
        response = json.dumps(response_data)
        parsed = transport.parse_response(response)
        assert parsed == response_data
        assert len(parsed) == 3

    def test_parse_response_with_nested_structures(self, transport):
        """Test parsing deeply nested JSON structures."""
        response_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": [
                            {"item": 1, "details": {"a": 1, "b": 2}},
                            {"item": 2, "details": {"a": 3, "b": 4}},
                        ]
                    }
                }
            }
        }
        response = json.dumps(response_data)
        parsed = transport.parse_response(response)
        assert parsed == response_data
        assert parsed["level1"]["level2"]["level3"]["data"][0]["details"]["a"] == 1

    def test_parse_response_with_number_types(self, transport):
        """Test parsing responses with various number types."""
        response_data = {
            "integer": 42,
            "float": 3.14159,
            "negative": -123,
            "zero": 0,
            "scientific": 1.23e-4,
            "large": 999999999999999999,
        }
        response = json.dumps(response_data)
        parsed = transport.parse_response(response)
        assert parsed == response_data
        assert isinstance(parsed["integer"], int)
        assert isinstance(parsed["float"], float)

    def test_parse_response_with_boolean_and_null(self, transport):
        """Test parsing responses with boolean and null values."""
        response_data = {
            "success": True,
            "failed": False,
            "empty": None,
            "flags": [True, False, None],
        }
        response = json.dumps(response_data)
        parsed = transport.parse_response(response)
        assert parsed == response_data
        assert parsed["success"] is True
        assert parsed["failed"] is False
        assert parsed["empty"] is None

    def test_format_and_parse_roundtrip(self, transport):
        """Test that format_body and parse_response are inverse operations."""
        original_data = {
            "complex": {
                "nested": ["data", "with", {"various": "types"}],
                "numbers": [1, 2.5, -3],
                "booleans": [True, False],
                "null_value": None,
            },
            "unicode": "Test with émojis 🚀 and spëcial chärs",
            "escapes": 'Line 1\nLine 2\tTabbed"Quoted\\',
        }

        # Format then parse
        formatted = transport.format_body(original_data)
        parsed = transport.parse_response(formatted)

        # Should get back the original
        assert parsed == original_data

    def test_format_body_with_large_data(self, transport):
        """Test formatting handles large data structures."""
        # Create a large nested structure
        large_data = {
            "items": [
                {
                    "id": i,
                    "data": f"item_{i}",
                    "metadata": {"index": i, "even": i % 2 == 0},
                }
                for i in range(1000)
            ],
            "summary": {"total": 1000, "description": "A large dataset for testing"},
        }

        formatted = transport.format_body(large_data)

        # Should handle large data without issues
        assert isinstance(formatted, str)
        assert len(formatted) > 10000  # Should be substantial

        # Should still be valid JSON
        parsed = json.loads(formatted)
        assert len(parsed["items"]) == 1000
        assert parsed["summary"]["total"] == 1000
