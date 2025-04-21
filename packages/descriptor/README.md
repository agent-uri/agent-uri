# Agent Descriptor

A Python library for parsing, validating, and manipulating agent.json descriptors as defined in the agent:// protocol specification.

## Overview

The Agent Descriptor library provides a comprehensive set of tools for working with agent descriptors, which are JSON documents that describe an agent's identity, capabilities, and behavior. These descriptors are a key part of the `agent://` protocol, which enables interoperability between autonomous and semi-autonomous software agents.

This library offers:

- Type-safe data models for representing agent descriptors
- Parsing and validation of agent descriptors
- Conversion between different descriptor formats (Agent2Agent's AgentCard, JSON-LD)
- Utilities for loading and saving descriptors from/to files

## Installation

```bash
pip install agent-descriptor
```

Or install directly from this repository:

```bash
cd agent-uri/packages/descriptor
pip install -e .
```

## Basic Usage

```python
from agent_descriptor import (
    parse_descriptor,
    load_descriptor,
    validate_descriptor,
    AgentDescriptor,
    Capability
)

# Parse a descriptor from a dictionary
descriptor_data = {
    "name": "example-agent",
    "version": "1.0.0",
    "capabilities": [
        {
            "name": "example-capability",
            "description": "An example capability"
        }
    ]
}
descriptor = parse_descriptor(descriptor_data)

# Load a descriptor from a file
descriptor = load_descriptor("path/to/agent.json")

# Validate a descriptor
from agent_descriptor.validator import validate_descriptor
result = validate_descriptor(descriptor_data)
if result.valid:
    print("Descriptor is valid!")
else:
    for error in result.errors:
        print(f"Error in {error.path}: {error.message}")

# Create a descriptor programmatically
from agent_descriptor.models import AgentDescriptor, Capability
descriptor = AgentDescriptor(
    name="my-agent",
    version="1.0.0",
    capabilities=[
        Capability(
            name="my-capability",
            description="A test capability"
        )
    ]
)

# Save a descriptor to a file
from agent_descriptor.parser import save_descriptor
save_descriptor(descriptor, "path/to/output/agent.json")

# Convert to Agent2Agent protocol's AgentCard format
from agent_descriptor.compatibility import to_agent_card
agent_card = to_agent_card(descriptor)
```

## Features

### Data Models

Agent Descriptor provides a set of data classes that match the structure of agent descriptors as defined in the agent:// protocol specification:

- `AgentDescriptor`: The main class representing an agent descriptor
- `Capability`: Represents a capability offered by an agent
- `Provider`: Information about the provider of the agent
- `Authentication`: Authentication methods supported by the agent
- `Skill`: A skill the agent possesses, which may map to multiple capabilities

### Parsing and Validation

The library includes comprehensive parsing and validation functionality:

- `parse_descriptor`: Parse an agent descriptor from a dictionary
- `load_descriptor`: Load a descriptor from a file path or URL
- `validate_descriptor`: Validate an agent descriptor against the schema
- `validate_required_fields`: Check that the descriptor contains all required fields

### Format Compatibility

Agent Descriptor supports converting between different descriptor formats:

- `to_agent_card`: Convert an AgentDescriptor to an Agent2Agent protocol AgentCard
- `from_agent_card`: Convert an Agent2Agent protocol AgentCard to an AgentDescriptor
- `is_agent_card_compatible`: Check if an AgentDescriptor is compatible with the Agent2Agent protocol

The library has a generic framework for supporting multiple formats through the `to_format`, `from_format`, and `is_format_compatible` functions.

## API Reference

### Core Classes

- `AgentDescriptor`: The main class representing an agent descriptor
- `ValidationResult`: Contains the results of a validation operation

### Core Functions

- `parse_descriptor(descriptor_data)`: Parse an agent descriptor from a dictionary
- `load_descriptor(source)`: Load an agent descriptor from a file path, URL, or dictionary
- `save_descriptor(descriptor, file_path)`: Save an AgentDescriptor to a JSON file
- `validate_descriptor(descriptor_data)`: Validate an agent descriptor against the schema
- `to_format(descriptor, format_type)`: Convert an AgentDescriptor to a specified external format
- `from_format(data, format_type)`: Convert from an external format to an AgentDescriptor

## License

MIT License
