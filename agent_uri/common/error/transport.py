"""
Transport binding utilities for the error handling framework.

This module provides functions for formatting and parsing error responses
across different transport bindings (HTTP, WebSocket, Local, etc.).
"""

import json
from typing import Any, Dict, Optional, Tuple, Union

from .models import AgentError, AgentProblemDetail


def format_for_http(
    problem: AgentProblemDetail, headers: Optional[Dict[str, str]] = None
) -> Tuple[Dict[str, str], int, Dict[str, Any]]:
    """
    Format a problem detail for HTTP responses.

    Args:
        problem: The problem detail to format
        headers: Optional additional headers to include in the response

    Returns:
        A tuple of (headers, status_code, response_body)
    """
    all_headers = {"Content-Type": "application/problem+json"}

    if headers:
        all_headers.update(headers)

    return all_headers, problem.status, problem.to_dict()


def format_for_websocket(problem: AgentProblemDetail) -> Dict[str, Any]:
    """
    Format a problem detail for WebSocket responses.

    Args:
        problem: The problem detail to format

    Returns:
        A JSON-serializable dict representing the error
    """
    return {"error": problem.to_dict()}


def format_for_local(problem: AgentProblemDetail) -> Dict[str, Any]:
    """
    Format a problem detail for local transport (e.g., IPC) responses.

    Args:
        problem: The problem detail to format

    Returns:
        A JSON-serializable dict representing the error
    """
    return {"error": problem.to_dict()}


def parse_http_error(
    status_code: int,
    body: Union[str, Dict[str, Any]],
    headers: Optional[Dict[str, str]] = None,
) -> Optional[AgentProblemDetail]:
    """
    Parse an HTTP error response into a problem detail.

    Args:
        status_code: The HTTP status code
        body: The response body, either as a string or parsed JSON
        headers: The response headers

    Returns:
        An AgentProblemDetail or None if not an error or couldn't be parsed
    """
    if status_code < 400:
        return None

    content_type = headers.get("Content-Type", "") if headers else ""

    # If it's a problem+json, parse accordingly
    if "application/problem+json" in content_type:
        if isinstance(body, str):
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return _create_fallback_problem(status_code, body)
        else:
            data = body

        return AgentProblemDetail(
            type=data.get("type", f"https://agent-uri.org/errors/{status_code}"),
            title=data.get("title", "Unknown Error"),
            status=data.get("status", status_code),
            detail=data.get("detail"),
            instance=data.get("instance"),
            extensions={
                k: v
                for k, v in data.items()
                if k not in ["type", "title", "status", "detail", "instance"]
            },
        )

    # Handle plain JSON errors
    elif "application/json" in content_type:
        if isinstance(body, str):
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return _create_fallback_problem(status_code, body)
        else:
            data = body

        # Try to extract error message from common JSON error patterns
        detail = None
        if "error" in data and isinstance(data["error"], str):
            detail = data["error"]
        elif "message" in data:
            detail = data["message"]
        elif "detail" in data:
            detail = data["detail"]

        return AgentProblemDetail(
            type=f"https://agent-uri.org/errors/{status_code}",
            title=_status_to_title(status_code),
            status=status_code,
            detail=detail,
            extensions=data,
        )

    # Handle text/plain or other content types
    else:
        return _create_fallback_problem(status_code, body)


def parse_websocket_error(
    data: Union[str, Dict[str, Any]],
) -> Optional[AgentProblemDetail]:
    """
    Parse a WebSocket error message into a problem detail.

    Args:
        data: The WebSocket message data

    Returns:
        An AgentProblemDetail or None if not an error or couldn't be parsed
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None

    if not isinstance(data, dict):
        return None

    # Check if it's an error message
    if "error" in data:
        error_data = data["error"]

        if isinstance(error_data, dict):
            # It's possibly a problem detail
            return AgentProblemDetail(
                type=error_data.get("type", "https://agent-uri.org/errors/unknown"),
                title=error_data.get("title", "Unknown Error"),
                status=error_data.get("status", 500),
                detail=error_data.get("detail"),
                instance=error_data.get("instance"),
                extensions={
                    k: v
                    for k, v in error_data.items()
                    if k not in ["type", "title", "status", "detail", "instance"]
                },
            )
        elif isinstance(error_data, str):
            # It's a simple error message
            return AgentProblemDetail(
                type="https://agent-uri.org/errors/unknown",
                title="WebSocket Error",
                status=500,
                detail=error_data,
            )

    return None


def parse_local_error(data: Any) -> Optional[AgentProblemDetail]:
    """
    Parse a local transport error into a problem detail.

    Args:
        data: The error data from the local transport

    Returns:
        An AgentProblemDetail or None if not an error or couldn't be parsed
    """
    # Handle direct problem detail or exception
    if isinstance(data, AgentProblemDetail):
        return data
    elif isinstance(data, AgentError):
        return data.to_problem_detail()

    # Handle dictionary format
    if isinstance(data, dict) and "error" in data:
        error_data = data["error"]

        if isinstance(error_data, dict):
            # It looks like a problem detail
            return AgentProblemDetail(
                type=error_data.get("type", "https://agent-uri.org/errors/unknown"),
                title=error_data.get("title", "Unknown Error"),
                status=error_data.get("status", 500),
                detail=error_data.get("detail"),
                instance=error_data.get("instance"),
                extensions={
                    k: v
                    for k, v in error_data.items()
                    if k not in ["type", "title", "status", "detail", "instance"]
                },
            )

    # If it's a generic exception or string
    if isinstance(data, Exception):
        return AgentProblemDetail(
            type="https://agent-uri.org/errors/unknown",
            title="Local Error",
            status=500,
            detail=str(data),
        )

    return None


def _create_fallback_problem(status_code: int, body: Any) -> AgentProblemDetail:
    """Create a fallback problem detail from a non-structured error response."""
    return AgentProblemDetail(
        type=f"https://agent-uri.org/errors/{status_code}",
        title=_status_to_title(status_code),
        status=status_code,
        detail=str(body) if body else None,
    )


def _status_to_title(status_code: int) -> str:
    """Convert an HTTP status code to a human-readable title."""
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        408: "Request Timeout",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }
    return titles.get(status_code, f"Error {status_code}")
