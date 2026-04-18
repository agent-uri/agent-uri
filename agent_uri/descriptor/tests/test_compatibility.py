"""
Tests for Agent2Agent and JSON-LD compatibility converters.

Aligned with draft-narvaneni-agent-uri-03: descriptor ``skills[]`` maps
1:1 to AgentCard ``skills``.
"""

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
from ..models import AgentDescriptor, Authentication, Provider, Skill


@pytest.fixture
def sample_descriptor() -> AgentDescriptor:
    return AgentDescriptor(
        name="test-agent",
        version="1.0.0",
        description="A test agent",
        url="https://test-agent.example.com/agent.json",
        documentation_url="https://test-agent.example.com/docs",
        provider=Provider(organization="Test Org", url="https://test-org.example.com"),
        authentication=Authentication(schemes=["bearer", "apiKey"]),
        skills=[
            Skill(
                id="echo",
                name="echo",
                description="Echo input back",
                tags=["test"],
                streaming=False,
            ),
            Skill(
                id="stream",
                name="stream",
                description="Stream chunks",
                streaming=True,
                streaming_format="sse",
            ),
        ],
    )


class TestAgent2AgentConverter:
    def test_to_external_basic_fields(self, sample_descriptor):
        card = Agent2AgentConverter.to_external(sample_descriptor)
        assert card["name"] == "test-agent"
        assert card["version"] == "1.0.0"
        assert card["description"] == "A test agent"
        assert card["url"] == "https://test-agent.example.com/agent.json"

    def test_to_external_provider(self, sample_descriptor):
        card = Agent2AgentConverter.to_external(sample_descriptor)
        assert card["provider"]["organization"] == "Test Org"
        assert card["provider"]["url"] == "https://test-org.example.com"

    def test_to_external_skills(self, sample_descriptor):
        card = Agent2AgentConverter.to_external(sample_descriptor)
        assert len(card["skills"]) == 2
        assert {s["id"] for s in card["skills"]} == {"echo", "stream"}

    def test_to_external_capabilities_flags(self, sample_descriptor):
        """AgentCard ``capabilities`` booleans derive from our skills."""
        card = Agent2AgentConverter.to_external(sample_descriptor)
        assert card["capabilities"]["streaming"] is True
        assert card["capabilities"]["pushNotifications"] is False

    def test_from_external_roundtrip(self, sample_descriptor):
        card = Agent2AgentConverter.to_external(sample_descriptor)
        rt = Agent2AgentConverter.from_external(card)
        assert rt.name == sample_descriptor.name
        assert rt.version == sample_descriptor.version
        assert rt.description == sample_descriptor.description
        assert rt.provider.organization == "Test Org"
        assert {s.id for s in rt.skills} == {"echo", "stream"}

    def test_from_external_missing_required(self):
        with pytest.raises(ValueError, match="Missing required field"):
            Agent2AgentConverter.from_external({"name": "x", "version": "1"})

    def test_is_compatible(self, sample_descriptor):
        assert Agent2AgentConverter.is_compatible(sample_descriptor) is True

    def test_is_not_compatible_when_no_skills(self):
        bad = AgentDescriptor(name="x", version="1.0.0", skills=[])
        assert Agent2AgentConverter.is_compatible(bad) is False


class TestJsonLdConverter:
    def test_to_external_adds_context(self, sample_descriptor):
        sample_descriptor.context = ["https://example.com/context.json"]
        out = JsonLdConverter.to_external(sample_descriptor)
        assert "@context" in out
        assert out["@context"] == ["https://example.com/context.json"]

    def test_from_external_roundtrip(self, sample_descriptor):
        sample_descriptor.context = ["https://example.com/ctx.json"]
        jsonld = JsonLdConverter.to_external(sample_descriptor)
        rt = JsonLdConverter.from_external(jsonld)
        assert rt.name == sample_descriptor.name
        assert rt.version == sample_descriptor.version

    def test_is_compatible(self, sample_descriptor):
        assert JsonLdConverter.is_compatible(sample_descriptor) is True


class TestConversionFunctions:
    def test_to_format_agent2agent(self, sample_descriptor):
        out = to_format(sample_descriptor, DescriptorFormat.AGENT2AGENT)
        assert out["name"] == "test-agent"

    def test_from_format_agent2agent(self, sample_descriptor):
        card = to_agent_card(sample_descriptor)
        rt = from_format(card, DescriptorFormat.AGENT2AGENT)
        assert rt.name == "test-agent"

    def test_is_format_compatible(self, sample_descriptor):
        assert is_format_compatible(sample_descriptor, DescriptorFormat.AGENT2AGENT)

    def test_is_agent_card_compatible(self, sample_descriptor):
        assert is_agent_card_compatible(sample_descriptor) is True

    def test_to_agent_card_shortcut(self, sample_descriptor):
        card = to_agent_card(sample_descriptor)
        assert card["name"] == "test-agent"
        rt = from_agent_card(card)
        assert rt.name == "test-agent"
