"""
Error handling framework for agent:// protocol.

This module provides a standardized error handling system that implements
RFC 7807 (Problem Details for HTTP APIs) for structured error responses
across different transport bindings.
"""

from .models import (
    AgentError,
    AgentProblemDetail,
    ErrorCategory,
    create_problem_detail,
    problem_from_exception,
)
from .transport import (
    format_for_http,
    format_for_local,
    format_for_websocket,
    parse_http_error,
    parse_local_error,
    parse_websocket_error,
)

__all__ = [
    "AgentError",
    "AgentProblemDetail",
    "ErrorCategory",
    "create_problem_detail",
    "problem_from_exception",
    "format_for_http",
    "format_for_websocket",
    "format_for_local",
    "parse_http_error",
    "parse_websocket_error",
    "parse_local_error",
]
