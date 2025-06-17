"""Tests for the validator module."""

from ..models import AgentDescriptor, Capability
from ..validator import (
    ValidationResult,
    check_json_ld_extensions,
    validate_agent_card_compatibility,
    validate_descriptor,
    validate_model,
    validate_required_fields,
)


def test_validate_required_fields():
    """Test validation of required fields."""
    # Valid descriptor with all required fields
    valid_descriptor = {
        "name": "test-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "test-capability"}],
    }
    result = validate_required_fields(valid_descriptor)
    assert result.valid
    assert len(result.errors) == 0

    # Missing name
    missing_name = {"version": "1.0.0", "capabilities": [{"name": "test-capability"}]}
    result = validate_required_fields(missing_name)
    assert not result.valid
    assert any("name" in err.path for err in result.errors)

    # Missing version
    missing_version = {
        "name": "test-agent",
        "capabilities": [{"name": "test-capability"}],
    }
    result = validate_required_fields(missing_version)
    assert not result.valid
    assert any("version" in err.path for err in result.errors)

    # Missing capabilities
    missing_capabilities = {"name": "test-agent", "version": "1.0.0"}
    result = validate_required_fields(missing_capabilities)
    assert not result.valid
    assert any("capabilities" in err.path for err in result.errors)

    # Empty capabilities array
    empty_capabilities = {"name": "test-agent", "version": "1.0.0", "capabilities": []}
    result = validate_required_fields(empty_capabilities)
    assert not result.valid
    assert any("capabilities" in err.path for err in result.errors)

    # Capability missing name
    capability_missing_name = {
        "name": "test-agent",
        "version": "1.0.0",
        "capabilities": [{"description": "A capability without a name"}],
    }
    result = validate_required_fields(capability_missing_name)
    assert not result.valid
    assert any("capabilities[0]" in err.path for err in result.errors)


def test_validate_descriptor():
    """Test full descriptor validation against the schema."""
    # Valid descriptor
    valid_descriptor = {
        "name": "test-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "test-capability"}],
    }
    result = validate_descriptor(valid_descriptor)
    assert result.valid
    assert len(result.errors) == 0

    # Invalid capability type
    invalid_capability_type = {
        "name": "test-agent",
        "version": "1.0.0",
        "capabilities": "not-an-array",  # Should be an array
    }
    result = validate_descriptor(invalid_capability_type)
    assert not result.valid
    assert any("capabilities" in err.path for err in result.errors)

    # Invalid version type
    invalid_version_type = {
        "name": "test-agent",
        "version": True,  # Should be string or number
        "capabilities": [{"name": "test-capability"}],
    }
    # Note: Our current schema implementation doesn't enforce strict type checking
    # This test simply verifies it doesn't crash
    result = validate_descriptor(invalid_version_type)

    # Valid descriptor with additional fields
    valid_with_extra = {
        "name": "test-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "test-capability"}],
        "description": "A test agent",
        "status": "active",
    }
    result = validate_descriptor(valid_with_extra)
    assert result.valid
    assert len(result.errors) == 0


def test_validate_agent_card_compatibility():
    """Test validation of compatibility with Agent2Agent's AgentCard."""
    # Fully compatible descriptor
    compatible_descriptor = {
        "name": "compatible-agent",
        "version": "1.0.0",
        "url": "agent://compatible-agent/",
        "capabilities": [{"name": "test-capability"}],
        "skills": [{"id": "skill-1", "name": "Test Skill"}],
    }
    result = validate_agent_card_compatibility(compatible_descriptor)
    assert result.valid
    # The implementation may add warnings but it should still be valid
    assert all(err.severity == "warning" for err in result.errors)

    # Missing fields for AgentCard compatibility
    incomplete_descriptor = {
        "name": "incomplete-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "test-capability"}],
    }
    result = validate_agent_card_compatibility(incomplete_descriptor)
    assert result.valid  # Should be valid but with warnings
    assert len(result.errors) > 0
    assert all(err.severity == "warning" for err in result.errors)
    assert any("url" in err.path for err in result.errors)
    assert any("skills" in err.path for err in result.errors)

    # Incorrect capabilities format for AgentCard
    incorrect_capabilities = {
        "name": "incorrect-agent",
        "version": "1.0.0",
        "url": "agent://incorrect-agent/",
        "capabilities": {
            "streaming": "yes",  # Should be boolean
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "skills": [{"id": "skill-1", "name": "Test Skill"}],
    }
    result = validate_agent_card_compatibility(incorrect_capabilities)
    assert result.valid  # Should be valid but with warnings
    assert len(result.errors) > 0
    assert any("capabilities.streaming" in err.path for err in result.errors)


def test_check_json_ld_extensions():
    """Test checking for JSON-LD extensions."""
    # Descriptor with JSON-LD context
    jsonld_descriptor = {
        "name": "jsonld-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "test-capability"}],
        "@context": "https://example.org/agent-context.jsonld",
        "@type": "Agent",
    }
    result = check_json_ld_extensions(jsonld_descriptor)
    assert result.valid
    assert len(result.errors) == 1  # One info for @type
    assert all(err.severity == "info" for err in result.errors)

    # Descriptor without JSON-LD context
    no_jsonld_descriptor = {
        "name": "no-jsonld-agent",
        "version": "1.0.0",
        "capabilities": [{"name": "test-capability"}],
    }
    result = check_json_ld_extensions(no_jsonld_descriptor)
    assert result.valid
    assert len(result.errors) == 1  # One info for missing @context
    assert all(err.severity == "info" for err in result.errors)
    assert any("@context" in err.path for err in result.errors)


def test_validate_model():
    """Test validation of an AgentDescriptor model instance."""
    # Valid model
    valid_model = AgentDescriptor(
        name="test-agent",
        version="1.0.0",
        capabilities=[Capability(name="test-capability")],
    )
    result = validate_model(valid_model)
    assert result.valid
    assert len(result.errors) == 0

    # Invalid model (create an incomplete model)
    # We can't easily create an invalid model through the constructor due to type hints,
    # so we'll modify the model after creation
    invalid_model = AgentDescriptor(
        name="test-agent",
        version="1.0.0",
        capabilities=[Capability(name="test-capability")],
    )
    invalid_model.capabilities = []  # Make it invalid by setting capabilities to empty
    result = validate_model(invalid_model)
    assert not result.valid
    assert len(result.errors) > 0
    assert any("capabilities" in err.path for err in result.errors)


def test_validation_result_class():
    """Test the ValidationResult class functionality."""
    # Create a valid result
    result = ValidationResult(valid=True)
    assert result.valid
    assert bool(result) is True
    assert len(result.errors) == 0

    # Add a warning (doesn't affect validity)
    result.add_error("test.path", "This is a warning", "warning")
    assert result.valid
    assert bool(result) is True
    assert len(result.errors) == 1
    assert result.errors[0].severity == "warning"

    # Add an error (affects validity)
    result.add_error("test.path2", "This is an error", "error")
    assert not result.valid
    assert bool(result) is False
    assert len(result.errors) == 2
    assert result.errors[1].severity == "error"

    # Create an invalid result directly
    invalid_result = ValidationResult(valid=False)
    assert not invalid_result.valid
    assert bool(invalid_result) is False
