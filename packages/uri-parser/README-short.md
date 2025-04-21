# Agent URI Parser

This package provides a complete implementation of the `agent://` URI parser according to the ABNF specification in Section 4 of the RFC draft. 

## Features

- Parses `agent://` URIs with support for all components (authority, path, query, fragment)
- Handles explicit transport bindings (`agent+protocol://`)
- Supports userinfo, host, and port in the authority component
- Provides round-trip functionality (parse -> modify -> stringify)
- Comprehensive test suite covering all aspects of the specification

## Installation

```bash
# Local development installation
cd agent-uri/packages/uri-parser
pip install -e .
```

## Basic Usage

```python
from agent_uri.parser import parse_agent_uri, AgentUri

# Parse an agent URI
uri = "agent://acme.ai/planning/generate-itinerary?city=Paris"
agent_uri = parse_agent_uri(uri)

print(agent_uri.authority)  # acme.ai
print(agent_uri.path)       # planning/generate-itinerary
print(agent_uri.query)      # {'city': 'Paris'}

# Round-trip
print(str(agent_uri))  # agent://acme.ai/planning/generate-itinerary?city=Paris

# Create from components
new_uri = AgentUri(
    transport="https",
    authority="example.com",
    path="assistant",
    query={"text": "Hello world"}
)
print(str(new_uri))  # agent+https://example.com/assistant?text=Hello%20world
```

## Running Tests

```bash
# Run tests using pytest
cd agent-uri/packages/uri-parser
python -m pytest -xvs tests/test_parser.py
```

See `example_usage.py` for more detailed examples.
