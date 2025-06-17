"""
Error models for the agent:// protocol error handling framework.

This module implements RFC 7807 (Problem Details for HTTP APIs) compatible
error structures that can be used across different transport bindings.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional, Union


class ErrorCategory(Enum):
    """Standard error categories for agent:// protocol."""

    CAPABILITY_NOT_FOUND = auto()
    INVALID_INPUT = auto()
    AMBIGUOUS_RESPONSE = auto()
    TIMEOUT = auto()
    PERMISSION_DENIED = auto()
    AUTHENTICATION_FAILED = auto()
    UNAUTHORIZED = auto()
    FORBIDDEN = auto()
    NOT_FOUND = auto()
    CONFLICT = auto()
    TOO_MANY_REQUESTS = auto()
    INTERNAL_ERROR = auto()
    SERVICE_UNAVAILABLE = auto()
    BAD_REQUEST = auto()
    VALIDATION_ERROR = auto()


# Mapping from ErrorCategory to HTTP status codes
HTTP_STATUS_CODES = {
    ErrorCategory.CAPABILITY_NOT_FOUND: 404,
    ErrorCategory.INVALID_INPUT: 400,
    ErrorCategory.AMBIGUOUS_RESPONSE: 300,
    ErrorCategory.TIMEOUT: 408,
    ErrorCategory.PERMISSION_DENIED: 403,
    ErrorCategory.AUTHENTICATION_FAILED: 401,
    ErrorCategory.UNAUTHORIZED: 401,
    ErrorCategory.FORBIDDEN: 403,
    ErrorCategory.NOT_FOUND: 404,
    ErrorCategory.CONFLICT: 409,
    ErrorCategory.TOO_MANY_REQUESTS: 429,
    ErrorCategory.INTERNAL_ERROR: 500,
    ErrorCategory.SERVICE_UNAVAILABLE: 503,
    ErrorCategory.BAD_REQUEST: 400,
    ErrorCategory.VALIDATION_ERROR: 422,
}


@dataclass
class AgentProblemDetail:
    """
    RFC 7807 Problem Details for HTTP APIs implementation.

    This class provides a structured way to represent errors that can be
    serialized across different transport bindings.
    """

    type: str
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None
    extensions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the problem detail to a dictionary for serialization."""
        result = {"type": self.type, "title": self.title, "status": self.status}

        if self.detail is not None:
            result["detail"] = self.detail

        if self.instance is not None:
            result["instance"] = self.instance

        # Add any extension fields
        result.update(self.extensions)

        return result


class AgentError(Exception):
    """
    Base class for all agent:// protocol errors.

    This error class is designed to carry structured error information
    that can be converted to/from RFC 7807 problem details.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL_ERROR,
        type_uri: Optional[str] = None,
        instance: Optional[str] = None,
        status: Optional[int] = None,
        extensions: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a new AgentError.

        Args:
            message: Human-readable error message
            category: The error category
            type_uri: URI reference that identifies the problem type
            instance: URI reference that identifies the specific occurrence
                of the problem
            status: HTTP status code (derived from category if not provided)
            extensions: Additional fields to include in the problem detail
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.type_uri = (
            type_uri or f"https://agent-uri.org/errors/{category.name.lower()}"
        )
        self.instance = instance
        self.status = status or HTTP_STATUS_CODES.get(category, 500)
        self.extensions = extensions or {}

    def to_problem_detail(self) -> AgentProblemDetail:
        """Convert this error to an RFC 7807 problem detail."""
        return AgentProblemDetail(
            type=self.type_uri,
            title=self.category.name.replace("_", " ").title(),
            status=self.status,
            detail=self.message,
            instance=self.instance,
            extensions=self.extensions,
        )


def create_problem_detail(
    category: ErrorCategory,
    detail: str,
    type_uri: Optional[str] = None,
    instance: Optional[str] = None,
    status: Optional[int] = None,
    extensions: Optional[Dict[str, Any]] = None,
) -> AgentProblemDetail:
    """
    Create an RFC 7807 problem detail from parameters.

    Args:
        category: The error category
        detail: A human-readable explanation of the error
        type_uri: URI reference that identifies the problem type
        instance: URI reference that identifies the specific occurrence of the problem
        status: HTTP status code (derived from category if not provided)
        extensions: Additional fields to include in the problem detail

    Returns:
        An AgentProblemDetail instance
    """
    type_uri = type_uri or f"https://agent-uri.org/errors/{category.name.lower()}"
    status = status or HTTP_STATUS_CODES.get(category, 500)
    title = category.name.replace("_", " ").title()

    return AgentProblemDetail(
        type=type_uri,
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        extensions=extensions or {},
    )


def problem_from_exception(
    exc: Union[AgentError, Exception],
    instance: Optional[str] = None,
    default_type: str = "https://agent-uri.org/errors/unknown",
) -> AgentProblemDetail:
    """
    Convert an exception to an RFC 7807 problem detail.

    Args:
        exc: The exception to convert
        instance: URI reference to include in the problem detail
        default_type: Default type URI for non-AgentError exceptions

    Returns:
        An AgentProblemDetail instance
    """
    if isinstance(exc, AgentError):
        return exc.to_problem_detail()

    # Handle generic exceptions
    return AgentProblemDetail(
        type=default_type,
        title="Internal Server Error",
        status=500,
        detail=str(exc),
        instance=instance,
    )
