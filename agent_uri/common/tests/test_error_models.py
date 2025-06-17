"""
Tests for the error models module in the agent:// protocol error handling framework.
"""

import unittest

from ..error.models import (
    AgentError,
    AgentProblemDetail,
    ErrorCategory,
    create_problem_detail,
    problem_from_exception,
)


class TestErrorModels(unittest.TestCase):
    """Test cases for the error models in the error handling framework."""

    def test_agent_problem_detail_creation(self):
        """Test creating and serializing a problem detail."""
        problem = AgentProblemDetail(
            type="https://agent-uri.org/errors/capability-not-found",
            title="Capability Not Found",
            status=404,
            detail="The requested capability was not found.",
            instance="/planner/generate-itinerary",
        )

        # Test to_dict method
        problem_dict = problem.to_dict()

        self.assertEqual(
            problem_dict["type"], "https://agent-uri.org/errors/capability-not-found"
        )
        self.assertEqual(problem_dict["title"], "Capability Not Found")
        self.assertEqual(problem_dict["status"], 404)
        self.assertEqual(
            problem_dict["detail"], "The requested capability was not found."
        )
        self.assertEqual(problem_dict["instance"], "/planner/generate-itinerary")

    def test_agent_problem_detail_with_extensions(self):
        """Test creating a problem detail with extension fields."""
        problem = AgentProblemDetail(
            type="https://agent-uri.org/errors/invalid-input",
            title="Invalid Input",
            status=400,
            detail="The input was invalid.",
            extensions={
                "field": "city",
                "reason": "City name cannot be empty",
                "inputValue": "",
            },
        )

        problem_dict = problem.to_dict()

        self.assertEqual(problem_dict["field"], "city")
        self.assertEqual(problem_dict["reason"], "City name cannot be empty")
        self.assertEqual(problem_dict["inputValue"], "")

    def test_agent_error_creation(self):
        """Test creating an AgentError and converting it to a problem detail."""
        error = AgentError(
            message="The requested capability was not found.",
            category=ErrorCategory.CAPABILITY_NOT_FOUND,
            instance="/planner/generate-itinerary",
        )

        self.assertEqual(error.message, "The requested capability was not found.")
        self.assertEqual(error.category, ErrorCategory.CAPABILITY_NOT_FOUND)
        self.assertEqual(error.instance, "/planner/generate-itinerary")
        self.assertEqual(error.status, 404)  # Should use the HTTP status mapping

        # Test conversion to problem detail
        problem = error.to_problem_detail()
        self.assertEqual(
            problem.type, "https://agent-uri.org/errors/capability_not_found"
        )
        self.assertEqual(problem.title, "Capability Not Found")
        self.assertEqual(problem.status, 404)
        self.assertEqual(problem.detail, "The requested capability was not found.")
        self.assertEqual(problem.instance, "/planner/generate-itinerary")

    def test_create_problem_detail_helper(self):
        """Test the create_problem_detail helper function."""
        problem = create_problem_detail(
            category=ErrorCategory.INVALID_INPUT,
            detail="The input was invalid.",
            instance="/planner/generate-itinerary",
            extensions={"field": "city"},
        )

        self.assertEqual(problem.type, "https://agent-uri.org/errors/invalid_input")
        self.assertEqual(problem.title, "Invalid Input")
        self.assertEqual(problem.status, 400)
        self.assertEqual(problem.detail, "The input was invalid.")
        self.assertEqual(problem.instance, "/planner/generate-itinerary")
        self.assertEqual(problem.extensions["field"], "city")

    def test_problem_from_exception_with_agent_error(self):
        """Test converting an AgentError to a problem detail."""
        error = AgentError(
            message="Authentication failed.",
            category=ErrorCategory.AUTHENTICATION_FAILED,
        )

        problem = problem_from_exception(error)

        self.assertEqual(
            problem.type, "https://agent-uri.org/errors/authentication_failed"
        )
        self.assertEqual(problem.title, "Authentication Failed")
        self.assertEqual(problem.status, 401)
        self.assertEqual(problem.detail, "Authentication failed.")

    def test_problem_from_exception_with_generic_exception(self):
        """Test converting a generic Exception to a problem detail."""
        error = ValueError("Invalid value")

        problem = problem_from_exception(error)

        self.assertEqual(problem.type, "https://agent-uri.org/errors/unknown")
        self.assertEqual(problem.title, "Internal Server Error")
        self.assertEqual(problem.status, 500)
        self.assertEqual(problem.detail, "Invalid value")


if __name__ == "__main__":
    unittest.main()
