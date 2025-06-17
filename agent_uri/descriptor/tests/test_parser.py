"""Tests for the parser module."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from ..models import AgentDescriptor, Capability, Provider, Skill
from ..parser import (
    descriptor_to_dict,
    load_descriptor,
    parse_descriptor,
    save_descriptor,
)


def test_parse_minimal_descriptor():
    """Test parsing a minimal valid descriptor."""
    descriptor_data = {
        "name": "test-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "test-capability"}],
    }

    descriptor = parse_descriptor(descriptor_data)

    assert descriptor.name == "test-agent"
    assert descriptor.version == "1.0.0"
    assert len(descriptor.capabilities) == 1
    assert descriptor.capabilities[0].name == "test-capability"


def test_parse_full_descriptor():
    """Test parsing a complete descriptor with all fields."""
    descriptor_data = {
        "name": "full-agent",
        "version": "2.1.0",
        "description": "A test agent with all fields",
        "url": "agent://full-agent/",
        "provider": {"organization": "Test Org", "url": "https://example.com"},
        "documentationUrl": "https://docs.example.com",
        "interactionModel": "agent2agent",
        "orchestration": "delegation",
        "envelopeSchemas": ["fipa-acl", "json-rpc"],
        "supportedVersions": {"1.0.0": "/v1/", "2.0.0": "/v2/"},
        "capabilities": [
            {
                "name": "capability-1",
                "description": "Test capability 1",
                "version": "1.0.0",
                "isDeterministic": False,
                "expectedOutputVariability": "medium",
                "tags": ["test", "demo"],
            },
            {
                "name": "capability-2",
                "description": "Test capability 2",
                "streaming": True,
            },
        ],
        "authentication": {"schemes": ["Bearer", "API Key"]},
        "skills": [
            {
                "id": "skill-1",
                "name": "Test Skill",
                "description": "A test skill",
                "tags": ["test"],
            }
        ],
        "defaultInputModes": ["text", "voice"],
        "defaultOutputModes": ["text", "image"],
    }

    descriptor = parse_descriptor(descriptor_data)

    # Check basic fields
    assert descriptor.name == "full-agent"
    assert descriptor.version == "2.1.0"
    assert descriptor.description == "A test agent with all fields"
    assert descriptor.url == "agent://full-agent/"

    # Check provider
    assert descriptor.provider.organization == "Test Org"
    assert descriptor.provider.url == "https://example.com"

    # Check supported versions
    assert descriptor.supported_versions == {"1.0.0": "/v1/", "2.0.0": "/v2/"}

    # Check capabilities
    assert len(descriptor.capabilities) == 2
    assert descriptor.capabilities[0].name == "capability-1"
    assert descriptor.capabilities[0].description == "Test capability 1"
    assert descriptor.capabilities[0].tags == ["test", "demo"]
    assert descriptor.capabilities[1].name == "capability-2"
    assert descriptor.capabilities[1].streaming is True

    # Check authentication
    assert descriptor.authentication.schemes == ["Bearer", "API Key"]

    # Check skills
    assert len(descriptor.skills) == 1
    assert descriptor.skills[0].id == "skill-1"
    assert descriptor.skills[0].name == "Test Skill"

    # Check modes
    assert descriptor.default_input_modes == ["text", "voice"]
    assert descriptor.default_output_modes == ["text", "image"]


def test_required_fields_missing():
    """Test that parsing fails when required fields are missing."""
    # Missing name
    with pytest.raises(ValueError, match="name"):
        parse_descriptor({"version": "1.0.0", "capabilities": [{"name": "test"}]})

    # Missing version
    with pytest.raises(ValueError, match="version"):
        parse_descriptor({"name": "test", "capabilities": [{"name": "test"}]})

    # Missing capabilities
    with pytest.raises(ValueError, match="capabilities"):
        parse_descriptor({"name": "test", "version": "1.0.0"})


def test_load_from_dict():
    """Test loading a descriptor from a dictionary."""
    descriptor_data = {
        "name": "test-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "test-capability"}],
    }

    descriptor = load_descriptor(descriptor_data)

    assert descriptor.name == "test-agent"
    assert descriptor.version == "1.0.0"
    assert len(descriptor.capabilities) == 1


def test_load_from_file():
    """Test loading a descriptor from a file."""
    descriptor_data = {
        "name": "file-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "file-capability"}],
    }

    # Create a temporary file with the descriptor data
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
        json.dump(descriptor_data, f)
        temp_path = f.name

    try:
        # Load the descriptor from the file
        descriptor = load_descriptor(temp_path)

        assert descriptor.name == "file-agent"
        assert descriptor.version == "1.0.0"
        assert len(descriptor.capabilities) == 1
        assert descriptor.capabilities[0].name == "file-capability"
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_descriptor_to_dict():
    """Test converting a descriptor to a dictionary."""
    # Create a descriptor
    descriptor = AgentDescriptor(
        name="test-agent",
        version="1.0.0",
        capabilities=[
            Capability(name="test-capability", description="A test capability")
        ],
        provider=Provider(organization="Test Org", url="https://example.com"),
        skills=[Skill(id="test-skill", name="Test Skill")],
        context="https://example.org/agent-context.jsonld",
    )

    # Convert to dictionary
    descriptor_dict = descriptor_to_dict(descriptor)

    # Check the conversion
    assert descriptor_dict["name"] == "test-agent"
    assert descriptor_dict["version"] == "1.0.0"
    assert len(descriptor_dict["capabilities"]) == 1
    assert descriptor_dict["capabilities"][0]["name"] == "test-capability"
    assert descriptor_dict["provider"]["organization"] == "Test Org"
    assert descriptor_dict["skills"][0]["id"] == "test-skill"
    assert descriptor_dict["@context"] == "https://example.org/agent-context.jsonld"


def test_save_descriptor():
    """Test saving a descriptor to a file."""
    # Create a descriptor
    descriptor = AgentDescriptor(
        name="save-agent",
        version="1.0.0",
        capabilities=[Capability(name="save-capability")],
    )

    # Create a temporary path for the descriptor file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "agent.json"

        # Save the descriptor
        save_descriptor(descriptor, str(temp_path))

        # Check that the file was created
        assert temp_path.exists()

        # Load the descriptor from the file and check its contents
        with open(temp_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["name"] == "save-agent"
        assert saved_data["version"] == "1.0.0"
        assert len(saved_data["capabilities"]) == 1
        assert saved_data["capabilities"][0]["name"] == "save-capability"
