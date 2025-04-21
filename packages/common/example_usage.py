#!/usr/bin/env python
"""
Example usage of the agent:// protocol error handling framework.

This script demonstrates how to use the error handling framework
in various scenarios.
"""

import json
import sys

from agent_common.error.models import (
    AgentError,
    AgentProblemDetail,
    ErrorCategory,
    create_problem_detail,
    problem_from_exception
)
from agent_common.error.transport import (
    format_for_http,
    format_for_websocket,
    format_for_local,
    parse_http_error,
    parse_websocket_error,
    parse_local_error
)


def example_creating_errors():
    """Example: Creating error responses."""
    print("\n=== Creating Error Responses ===\n")
    
    # Method 1: Create directly using AgentProblemDetail
    problem1 = AgentProblemDetail(
        type="https://agent-uri.org/errors/capability-not-found",
        title="Capability Not Found",
        status=404,
        detail="The requested capability was not found.",
        instance="/planner/generate-itinerary"
    )
    print("Method 1 (Direct):", json.dumps(problem1.to_dict(), indent=2))
    
    # Method 2: Create using the create_problem_detail helper
    problem2 = create_problem_detail(
        category=ErrorCategory.INVALID_INPUT,
        detail="The city parameter is required.",
        instance="/planner/generate-itinerary?city=",
        extensions={"requiredFields": ["city"]}
    )
    print("\nMethod 2 (Helper):", json.dumps(problem2.to_dict(), indent=2))
    
    # Method 3: Create from exception
    try:
        raise AgentError(
            message="Authentication failed.",
            category=ErrorCategory.AUTHENTICATION_FAILED
        )
    except AgentError as e:
        problem3 = e.to_problem_detail()
        print("\nMethod 3 (From Exception):", json.dumps(problem3.to_dict(), indent=2))
    
    # Method 4: Create from a standard Python exception
    try:
        # Some operation that fails
        raise ValueError("Invalid value")
    except Exception as e:
        problem4 = problem_from_exception(e)
        print("\nMethod 4 (From std Exception):", json.dumps(problem4.to_dict(), indent=2))


def example_transport_formatting():
    """Example: Formatting errors for different transports."""
    print("\n=== Formatting for Different Transports ===\n")
    
    problem = create_problem_detail(
        category=ErrorCategory.NOT_FOUND,
        detail="The requested resource was not found.",
        instance="/resources/123"
    )
    
    # Format for HTTP
    headers, status, body = format_for_http(problem)
    print("HTTP Response:")
    print(f"  Status: {status}")
    print(f"  Headers: {headers}")
    print(f"  Body: {json.dumps(body, indent=2)}")
    
    # Format for WebSocket
    ws_message = format_for_websocket(problem)
    print("\nWebSocket Message:")
    print(f"  {json.dumps(ws_message, indent=2)}")
    
    # Format for Local transport
    local_message = format_for_local(problem)
    print("\nLocal Transport Message:")
    print(f"  {json.dumps(local_message, indent=2)}")


def example_transport_parsing():
    """Example: Parsing errors from different transports."""
    print("\n=== Parsing Errors from Different Transports ===\n")
    
    # Create a sample error response
    original_problem = create_problem_detail(
        category=ErrorCategory.FORBIDDEN,
        detail="You do not have permission to access this resource.",
        instance="/resources/secret"
    )
    
    # HTTP
    _, status, body = format_for_http(original_problem)
    headers = {"Content-Type": "application/problem+json"}
    
    # Parse from HTTP
    parsed_http = parse_http_error(status, body, headers)
    print("Parsed from HTTP:")
    print(f"  Type: {parsed_http.type}")
    print(f"  Title: {parsed_http.title}")
    print(f"  Status: {parsed_http.status}")
    print(f"  Detail: {parsed_http.detail}")
    
    # WebSocket
    ws_message = format_for_websocket(original_problem)
    
    # Parse from WebSocket
    parsed_ws = parse_websocket_error(ws_message)
    print("\nParsed from WebSocket:")
    print(f"  Type: {parsed_ws.type}")
    print(f"  Title: {parsed_ws.title}")
    print(f"  Status: {parsed_ws.status}")
    print(f"  Detail: {parsed_ws.detail}")
    
    # Local
    local_message = format_for_local(original_problem)
    
    # Parse from Local
    parsed_local = parse_local_error(local_message)
    print("\nParsed from Local:")
    print(f"  Type: {parsed_local.type}")
    print(f"  Title: {parsed_local.title}")
    print(f"  Status: {parsed_local.status}")
    print(f"  Detail: {parsed_local.detail}")


def example_error_handling():
    """Example: Error handling in application code."""
    print("\n=== Error Handling in Application Code ===\n")
    
    # Client-side error handling
    def client_example(url, params):
        """Simulate a client making a request and handling errors."""
        print("Client making request to:", url)
        
        # Simulate a 404 error response
        status_code = 404
        response_body = {
            "type": "https://agent-uri.org/errors/capability-not-found",
            "title": "Capability Not Found",
            "status": 404,
            "detail": "The requested capability 'generate-itinerary' was not found.",
            "instance": "/planner/generate-itinerary"
        }
        headers = {"Content-Type": "application/problem+json"}
        
        # Parse the error
        problem = parse_http_error(status_code, response_body, headers)
        
        if problem:
            print(f"Request failed: {problem.status} {problem.title}")
            print(f"Details: {problem.detail}")
            print("Handling the error appropriately...")
            if problem.status == 404:
                print("  - Could suggest alternative capabilities")
            elif problem.status == 401 or problem.status == 403:
                print("  - Could prompt for authentication")
            return None
        
        # Process successful response
        return {"result": "success"}
    
    # Server-side error handling
    def server_example(request_path, request_params):
        """Simulate a server handling a request and generating errors."""
        print("\nServer handling request for:", request_path)
        
        try:
            # Check for missing parameters
            if not request_params.get("city"):
                raise AgentError(
                    message="The city parameter is required.",
                    category=ErrorCategory.INVALID_INPUT,
                    instance=request_path
                )
            
            # Simulate capability not found
            if "nonexistent" in request_path:
                raise AgentError(
                    message="The requested capability does not exist.",
                    category=ErrorCategory.CAPABILITY_NOT_FOUND,
                    instance=request_path
                )
            
            # Simulate successful processing
            print("Successfully processed request")
            return {"result": "Itinerary generated successfully"}
            
        except AgentError as e:
            # Convert to problem detail
            problem = e.to_problem_detail()
            headers, status, body = format_for_http(problem)
            
            print(f"Error occurred: {status} {e.category.name}")
            print(f"Response: {json.dumps(body, indent=2)}")
            return None
            
        except Exception as e:
            # Handle unexpected errors
            problem = create_problem_detail(
                category=ErrorCategory.INTERNAL_ERROR,
                detail=str(e),
                instance=request_path
            )
            headers, status, body = format_for_http(problem)
            
            print(f"Unexpected error: {status} Internal Server Error")
            print(f"Response: {json.dumps(body, indent=2)}")
            return None
    
    # Example client-side code
    client_example("https://planner.acme.ai/generate-itinerary", {"city": "Paris"})
    
    # Example server-side code
    server_example("/planner/generate-itinerary", {})  # Missing parameter
    server_example("/planner/nonexistent-capability", {"city": "Paris"})  # Non-existent capability
    server_example("/planner/generate-itinerary", {"city": "Paris"})  # Success case


def main():
    """Run the examples."""
    example_creating_errors()
    example_transport_formatting()
    example_transport_parsing()
    example_error_handling()


if __name__ == "__main__":
    main()
