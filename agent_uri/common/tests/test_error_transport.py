"""
Tests for the transport binding utilities in the error handling framework.
"""

import json
import unittest

from ..error.models import AgentProblemDetail, ErrorCategory, create_problem_detail
from ..error.transport import (
    format_for_http,
    format_for_local,
    format_for_websocket,
    parse_http_error,
    parse_local_error,
    parse_websocket_error,
)


class TestErrorTransport(unittest.TestCase):
    """Test cases for the transport utilities in the error handling framework."""

    def setUp(self):
        """Set up test fixtures."""
        self.problem = AgentProblemDetail(
            type="https://agent-uri.org/errors/capability-not-found",
            title="Capability Not Found",
            status=404,
            detail="The requested capability was not found.",
            instance="/planner/generate-itinerary",
        )

    def test_format_for_http(self):
        """Test formatting a problem detail for HTTP responses."""
        headers, status, body = format_for_http(self.problem)

        self.assertEqual(headers["Content-Type"], "application/problem+json")
        self.assertEqual(status, 404)
        self.assertEqual(
            body["type"], "https://agent-uri.org/errors/capability-not-found"
        )
        self.assertEqual(body["title"], "Capability Not Found")
        self.assertEqual(body["status"], 404)
        self.assertEqual(body["detail"], "The requested capability was not found.")
        self.assertEqual(body["instance"], "/planner/generate-itinerary")

        # Test with additional headers
        headers, status, body = format_for_http(self.problem, {"X-Request-ID": "12345"})
        self.assertEqual(headers["Content-Type"], "application/problem+json")
        self.assertEqual(headers["X-Request-ID"], "12345")

    def test_format_for_websocket(self):
        """Test formatting a problem detail for WebSocket responses."""
        message = format_for_websocket(self.problem)

        self.assertIn("error", message)
        error = message["error"]
        self.assertEqual(
            error["type"], "https://agent-uri.org/errors/capability-not-found"
        )
        self.assertEqual(error["title"], "Capability Not Found")
        self.assertEqual(error["status"], 404)
        self.assertEqual(error["detail"], "The requested capability was not found.")
        self.assertEqual(error["instance"], "/planner/generate-itinerary")

    def test_format_for_local(self):
        """Test formatting a problem detail for local transport."""
        message = format_for_local(self.problem)

        self.assertIn("error", message)
        error = message["error"]
        self.assertEqual(
            error["type"], "https://agent-uri.org/errors/capability-not-found"
        )
        self.assertEqual(error["title"], "Capability Not Found")
        self.assertEqual(error["status"], 404)
        self.assertEqual(error["detail"], "The requested capability was not found.")
        self.assertEqual(error["instance"], "/planner/generate-itinerary")

    def test_parse_http_error_with_problem_json(self):
        """Test parsing an HTTP error with problem+json content type."""
        body = {
            "type": "https://agent-uri.org/errors/capability-not-found",
            "title": "Capability Not Found",
            "status": 404,
            "detail": "The requested capability was not found.",
            "instance": "/planner/generate-itinerary",
        }

        headers = {"Content-Type": "application/problem+json"}

        problem = parse_http_error(404, body, headers)

        self.assertIsNotNone(problem)
        self.assertEqual(
            problem.type, "https://agent-uri.org/errors/capability-not-found"
        )
        self.assertEqual(problem.title, "Capability Not Found")
        self.assertEqual(problem.status, 404)
        self.assertEqual(problem.detail, "The requested capability was not found.")
        self.assertEqual(problem.instance, "/planner/generate-itinerary")

        # Test with string body
        body_str = json.dumps(body)
        problem = parse_http_error(404, body_str, headers)

        self.assertIsNotNone(problem)
        self.assertEqual(
            problem.type, "https://agent-uri.org/errors/capability-not-found"
        )

        # Test with invalid JSON
        problem = parse_http_error(404, "Invalid JSON", headers)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.status, 404)
        self.assertEqual(problem.detail, "Invalid JSON")

    def test_parse_http_error_with_json(self):
        """Test parsing an HTTP error with application/json content type."""
        # Test common JSON error patterns

        # Pattern 1: {"error": "message"}
        body = {"error": "Authentication failed"}
        headers = {"Content-Type": "application/json"}

        problem = parse_http_error(401, body, headers)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.status, 401)
        self.assertEqual(problem.detail, "Authentication failed")

        # Pattern 2: {"message": "error message"}
        body = {"message": "Invalid input parameter"}

        problem = parse_http_error(400, body, headers)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.status, 400)
        self.assertEqual(problem.detail, "Invalid input parameter")

        # Pattern 3: {"detail": "error detail"}
        body = {"detail": "Resource not found"}

        problem = parse_http_error(404, body, headers)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.status, 404)
        self.assertEqual(problem.detail, "Resource not found")

    def test_parse_http_error_with_text(self):
        """Test parsing an HTTP error with text/plain content type."""
        body = "Internal server error occurred"
        headers = {"Content-Type": "text/plain"}

        problem = parse_http_error(500, body, headers)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.type, "https://agent-uri.org/errors/500")
        self.assertEqual(problem.title, "Internal Server Error")
        self.assertEqual(problem.status, 500)
        self.assertEqual(problem.detail, "Internal server error occurred")

    def test_parse_http_error_with_non_error_status(self):
        """Test parsing a non-error HTTP response."""
        body = {"result": "success"}
        headers = {"Content-Type": "application/json"}

        problem = parse_http_error(200, body, headers)

        self.assertIsNone(problem)

    def test_parse_websocket_error(self):
        """Test parsing a WebSocket error message."""
        # Test structured error message
        data = {
            "error": {
                "type": "https://agent-uri.org/errors/invalid-input",
                "title": "Invalid Input",
                "status": 400,
                "detail": "The input was invalid.",
            }
        }

        problem = parse_websocket_error(data)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.type, "https://agent-uri.org/errors/invalid-input")
        self.assertEqual(problem.title, "Invalid Input")
        self.assertEqual(problem.status, 400)
        self.assertEqual(problem.detail, "The input was invalid.")

        # Test simple error message
        data = {"error": "Connection failed"}

        problem = parse_websocket_error(data)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.title, "WebSocket Error")
        self.assertEqual(problem.detail, "Connection failed")

        # Test JSON string
        data_str = json.dumps({"error": "Authentication failed"})

        problem = parse_websocket_error(data_str)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.detail, "Authentication failed")

        # Test non-error message
        data = {"result": "success"}

        problem = parse_websocket_error(data)

        self.assertIsNone(problem)

        # Test invalid JSON
        problem = parse_websocket_error("Invalid JSON")

        self.assertIsNone(problem)

    def test_parse_local_error(self):
        """Test parsing a local transport error."""
        # Test with problem detail
        original_problem = create_problem_detail(
            category=ErrorCategory.TIMEOUT,
            detail="Operation timed out.",
            instance="/planner/generate-itinerary",
        )

        problem = parse_local_error(original_problem)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.type, "https://agent-uri.org/errors/timeout")
        self.assertEqual(problem.title, "Timeout")
        self.assertEqual(problem.status, 408)
        self.assertEqual(problem.detail, "Operation timed out.")

        # Test with dictionary error
        data = {
            "error": {
                "type": "https://agent-uri.org/errors/invalid-input",
                "title": "Invalid Input",
                "status": 400,
                "detail": "The input was invalid.",
            }
        }

        problem = parse_local_error(data)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.type, "https://agent-uri.org/errors/invalid-input")
        self.assertEqual(problem.title, "Invalid Input")
        self.assertEqual(problem.status, 400)
        self.assertEqual(problem.detail, "The input was invalid.")

        # Test with Exception
        exc = ValueError("Invalid value")

        problem = parse_local_error(exc)

        self.assertIsNotNone(problem)
        self.assertEqual(problem.title, "Local Error")
        self.assertEqual(problem.detail, "Invalid value")

        # Test with non-error data
        data = {"result": "success"}

        problem = parse_local_error(data)

        self.assertIsNone(problem)


if __name__ == "__main__":
    unittest.main()
