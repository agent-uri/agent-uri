# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a reference implementation of the `agent://` protocol - a URI-based framework for addressing, invoking, and interoperating with AI agents. The project implements a complete layered architecture for agent discovery, transport, and interaction.

## Build System & Development Commands

This project uses Poetry + uv for dependency management and development. The build system is configured in `pyproject.toml` with comprehensive tooling.

### Essential Commands

```bash
# Development setup
make install-dev          # Install all dependencies + dev tools + pre-commit hooks
make install             # Install production dependencies only
uv sync                  # Fast dependency sync with uv

# Testing
make test                # Run fast unit tests
make test-all           # Run all tests including integration
make test-coverage      # Run tests with coverage report
pytest packages/*/tests # Run tests for specific packages
scripts/test-all.sh     # Comprehensive test suite with reporting

# Code Quality
make lint               # Run all linting tools (flake8, black, isort)
make format             # Auto-format code with black and isort
make type-check         # Run mypy type checking
make security           # Run bandit security checks
make quality-gate       # Run complete quality gate (CI checks)
scripts/lint-all.sh     # Comprehensive linting with reporting
scripts/lint-all.sh fix # Auto-fix formatting issues

# Documentation
make docs               # Build documentation
make docs-serve         # Serve docs locally at http://127.0.0.1:8000

# Build & Maintenance
make build              # Build all packages for distribution
make clean              # Clean build artifacts and caches
make update-deps        # Update all dependencies
```

### Running Specific Tests

```bash
# Test specific components
pytest agent_uri/tests/            # Test all components
pytest agent_uri/common/tests/     # Test common utilities
pytest agent_uri/descriptor/tests/ # Test descriptor functionality
pytest agent_uri/transport/tests/  # Test transport layer
```

## Architecture Overview

### Package Structure

The codebase is organized as a single `agent_uri` package with modular components:

```
agent_uri/
├── parser.py          # Core: Parse and validate agent:// URIs
├── common/            # Shared utilities and RFC 7807 error handling
├── descriptor/        # Data models for agent.json descriptors
├── resolver/          # Discovery layer: resolve URIs to descriptors
├── transport/         # Abstract transport layer (HTTPS, WebSocket, Local)
├── server.py          # Server framework for building agents
├── client.py          # High-level client SDK
├── auth.py            # Authentication providers
├── capability.py      # Capability registration and decorators
├── handler.py         # Request handlers for different transports
└── exceptions.py      # Custom exceptions
```

### Dependency Flow

```
┌─────────────────────────────┐
│     agent-client            │ (Application Layer)
├─────────────────────────────┤
│     agent-server            │ (Server Framework)
├─────────────────────────────┤
│  agent-resolver │ transport │ (Service Layer)
├─────────────────────────────┤
│  descriptor │ uri-parser    │ (Core Layer)
├─────────────────────────────┤
│       agent-common          │ (Foundation)
└─────────────────────────────┘
```

**Key principle**: No circular dependencies. Higher-level packages depend on lower-level ones.

### Core Workflows

1. **URI Resolution Flow**:
   ```
   Client → Parse URI → Resolve to Descriptor → Get Transport → Invoke Capability
   ```

2. **Server Registration Flow**:
   ```
   Define Capability → Register with Server → Generate Descriptor → Handle Requests
   ```

3. **Error Propagation**:
   ```
   Transport Error → Common Error Model → Client Exception → User Feedback
   ```

## Key Architectural Patterns

### 1. Layered Architecture
- Clear separation of concerns across layers
- Each package has a specific responsibility
- Dependencies flow downward only

### 2. Plugin Architecture
- Transport layer uses registry pattern for extensibility
- Server capabilities use decorator pattern
- New transports can be added without modifying core code

### 3. Protocol Implementation
- Implements RFC-style agent:// URI specification
- Uses RFC 7807 for standardized error handling
- JSON Schema validation for descriptors

### 4. Type Safety
- Comprehensive use of Python type hints
- Dataclasses for structured data
- mypy type checking enforced

## Development Patterns

### Package Structure Convention
Each package follows this structure:
```
packages/package-name/
├── agent_package/      # Main module (note: underscores in module names)
│   ├── __init__.py
│   ├── main_module.py
│   └── tests/         # Tests co-located with code
├── setup.py           # Package configuration
└── README.md
```

### Test Strategy
- Unit tests in each package's tests/ directory
- Integration tests use `@pytest.mark.integration`
- Coverage target: 80%+ (configured in pyproject.toml)
- Use pytest markers: `unit`, `integration`, `e2e`, `slow`, `network`

### Code Quality Standards
- Black formatting (line length: 88)
- isort for import sorting
- flake8 for PEP8 compliance
- mypy for type checking
- bandit for security scanning
- Pre-commit hooks enforced

### Error Handling
- Use agent-common error models for consistency
- Follow RFC 7807 Problem Details format
- Provide transport-specific error formatting
- Include proper error context and debugging info

## Working with the Codebase

### Adding New Packages
1. Create package directory under `packages/`
2. Add to pyproject.toml dependencies
3. Follow existing naming conventions (agent_package_name)
4. Include tests/ directory
5. Add to scripts/test-all.sh and scripts/lint-all.sh

### Transport Implementation
- Inherit from `agent_transport.base.BaseTransport`
- Register in `agent_transport.registry`
- Implement required methods: `invoke`, `stream`, `close`
- Add tests in `agent_transport/tests/`

### Server Capabilities
- Use `@capability` decorator from agent_server
- Register capabilities with the server
- Descriptors auto-generated from capability definitions
- Support both sync and async handlers

### Client Usage
- Use `AgentClient` for high-level interactions
- Supports session management and authentication
- Handles transport selection automatically
- Provides both sync and async interfaces

## Important Files

- `pyproject.toml`: Main project configuration, dependencies, tool settings
- `Makefile`: Development commands and build automation
- `scripts/`: Development automation scripts
- `docs/rfc/`: Agent URI protocol specification
- `examples/echo-agent/`: Complete example implementation

## Testing Notes

- Run `make test` for fast unit tests during development
- Use `make test-all` for comprehensive testing before commits
- Integration tests may require network access
- Performance tests available but not run by default
- Coverage reports generated in `htmlcov/`

## Build Notes

- Uses Poetry for dependency management
- uv for fast dependency resolution
- Supports Python 3.9-3.12
- Single package structure ready for PyPI publishing
- No internal path dependencies - all components in one package

## PyPI Publishing

The package is configured as a single `agent-uri` package ready for PyPI:

```bash
# Build for distribution
poetry build                    # Creates wheel and sdist in dist/

# Publish to Test PyPI (for testing)
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry publish --repository testpypi

# Publish to Production PyPI
poetry publish                  # Requires PyPI API token

# Install from PyPI (once published)
pip install agent-uri
```

### Usage after PyPI installation:
```python
from agent_uri import AgentUri, parse_agent_uri

# Parse an agent URI
uri = parse_agent_uri("agent://example.com/my-agent")
print(f"Host: {uri.host}, Path: {uri.path}")
```
