"""Tests for the compatibility module."""

import pytest

from ..compatibility import (
    Agent2AgentConverter,
    DescriptorFormat,
    JsonLdConverter,
    from_agent_card,
    from_format,
    is_agent_card_compatible,
    is_format_compatible,
    to_agent_card,
    to_format,
)
from ..models import (
    AgentCapabilities,
    AgentDescriptor,
    Authentication,
    Capability,
    Provider,
    Skill,
)


def test_to_agent_card():
    """Test converting an AgentDescriptor to an Agent2Agent AgentCard."""
    # Create a descriptor
    descriptor = AgentDescriptor(
        name="test-agent",
        version="1.0.0",
        url="agent://test-agent/",
        description="A test agent",
        capabilities=[
            Capability(name="test-capability", description="A test capability")
        ],
        provider=Provider(organization="Test Org", url="https://example.com"),
        skills=[
            Skill(
                id="test-skill",
                name="Test Skill",
                description="A test skill",
                tags=["test"],
            )
        ],
        agent_capabilities=AgentCapabilities(
            streaming=True, push_notifications=False, state_transition_history=True
        ),
        authentication=Authentication(schemes=["Bearer", "API Key"]),
        default_input_modes=["text", "voice"],
        default_output_modes=["text"],
    )

    # Convert to AgentCard
    agent_card = to_agent_card(descriptor)

    # Check the conversion
    assert agent_card["name"] == "test-agent"
    assert agent_card["version"] == "1.0.0"
    assert agent_card["url"] == "agent://test-agent/"
    assert agent_card["description"] == "A test agent"

    # Check provider
    assert agent_card["provider"]["organization"] == "Test Org"
    assert agent_card["provider"]["url"] == "https://example.com"

    # Check capabilities
    assert agent_card["capabilities"]["streaming"] is True
    assert agent_card["capabilities"]["pushNotifications"] is False
    assert agent_card["capabilities"]["stateTransitionHistory"] is True

    # Check authentication
    assert agent_card["authentication"]["schemes"] == ["Bearer", "API Key"]

    # Check skills
    assert len(agent_card["skills"]) == 1
    assert agent_card["skills"][0]["id"] == "test-skill"
    assert agent_card["skills"][0]["name"] == "Test Skill"
    assert agent_card["skills"][0]["tags"] == ["test"]

    # Check modes
    assert agent_card["defaultInputModes"] == ["text", "voice"]
    assert agent_card["defaultOutputModes"] == ["text"]


