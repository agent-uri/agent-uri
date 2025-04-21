# Agent Common

Common utilities for the agent:// protocol implementation.

## Overview

This package provides shared functionality used across different agent:// protocol packages, including:

- Error handling framework with RFC 7807 support
- Common utility functions and models

## Error Handling Framework

The error handling framework implements RFC 7807 ("Problem Details for HTTP APIs") to provide a standardized way of expressing errors across different transport bindings. This enables consistent error handling across the entire agent:// protocol ecosystem.

### Features

- Standardized error representation using RFC 7807 `application/problem+json` format
- Support for different transport bindings (HTTP, WebSocket, Local)
- Helper functions for creating and parsing error responses
- Integration with Python's exception system

### Usage Examples

#### Creating an Error Response

```python
from agent_common.error.models import AgentError, ErrorCategory

# Raise an error with structured information
try:
    # Some operation that fails
    raise AgentError(
        message="The requested capability was not found.",
        category=ErrorCategory.CAPABILITY_NOT_FOUND,
        instance="/planner/generate-itinerary"
    )
except AgentError as e:
    # Convert to problem detail
    problem = e.to_problem_detail()
    
    # Use in appropriate transport
    from agent_common.error.transport import format_for_http
    headers, status, body = format_for_http(problem)
    # Return the HTTP response with these values
```

#### HTTP Server Error Handling

```python
from agent_common.error.models import AgentError, ErrorCategory, create_problem_detail
from agent_common.error.transport import format_for_http

def handle_request(request):
    try:
        # Process request
        result = process_request(request)
        return success_response(result)
    except AgentError as e:
        # Convert error to HTTP response
        headers, status, body = format_for_http(e.to_problem_detail())
        return error_response(headers, status, body)
    except Exception as e:
        # Handle unexpected errors
        problem = create_problem_detail(
            category=ErrorCategory.INTERNAL_ERROR,
            detail=str(e)
        )
        headers, status, body = format_for_http(problem)
        return error_response(headers, status, body)
```

#### HTTP Client Error Handling

```python
from agent_common.error.transport import parse_http_error

def make_request(url, params):
    response = http_client.get(url, params=params)
    
    # Check for errors
    problem = parse_http_error(
        response.status_code, 
        response.json() if response.headers.get('Content-Type') == 'application/json' else response.text,
        response.headers
    )
    
    if problem:
        # Handle the error appropriately
        if problem.status == 404:
            # Handle not found
            pass
        elif problem.status == 401:
            # Handle unauthorized
            pass
        # ...
        raise Exception(f"Request failed: {problem.title} - {problem.detail}")
    
    # Process successful response
    return response.json()
```

#### WebSocket Error Handling

```python
from agent_common.error.transport import parse_websocket_error, format_for_websocket
from agent_common.error.models import create_problem_detail, ErrorCategory

# Sending an error response
def send_error(websocket, error_category, message, instance=None):
    problem = create_problem_detail(
        category=error_category,
        detail=message,
        instance=instance
    )
    
    error_response = format_for_websocket(problem)
    websocket.send(json.dumps(error_response))

# Receiving and handling errors
def on_message(websocket, message):
    try:
        data = json.loads(message)
        
        # Check for errors
        problem = parse_websocket_error(data)
        if problem:
            # Handle error
            print(f"Error: {problem.title} - {problem.detail}")
            return
        
        # Process normal message
        process_message(data)
        
    except json.JSONDecodeError:
        print("Invalid JSON message")
```

## Installation

### For Development

```bash
# Clone the repository
git clone https://github.com/agent-uri/agent-uri.git
cd agent-uri/packages/common

# Install in development mode
python install_dev.py
```

### For Use in Other Projects

```bash
pip install git+https://github.com/agent-uri/agent-uri.git#subdirectory=packages/common
```

## Running Tests

```bash
# From the packages/common directory
python run_tests.py
```

## License

[TBD]
