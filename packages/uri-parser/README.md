# Agent URI Parser

A Python implementation of the `agent://` URI parser according to the ABNF specification in Section 4 of the RFC draft.

## Features

- Complete implementation of the `agent://` URI scheme parsing
- Support for all components including authority, path, query parameters, and fragments
- Support for explicit transport bindings (agent+protocol://)
- Clean and easy-to-use API
- Comprehensive test suite

## Installation

```bash
# From the agent-uri/packages/uri-parser directory
pip install -e .
```

## Usage

### Basic Parsing

```python
from agent_uri.parser import parse_agent_uri

# Parse a basic agent URI
uri = "agent://acme.ai/planning/generate-itinerary"
agent_uri = parse_agent_uri(uri)

print(agent_uri.authority)  # acme.ai
print(agent_uri.path)       # planning/generate-itinerary
```

### Parsing with Transport Protocol

```python
# Parse with explicit transport binding
uri = "agent+https://acme.com/assistants/chatgpt?query=hello"
agent_uri = parse_agent_uri(uri)

print(agent_uri.transport)   # https
print(agent_uri.authority)   # acme.com
print(agent_uri.query)       # {'query': 'hello'}
```

### Creating URIs

```python
from agent_uri.parser import AgentUri

# Create from components
agent_uri = AgentUri(
    transport="wss",
    authority="example.com:8080",
    path="path/to/resource",
    query={"param": "value"},
    fragment="section"
)

print(str(agent_uri))  # agent+wss://example.com:8080/path/to/resource?param=value#section
```

### Validation

```python
from agent_uri.parser import is_valid_agent_uri

is_valid = is_valid_agent_uri("agent://acme.ai/planning")  # True
is_valid = is_valid_agent_uri("http://acme.ai/planning")   # False
```

## API Reference

### `parse_agent_uri(uri: str) -> AgentUri`

Parses an agent:// URI and returns an `AgentUri` object.

### `is_valid_agent_uri(uri: str) -> bool`

Checks if a string is a valid agent:// URI.

### `AgentUri` class

Represents a parsed agent:// URI with properties for all components.

- `scheme`: Always "agent"
- `transport`: Optional transport protocol (e.g., "https", "wss", "local")
- `authority`: The authority component (e.g., "acme.ai:8080")
- `path`: The path component
- `query`: Dictionary of query parameters
- `fragment`: Optional fragment
- `userinfo`: Optional userinfo from the authority
- `host`: Host portion of the authority
- `port`: Optional port number

#### Methods

- `to_string()`: Converts the URI back to a string
- `to_dict()`: Converts the URI to a dictionary representation

## Running Tests

```bash
# From the agent-uri/packages/uri-parser directory
python -m unittest discover tests
