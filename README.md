# Agent URI Reference Implementation

[![Test Coverage](https://img.shields.io/badge/coverage-66%25-yellow.svg)](https://github.com/agent-uri/agent-uri/actions)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](LICENSE)
[![CI Status](https://github.com/agent-uri/agent-uri/actions/workflows/test-and-quality-checks.yml/badge.svg)](https://github.com/agent-uri/agent-uri/actions/workflows/test-and-quality-checks.yml)
[![Security](https://img.shields.io/badge/security-bandit-informational.svg)](https://github.com/agent-uri/agent-uri/actions)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This repository contains a reference implementation of the `agent://` protocol as defined in the [protocol specification](docs/rfc/draft-narvaneni-agent-uri-00.md).

## Overview

The `agent://` protocol is a URI-based framework for addressing, invoking, and interoperating with autonomous and semi-autonomous software agents. It introduces a layered architecture that supports minimal implementations (addressing and transport) and extensible features (capability discovery, contracts, orchestration).

This reference implementation provides a complete implementation of the protocol, including:

- URI parsing and validation
- Agent descriptor handling
- Resolution framework
- Transport bindings (HTTPS, WebSocket, Local)
- Security implementations
- Client and server SDKs
- Integration with other protocols (Agent2Agent, MCP)
- Example implementations and tools

## Architecture

The implementation follows a modular, layered architecture:

```
agent-uri/
├── README.md                    # Project overview, setup instructions
├── pyproject.toml               # Modern Poetry-based build configuration
├── Makefile                     # Development commands and workflows
├── agent_uri/                   # Unified Python package
│   ├── __init__.py              # Package initialization and public API
│   ├── parser.py                # URI parsing and validation
│   ├── descriptor/              # Agent descriptor handling
│   │   ├── models.py            # Data models for agent descriptors
│   │   ├── parser.py            # Descriptor parsing and validation
│   │   ├── validator.py         # Schema validation
│   │   └── compatibility.py     # Agent Card compatibility layer
│   ├── resolver/                # Resolution framework
│   │   ├── resolver.py          # Agent resolution logic
│   │   └── cache.py             # Caching mechanisms
│   ├── transport/               # Transport bindings
│   │   ├── base.py              # Abstract transport interface
│   │   ├── registry.py          # Transport registry
│   │   └── transports/          # Transport implementations
│   │       ├── https.py         # HTTPS transport
│   │       ├── websocket.py     # WebSocket transport
│   │       └── local.py         # Local/direct transport
│   ├── client.py                # Client SDK for agent communication
│   ├── server.py                # Server SDK for agent hosting
│   ├── capability.py            # Capability framework and decorators
│   ├── auth.py                  # Authentication and authorization
│   ├── cli.py                   # Command-line interface
│   └── common/                  # Shared utilities and types
│       └── error/               # Error handling framework
├── docs/                        # Documentation
│   ├── rfc/                     # RFC documents and specifications
│   ├── spec/                    # Technical specifications
│   └── examples.md              # Usage examples and tutorials
├── examples/                    # Example implementations
│   └── echo-agent/              # Echo agent demonstration
└── scripts/                     # Development and build scripts
```

## Installation

Install from PyPI:

```bash
pip install agent-uri
```

Or install from source:

```bash
git clone https://github.com/agent-uri/agent-uri.git
cd agent-uri
make install-dev
```

## Quick Start

### Parsing Agent URIs

```python
from agent_uri import parse_agent_uri

# Parse a basic agent URI
uri = parse_agent_uri("agent://example.com/my-agent")
print(f"Host: {uri.host}, Path: {uri.path}")

# Parse with protocol and capability
uri = parse_agent_uri("agent+https://api.example.com/agents/assistant/chat")
print(f"Protocol: {uri.protocol}, Capability: {uri.capability}")
```

### Creating an Agent Server

```python
from agent_uri import FastAPIAgentServer, capability

@capability(
    name="echo",
    description="Echo back the input message",
    version="1.0.0"
)
async def echo_handler(message: str) -> dict:
    return {"response": f"Echo: {message}"}

# Create and configure server
server = FastAPIAgentServer(
    name="my-agent",
    version="1.0.0",
    description="A simple echo agent"
)
server.register_capability("echo", echo_handler)

# Run the server
if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8000)
```

### Using the Agent Client

```python
from agent_uri import AgentClient

# Connect to an agent
client = AgentClient("agent+https://api.example.com/my-agent")

# Invoke a capability
result = await client.invoke("echo", {"message": "Hello, World!"})
print(result["response"])  # "Echo: Hello, World!"
```

## Development

This project uses Poetry and uv for dependency management:

```bash
# Install development dependencies
make install-dev

# Run tests
make test-all

# Run linting and formatting
make lint
make format

# Run type checking
make type-check

# Run security checks
make security
```

See the [Makefile](./Makefile) for all available commands.

## Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Usage Examples](docs/examples.md)
- [Protocol Specification](docs/rfc/draft-narvaneni-agent-uri-00.md)

## License

[BSD 3-Clause License](./LICENSE)
