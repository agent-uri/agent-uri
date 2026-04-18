"""Tests for the descriptor parser (draft-narvaneni-agent-uri-03)."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from ..models import AgentDescriptor, Provider, Skill
from ..parser import (
    descriptor_to_dict,
    load_descriptor,
    parse_descriptor,
    save_descriptor,
)


def _minimal() -> dict:
    return {
        "name": "test-agent",
        "version": "1.0.0",
        "skills": [
            {"id": "echo", "name": "echo", "description": "Echo skill"},
        ],
    }


def test_parse_minimal_descriptor():
    descriptor = parse_descriptor(_minimal())
    assert descriptor.name == "test-agent"
    assert descriptor.version == "1.0.0"
    assert len(descriptor.skills) == 1
    assert descriptor.skills[0].id == "echo"
    assert descriptor.skills[0].name == "echo"
    assert descriptor.skills[0].description == "Echo skill"


def test_parse_full_descriptor():
    data = {
        "name": "full-agent",
        "version": "2.1.0",
        "description": "A test agent with all fields",
        "url": "agent://full-agent/",
        "provider": {"organization": "Test Org", "url": "https://example.com"},
        "documentationUrl": "https://docs.example.com",
        "interactionModel": ["agent2agent"],
        "supportedVersions": {"1.0.0": "/v1/", "2.0.0": "/v2/"},
        "conformanceLevel": 2,
        "environment": "production",
        "authentication": {"schemes": ["Bearer", "API Key"]},
        "transport": {"endpoint": "https://full-agent.example.com/"},
        "skills": [
            {
                "id": "echo",
                "name": "echo",
                "description": "A test skill",
                "version": "1.0.0",
                "tags": ["test", "demo"],
            },
            {
                "id": "stream",
                "name": "stream",
                "description": "Streaming skill",
                "streaming": True,
                "streamingFormat": "sse",
            },
        ],
    }

    descriptor = parse_descriptor(data)

    assert descriptor.name == "full-agent"
    assert descriptor.version == "2.1.0"
    assert descriptor.description == "A test agent with all fields"
    assert descriptor.conformance_level == 2
    assert descriptor.environment == "production"
    assert descriptor.provider.organization == "Test Org"
    assert descriptor.supported_versions == {"1.0.0": "/v1/", "2.0.0": "/v2/"}
    assert descriptor.interaction_model == ["agent2agent"]
    assert descriptor.transport.endpoint == "https://full-agent.example.com/"
    assert descriptor.authentication.schemes == ["Bearer", "API Key"]

    assert len(descriptor.skills) == 2
    assert descriptor.skills[0].tags == ["test", "demo"]
    assert descriptor.skills[1].streaming is True
    assert descriptor.skills[1].streaming_format == "sse"


def test_required_fields_missing():
    with pytest.raises(ValueError, match="name"):
        parse_descriptor(
            {
                "version": "1.0.0",
                "skills": [{"id": "s", "name": "s", "description": "s"}],
            }
        )

    with pytest.raises(ValueError, match="version"):
        parse_descriptor(
            {"name": "test", "skills": [{"id": "s", "name": "s", "description": "s"}]}
        )

    with pytest.raises(ValueError, match="skills"):
        parse_descriptor({"name": "test", "version": "1.0.0"})


def test_skill_requires_id_name_description():
    """Each skill must have id, name, description."""
    with pytest.raises(ValueError):
        parse_descriptor(
            {"name": "x", "version": "1.0.0", "skills": [{"name": "no-id"}]}
        )


def test_load_from_dict():
    descriptor = load_descriptor(_minimal())
    assert descriptor.name == "test-agent"
    assert len(descriptor.skills) == 1


def test_load_from_file():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
        json.dump(_minimal(), f)
        temp_path = f.name
    try:
        descriptor = load_descriptor(temp_path)
        assert descriptor.name == "test-agent"
        assert descriptor.skills[0].id == "echo"
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_descriptor_to_dict():
    descriptor = AgentDescriptor(
        name="test-agent",
        version="1.0.0",
        skills=[Skill(id="test-skill", name="Test Skill", description="A skill")],
        provider=Provider(organization="Test Org", url="https://example.com"),
        context="https://example.org/agent-context.jsonld",
    )

    out = descriptor_to_dict(descriptor)
    assert out["name"] == "test-agent"
    assert out["version"] == "1.0.0"
    assert out["skills"][0]["id"] == "test-skill"
    assert out["provider"]["organization"] == "Test Org"
    assert out["@context"] == "https://example.org/agent-context.jsonld"


def test_save_descriptor():
    descriptor = AgentDescriptor(
        name="save-agent",
        version="1.0.0",
        skills=[Skill(id="s", name="s", description="save skill")],
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "agent.json"
        save_descriptor(descriptor, str(path))
        assert path.exists()
        with open(path, "r") as f:
            saved = json.load(f)
        assert saved["name"] == "save-agent"
        assert saved["skills"][0]["id"] == "s"
