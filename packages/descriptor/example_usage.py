#!/usr/bin/env python3
"""
Example script demonstrating how to use the agent_descriptor library.

This example covers:
1. Creating agent descriptors programmatically
2. Parsing descriptors from JSON
3. Validating descriptors
4. Converting to Agent2Agent's AgentCard format
5. Loading and saving descriptors to files
"""

import json
import sys
import tempfile
from pathlib import Path

from agent_descriptor.models import (
    AgentDescriptor,
    Capability,
    Provider,
    Authentication,
    Skill,
    AgentCapabilities
)
from agent_descriptor.parser import (
    parse_descriptor,
    load_descriptor,
    save_descriptor,
    descriptor_to_dict
)
from agent_descriptor.validator import (
    validate_descriptor,
    validate_agent_card_compatibility,
    check_json_ld_extensions
)
from agent_descriptor.compatibility import (
    to_agent_card,
    from_agent_card,
    is_agent_card_compatible,
    DescriptorFormat,
    to_format
)


def create_descriptor_example():
    """Create an AgentDescriptor object programmatically."""
    print("\n=== Creating a descriptor programmatically ===")
    
    # Create a descriptor
    descriptor = AgentDescriptor(
        name="example-agent",
        version="1.0.0",
        description="An example agent for demonstration purposes",
        url="agent://example-agent/",
        capabilities=[
            Capability(
                name="echo",
                description="Echoes back the input",
                is_deterministic=True,
                tags=["utility", "basic"]
            ),
            Capability(
                name="generate-text",
                description="Generates text based on a prompt",
                is_deterministic=False,
                expected_output_variability="high",
                streaming=True,
                tags=["ai", "nlp"]
            )
        ],
        provider=Provider(
            organization="Example Org",
            url="https://example.com"
        ),
        skills=[
            Skill(
                id="echo-skill",
                name="Echo Skill",
                description="Can echo back user input"
            ),
            Skill(
                id="generation-skill",
                name="Text Generation",
                description="Can generate text responses",
                tags=["ai", "nlp"]
            )
        ],
        authentication=Authentication(
            schemes=["Bearer", "API Key"]
        ),
        agent_capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            state_transition_history=True
        )
    )
    
    print(f"Created descriptor for '{descriptor.name}' version {descriptor.version}")
    print(f"It has {len(descriptor.capabilities)} capabilities and {len(descriptor.skills)} skills")
    
    return descriptor


def parse_descriptor_example():
    """Parse a descriptor from a JSON string."""
    print("\n=== Parsing a descriptor from JSON ===")
    
    # Descriptor data as JSON
    descriptor_json = """
    {
        "name": "json-agent",
        "version": "2.0.0",
        "description": "An agent parsed from JSON",
        "capabilities": [
            {
                "name": "json-capability",
                "description": "A capability defined in JSON",
                "tags": ["json", "example"]
            }
        ],
        "skills": [
            {
                "id": "json-skill",
                "name": "JSON Skill"
            }
        ]
    }
    """
    
    # Parse the JSON
    data = json.loads(descriptor_json)
    descriptor = parse_descriptor(data)
    
    print(f"Parsed descriptor for '{descriptor.name}' version {descriptor.version}")
    print(f"Description: {descriptor.description}")
    print(f"First capability: {descriptor.capabilities[0].name}")
    
    return descriptor


def validate_descriptor_example(descriptor):
    """Validate a descriptor against the schema."""
    print("\n=== Validating a descriptor ===")
    
    # Convert to dictionary for validation
    descriptor_dict = descriptor_to_dict(descriptor)
    
    # Validate
    result = validate_descriptor(descriptor_dict)
    
    if result.valid:
        print("✅ Descriptor is valid!")
    else:
        print("❌ Descriptor is invalid:")
        for error in result.errors:
            print(f"  - Error in {error.path}: {error.message}")
    
    # Check Agent2Agent compatibility
    compat_result = validate_agent_card_compatibility(descriptor_dict)
    
    if not any(err.severity == "warning" for err in compat_result.errors):
        print("✅ Descriptor is fully compatible with Agent2Agent's AgentCard format")
    else:
        print("⚠️ Descriptor has some Agent2Agent compatibility warnings:")
        for error in compat_result.errors:
            if error.severity == "warning":
                print(f"  - Warning in {error.path}: {error.message}")
    
    # Check JSON-LD
    jsonld_result = check_json_ld_extensions(descriptor_dict)
    
    if any(err.path == "@context" for err in jsonld_result.errors):
        print("ℹ️ Descriptor could be improved with a JSON-LD @context")


def convert_formats_example(descriptor):
    """Convert between different descriptor formats."""
    print("\n=== Converting between formats ===")
    
    # Convert to Agent2Agent AgentCard
    agent_card = to_agent_card(descriptor)
    print("Converted to Agent2Agent AgentCard format:")
    print(f"  - Name: {agent_card['name']}")
    print(f"  - Capabilities: {agent_card['capabilities']}")
    print(f"  - Skills: {len(agent_card['skills'])} skills")
    
    # Check if compatible
    is_compatible = is_agent_card_compatible(descriptor)
    print(f"Is compatible with AgentCard: {is_compatible}")
    
    # Convert using the generic API
    jsonld_format = to_format(descriptor, DescriptorFormat.JSONLD)
    print("\nConverted to JSON-LD format:")
    if "@context" in jsonld_format:
        print(f"  - @context: {jsonld_format['@context']}")
    else:
        print("  - No @context specified (using default)")


def save_load_example(descriptor):
    """Save and load a descriptor to/from a file."""
    print("\n=== Saving and loading descriptors ===")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "agent.json"
        
        # Save the descriptor
        save_descriptor(descriptor, str(file_path))
        print(f"Saved descriptor to {file_path}")
        
        # Load the descriptor
        loaded_descriptor = load_descriptor(str(file_path))
        print(f"Loaded descriptor for '{loaded_descriptor.name}' version {loaded_descriptor.version}")
        
        # Verify it's the same
        if loaded_descriptor.name == descriptor.name and loaded_descriptor.version == descriptor.version:
            print("✅ Loaded descriptor matches the original")
        else:
            print("❌ Loaded descriptor doesn't match the original")


def main():
    """Run all the examples."""
    print("=== Agent Descriptor Library Example ===")
    
    # Step 1: Create a descriptor programmatically
    descriptor = create_descriptor_example()
    
    # Step 2: Parse a descriptor from JSON
    parsed = parse_descriptor_example()
    
    # Step 3: Validate a descriptor
    validate_descriptor_example(descriptor)
    
    # Step 4: Convert between formats
    convert_formats_example(descriptor)
    
    # Step 5: Save and load a descriptor
    save_load_example(descriptor)
    
    print("\nAll examples completed successfully!")


if __name__ == "__main__":
    main()
