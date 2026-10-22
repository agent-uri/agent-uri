"""Tests for the descriptor validator (draft-narvaneni-agent-uri-03)."""

from ..models import AgentDescriptor, Skill
from ..validator import (
    ValidationResult,
    check_json_ld_extensions,
    validate_agent_card_compatibility,
    validate_descriptor,
    validate_model,
    validate_required_fields,
)


def _skill_dict() -> dict:
    return {"id": "echo", "name": "echo", "description": "Echo skill"}


def test_validate_required_fields_success():
    descriptor = {
        "name": "test-agent",
        "version": "1.0.0",
        "skills": [_skill_dict()],
    }
    result = validate_required_fields(descriptor)
    assert result.valid
    assert len(result.errors) == 0


def test_validate_required_fields_missing_name():
    result = validate_required_fields({"version": "1.0.0", "skills": [_skill_dict()]})
    assert not result.valid
    assert any("name" in err.path for err in result.errors)


def test_validate_required_fields_missing_version():
    result = validate_required_fields({"name": "test-agent", "skills": [_skill_dict()]})
    assert not result.valid
    assert any("version" in err.path for err in result.errors)


def test_validate_required_fields_missing_skills():
    result = validate_required_fields({"name": "test-agent", "version": "1.0.0"})
    assert not result.valid
    assert any("skills" in err.path for err in result.errors)


def test_validate_required_fields_empty_skills():
    result = validate_required_fields(
        {"name": "test-agent", "version": "1.0.0", "skills": []}
    )
    assert not result.valid
    assert any("skills" in err.path for err in result.errors)


def test_validate_required_fields_skill_missing_id():
    result = validate_required_fields(
        {
            "name": "test-agent",
            "version": "1.0.0",
            "skills": [{"name": "echo", "description": "x"}],
        }
    )
    assert not result.valid
    assert any("skills[0]" in err.path for err in result.errors)


def test_validate_conformance_level_bounds():
    bad = {
        "name": "x",
        "version": "1.0.0",
        "skills": [_skill_dict()],
        "conformanceLevel": 7,
    }
    result = validate_required_fields(bad)
    assert not result.valid
    assert any("conformanceLevel" in err.path for err in result.errors)


def test_validate_status_enum():
    bad = {
        "name": "x",
        "version": "1.0.0",
        "skills": [_skill_dict()],
        "status": "weird",
    }
    result = validate_required_fields(bad)
    assert not result.valid
    assert any("status" in err.path for err in result.errors)


def test_validate_descriptor_valid():
    descriptor = {
        "name": "test-agent",
        "version": "1.0.0",
        "skills": [_skill_dict()],
    }
    result = validate_descriptor(descriptor)
    assert result.valid


def test_validate_descriptor_invalid_skills_type():
    bad = {"name": "x", "version": "1.0.0", "skills": "not-an-array"}
    result = validate_descriptor(bad)
    assert not result.valid
    assert any("skills" in err.path for err in result.errors)


def test_validate_descriptor_with_extras():
    valid = {
        "name": "test-agent",
        "version": "1.0.0",
        "skills": [_skill_dict()],
        "description": "desc",
        "status": "active",
    }
    assert validate_descriptor(valid).valid


def test_validate_agent_card_compatibility_complete():
    compatible = {
        "name": "compatible-agent",
        "version": "1.0.0",
        "url": "agent://compatible-agent/",
        "description": "An AgentCard compatible agent",
        "skills": [_skill_dict()],
    }
    result = validate_agent_card_compatibility(compatible)
    assert result.valid
    # Warnings only
    assert all(err.severity == "warning" for err in result.errors)


def test_validate_agent_card_compatibility_incomplete():
    incomplete = {
        "name": "x",
        "version": "1.0.0",
        "skills": [_skill_dict()],
    }
    result = validate_agent_card_compatibility(incomplete)
    assert result.valid
    assert len(result.errors) > 0
    assert any("url" in err.path for err in result.errors)


def test_check_json_ld_extensions_with_context():
    descriptor = {
        "name": "jsonld-agent",
        "version": "1.0.0",
        "skills": [_skill_dict()],
        "@context": "https://example.org/agent-context.jsonld",
        "@type": "Agent",
    }
    result = check_json_ld_extensions(descriptor)
    assert result.valid
    # @type is surfaced as an informational entry.
    assert any("@type" in err.path for err in result.errors)


def test_check_json_ld_extensions_without_context():
    descriptor = {
        "name": "no-jsonld-agent",
        "version": "1.0.0",
        "skills": [_skill_dict()],
    }
    result = check_json_ld_extensions(descriptor)
    assert result.valid
    assert any("@context" in err.path for err in result.errors)


def test_validate_model_valid():
    model = AgentDescriptor(
        name="test-agent",
        version="1.0.0",
        skills=[Skill(id="echo", name="echo", description="Echo skill")],
    )
    result = validate_model(model)
    assert result.valid
    assert len(result.errors) == 0


def test_validate_model_empty_skills():
    model = AgentDescriptor(
        name="x",
        version="1.0.0",
        skills=[Skill(id="echo", name="echo", description="e")],
    )
    model.skills = []
    result = validate_model(model)
    assert not result.valid
    assert any("skills" in err.path for err in result.errors)


def test_validate_model_skill_missing_description():
    model = AgentDescriptor(
        name="x",
        version="1.0.0",
        skills=[Skill(id="echo", name="echo", description="")],
    )
    result = validate_model(model)
    assert not result.valid
    assert any("skills[0].description" in err.path for err in result.errors)


def test_validation_result_behavior():
    result = ValidationResult(valid=True)
    assert bool(result) is True

    result.add_error("p", "warn", "warning")
    assert result.valid
    assert len(result.errors) == 1

    result.add_error("p2", "err", "error")
    assert not result.valid
    assert bool(result) is False