def test_from_agent_card():
    """Test converting an Agent2Agent AgentCard to an AgentDescriptor."""
    # Create an AgentCard
    agent_card = {
        "name": "card-agent",
        "version": "2.0.0",
        "url": "agent://card-agent/",
        "description": "An agent from a card",
        "provider": {"organization": "Card Org"},
        "capabilities": {
            "streaming": True,
            "pushNotifications": True,
            "stateTransitionHistory": False,
        },
        "authentication": {"schemes": ["OAuth2"], "credentials": "token"},
        "skills": [
            {
                "id": "card-skill",
                "name": "Card Skill",
                "description": "A skill from a card",
                "tags": ["card"],
                "examples": ["Example 1", "Example 2"],
                "inputModes": ["text"],
                "outputModes": ["text", "image"],
            }
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text", "image"],
    }

    # Convert to AgentDescriptor
    descriptor = from_agent_card(agent_card)

    # Check the conversion
    assert descriptor.name == "card-agent"
    assert descriptor.version == "2.0.0"
    assert descriptor.url == "agent://card-agent/"
    assert descriptor.description == "An agent from a card"

    # Check provider
    assert descriptor.provider.organization == "Card Org"

    # Check capabilities (auto-generated from skills)
    assert len(descriptor.capabilities) == 1
    assert descriptor.capabilities[0].name == "capability-card-skill"

    # Check agent_capabilities
    assert descriptor.agent_capabilities.streaming is True
    assert descriptor.agent_capabilities.push_notifications is True
    assert descriptor.agent_capabilities.state_transition_history is False

    # Check authentication
    assert descriptor.authentication.schemes == ["OAuth2"]
    assert descriptor.authentication.details == {"credentials": "token"}

    # Check skills
    assert len(descriptor.skills) == 1
    assert descriptor.skills[0].id == "card-skill"
    assert descriptor.skills[0].name == "Card Skill"
    assert descriptor.skills[0].tags == ["card"]
    assert descriptor.skills[0].examples == ["Example 1", "Example 2"]
    assert descriptor.skills[0].input_modes == ["text"]
    assert descriptor.skills[0].output_modes == ["text", "image"]

    # Check modes
    assert descriptor.default_input_modes == ["text"]
    assert descriptor.default_output_modes == ["text", "image"]


def test_is_agent_card_compatible():
    """Test checking if an AgentDescriptor is compatible with AgentCard."""
    # Create a compatible descriptor
    compatible = AgentDescriptor(
        name="compatible-agent",
        version="1.0.0",
        url="agent://compatible-agent/",
        capabilities=[Capability(name="compatible-capability")],
        skills=[Skill(id="compatible-skill", name="Compatible Skill")],
    )
    assert is_agent_card_compatible(compatible) is True

    # Create an incompatible descriptor (no skills)
    incompatible = AgentDescriptor(
        name="incompatible-agent",
        version="1.0.0",
        capabilities=[Capability(name="incompatible-capability")],
        skills=[],  # No skills - incompatible with AgentCard
    )
    assert is_agent_card_compatible(incompatible) is False

    # Create another incompatible descriptor (no capabilities)
    incompatible2 = AgentDescriptor(
        name="incompatible-agent-2",
        version="1.0.0",
        url="agent://incompatible-agent-2/",
        capabilities=[],  # No capabilities - incompatible with AgentCard
        skills=[Skill(id="incompatible-skill", name="Incompatible Skill")],
    )
    assert is_agent_card_compatible(incompatible2) is False


def test_to_format():
    """Test converting to different formats."""
    # Create a descriptor
    descriptor = AgentDescriptor(
        name="format-agent",
        version="1.0.0",
        capabilities=[Capability(name="format-capability")],
        skills=[Skill(id="format-skill", name="Format Skill")],
        context="https://example.org/agent-context.jsonld",
    )

    # Convert to Agent2Agent format
    agent2agent = to_format(descriptor, DescriptorFormat.AGENT2AGENT)
    assert agent2agent["name"] == "format-agent"
    assert "skills" in agent2agent

    # Convert to JSON-LD format
    jsonld = to_format(descriptor, DescriptorFormat.JSONLD)
    assert jsonld["name"] == "format-agent"
    assert jsonld["@context"] == "https://example.org/agent-context.jsonld"

    # Test invalid format
    with pytest.raises(ValueError):
        to_format(descriptor, "invalid-format")


def test_from_format():
    """Test converting from different formats."""
    # Create an AgentCard
    agent_card = {
        "name": "from-card",
        "version": "1.0.0",
        "url": "agent://from-card/",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "skills": [{"id": "from-skill", "name": "From Skill"}],
    }

    # Convert from Agent2Agent format
    descriptor = from_format(agent_card, DescriptorFormat.AGENT2AGENT)
    assert descriptor.name == "from-card"
    assert descriptor.url == "agent://from-card/"

    # Create a JSON-LD document
    jsonld_doc = {
        "@context": "https://example.org/agent-context.jsonld",
        "name": "from-jsonld",
        "version": "1.0.0",
        "capabilities": [{"name": "jsonld-capability"}],
    }

    # Convert from JSON-LD format
    descriptor = from_format(jsonld_doc, DescriptorFormat.JSONLD)
    assert descriptor.name == "from-jsonld"
    assert descriptor.context == "https://example.org/agent-context.jsonld"

    # Test invalid format
    with pytest.raises(ValueError):
        from_format({}, "invalid-format")


def test_is_format_compatible():
    """Test checking compatibility with different formats."""
    # Create a descriptor
    descriptor = AgentDescriptor(
        name="compatibility-agent",
        version="1.0.0",
        capabilities=[Capability(name="compatibility-capability")],
        skills=[Skill(id="compatibility-skill", name="Compatibility Skill")],
    )

    # Check Agent2Agent compatibility
    assert is_format_compatible(descriptor, DescriptorFormat.AGENT2AGENT) is True

    # Check JSON-LD compatibility (all descriptors are JSON-LD compatible)
    assert is_format_compatible(descriptor, DescriptorFormat.JSONLD) is True

    # Test invalid format
    with pytest.raises(ValueError):
        is_format_compatible(descriptor, "invalid-format")


def test_converter_classes():
    """Test the converter classes directly."""
    # Create a descriptor
    descriptor = AgentDescriptor(
        name="converter-agent",
        version="1.0.0",
        capabilities=[Capability(name="converter-capability")],
        skills=[Skill(id="converter-skill", name="Converter Skill")],
    )

    # Test Agent2Agent converter
    agent_card = Agent2AgentConverter.to_external(descriptor)
    assert agent_card["name"] == "converter-agent"
    assert "skills" in agent_card

    descriptor2 = Agent2AgentConverter.from_external(agent_card)
    assert descriptor2.name == "converter-agent"

    assert Agent2AgentConverter.is_compatible(descriptor) is True

    # Test JSON-LD converter
    jsonld_doc = JsonLdConverter.to_external(descriptor)
    assert jsonld_doc["name"] == "converter-agent"

    descriptor3 = JsonLdConverter.from_external(jsonld_doc)
    assert descriptor3.name == "converter-agent"

    assert JsonLdConverter.is_compatible(descriptor) is True
