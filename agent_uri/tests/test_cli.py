"""
Tests for the CLI module.

This module contains comprehensive tests for the agent-uri CLI functionality.
"""

import json
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from ..cli import (
    async_main,
    cmd_describe,
    cmd_invoke,
    cmd_parse,
    cmd_resolve,
    cmd_version,
    format_output,
    parse_arguments,
)


class TestCLIArgumentParsing:
    """Test CLI argument parsing functionality."""

    def test_parse_arguments_version(self, monkeypatch):
        """Test version command argument parsing."""
        monkeypatch.setattr(sys, "argv", ["agent-uri", "version"])
        args = parse_arguments()
        assert args.command == "version"

    def test_parse_arguments_parse_basic(self, monkeypatch):
        """Test parse command with basic arguments."""
        monkeypatch.setattr(sys, "argv", ["agent-uri", "parse", "agent://example.com"])
        args = parse_arguments()
        assert args.command == "parse"
        assert args.uri == "agent://example.com"
        assert args.json is False

    def test_parse_arguments_parse_json(self, monkeypatch):
        """Test parse command with JSON output flag."""
        monkeypatch.setattr(
            sys, "argv", ["agent-uri", "parse", "--json", "agent://example.com"]
        )
        args = parse_arguments()
        assert args.command == "parse"
        assert args.uri == "agent://example.com"
        assert args.json is True

    def test_parse_arguments_invoke(self, monkeypatch):
        """Test invoke command argument parsing."""
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "agent-uri",
                "invoke",
                "agent://example.com/echo",
                "--params",
                '{"message": "test"}',
                "--timeout",
                "60",
            ],
        )
        args = parse_arguments()
        assert args.command == "invoke"
        assert args.uri == "agent://example.com/echo"
        assert args.params == '{"message": "test"}'
        assert args.timeout == 60


class TestCLIOutputFormatting:
    """Test CLI output formatting functionality."""

    def test_format_output_dict_text(self):
        """Test formatting dictionary output as text."""
        data = {"key1": "value1", "key2": 42, "key3": {"nested": "value"}}
        result = format_output(data, json_format=False)
        assert "key1: value1" in result
        assert "key2: 42" in result
        assert '"nested": "value"' in result

    def test_format_output_dict_json(self):
        """Test formatting dictionary output as JSON."""
        data = {"key1": "value1", "key2": 42}
        result = format_output(data, json_format=True)
        parsed = json.loads(result)
        assert parsed == data

    def test_format_output_string(self):
        """Test formatting string output."""
        data = "simple string"
        result = format_output(data, json_format=False)
        assert result == "simple string"

    def test_format_output_string_json(self):
        """Test formatting string output as JSON."""
        data = "simple string"
        result = format_output(data, json_format=True)
        assert json.loads(result) == "simple string"


class TestCLICommands:
    """Test individual CLI command implementations."""

    @pytest.mark.asyncio
    async def test_cmd_version(self):
        """Test version command implementation."""
        args = Mock()
        result = cmd_version(args)
        assert result == 0

    @pytest.mark.asyncio
    async def test_cmd_parse_valid_uri(self):
        """Test parse command with valid URI."""
        args = Mock()
        args.uri = "agent://example.com/my-agent"
        args.json = False

        with patch("builtins.print") as mock_print:
            result = await cmd_parse(args)
            assert result == 0
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            assert "scheme: agent" in output
            assert "host: example.com" in output

    @pytest.mark.asyncio
    async def test_cmd_parse_valid_uri_json(self):
        """Test parse command with valid URI and JSON output."""
        args = Mock()
        args.uri = "agent+https://example.com:8080/my-agent/echo"
        args.json = True

        with patch("builtins.print") as mock_print:
            result = await cmd_parse(args)
            assert result == 0
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            parsed = json.loads(output)
            assert parsed["scheme"] == "agent"
            assert parsed["transport"] == "https"
            assert parsed["host"] == "example.com"
            assert parsed["port"] == 8080
            assert parsed["capability"] == "echo"

    @pytest.mark.asyncio
    async def test_cmd_parse_invalid_uri(self):
        """Test parse command with invalid URI."""
        args = Mock()
        args.uri = "http://example.com"  # Not an agent:// URI
        args.json = False

        with patch("builtins.print") as mock_print:
            result = await cmd_parse(args)
            assert result == 1
            mock_print.assert_called_once()
            assert "Error parsing URI" in mock_print.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_invoke_missing_capability(self):
        """Test invoke command with URI missing capability."""
        args = Mock()
        args.uri = "agent://example.com"  # No capability path
        args.params = None
        args.timeout = 30

        with patch("builtins.print") as mock_print:
            result = await cmd_invoke(args)
            assert result == 1
            mock_print.assert_called_once()
            assert "must include a capability path" in mock_print.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_invoke_invalid_params_json(self):
        """Test invoke command with invalid JSON parameters."""
        args = Mock()
        args.uri = "agent://example.com/echo"
        args.params = '{"invalid": json}'  # Invalid JSON
        args.timeout = 30

        with patch("builtins.print") as mock_print:
            result = await cmd_invoke(args)
            assert result == 1
            mock_print.assert_called_once()
            assert "Error parsing parameters JSON" in mock_print.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_resolve_error(self):
        """Test resolve command error handling."""
        args = Mock()
        args.uri = "agent://nonexistent.example.com"
        args.json = False

        with patch("builtins.print") as mock_print:
            result = await cmd_resolve(args)
            assert result == 1
            mock_print.assert_called_once()
            assert "Error resolving URI" in mock_print.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_describe_error(self):
        """Test describe command error handling."""
        args = Mock()
        args.uri = "agent://nonexistent.example.com"
        args.json = False

        with patch("builtins.print") as mock_print:
            result = await cmd_describe(args)
            assert result == 1
            mock_print.assert_called_once()
            assert "Error getting agent descriptor" in mock_print.call_args[0][0]


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    @pytest.mark.asyncio
    async def test_async_main_no_command(self):
        """Test main function with no command specified."""
        with patch("agent_uri.cli.parse_arguments") as mock_parse:
            mock_args = Mock()
            mock_args.command = None
            mock_parse.return_value = mock_args

            with patch("builtins.print") as mock_print:
                result = await async_main()
                assert result == 1
                mock_print.assert_called_once()
                assert "No command specified" in mock_print.call_args[0][0]

    @pytest.mark.asyncio
    async def test_async_main_unknown_command(self):
        """Test main function with unknown command."""
        with patch("agent_uri.cli.parse_arguments") as mock_parse:
            mock_args = Mock()
            mock_args.command = "unknown"
            mock_parse.return_value = mock_args

            with patch("builtins.print") as mock_print:
                result = await async_main()
                assert result == 1
                mock_print.assert_called_once()
                assert "Unknown command" in mock_print.call_args[0][0]

    @pytest.mark.asyncio
    async def test_async_main_version_command(self):
        """Test main function with version command."""
        with patch("agent_uri.cli.parse_arguments") as mock_parse:
            mock_args = Mock()
            mock_args.command = "version"
            mock_parse.return_value = mock_args

            result = await async_main()
            assert result == 0

    @pytest.mark.asyncio
    async def test_async_main_parse_command(self):
        """Test main function with parse command."""
        with patch("agent_uri.cli.parse_arguments") as mock_parse:
            mock_args = Mock()
            mock_args.command = "parse"
            mock_args.uri = "agent://example.com"
            mock_args.json = False
            mock_parse.return_value = mock_args

            with patch("builtins.print"):
                result = await async_main()
                assert result == 0


class TestCLICommandLine:
    """Test CLI via command line interface."""

    def test_cli_version_command_line(self):
        """Test CLI version command via command line."""
        result = subprocess.run(
            [sys.executable, "-m", "agent_uri.cli", "version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "agent-uri" in result.stdout
        # Should show some version number
        assert any(char.isdigit() for char in result.stdout)

    def test_cli_parse_command_line(self):
        """Test CLI parse command via command line."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agent_uri.cli",
                "parse",
                "agent://example.com/test",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["scheme"] == "agent"
        assert data["host"] == "example.com"

    def test_cli_help_command_line(self):
        """Test CLI help command via command line."""
        result = subprocess.run(
            [sys.executable, "-m", "agent_uri.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "agent:// protocol" in result.stdout
        assert "parse" in result.stdout
        assert "invoke" in result.stdout

    def test_cli_invalid_command_line(self):
        """Test CLI with invalid command via command line."""
        result = subprocess.run(
            [sys.executable, "-m", "agent_uri.cli", "invalid-command"],
            capture_output=True,
            text=True,
        )
        # argparse returns 2 for invalid arguments, not 1
        assert result.returncode == 2
        assert "invalid choice" in result.stderr


class TestCLIErrorHandling:
    """Test CLI error handling scenarios."""

    @pytest.mark.asyncio
    async def test_cmd_parse_capability_extraction(self):
        """Test parse command capability extraction logic."""
        # Test with capability in path
        args = Mock()
        args.uri = "agent://example.com/agent/echo"
        args.json = True

        with patch("builtins.print") as mock_print:
            result = await cmd_parse(args)
            assert result == 0
            output = json.loads(mock_print.call_args[0][0])
            assert output["capability"] == "echo"

        # Test without capability
        args.uri = "agent://example.com/agent"
        with patch("builtins.print") as mock_print:
            result = await cmd_parse(args)
            assert result == 0
            output = json.loads(mock_print.call_args[0][0])
            assert output["capability"] is None

    @pytest.mark.asyncio
    async def test_cmd_invoke_valid_capability_path(self):
        """Test invoke command with valid capability path."""
        args = Mock()
        args.uri = "agent://example.com/my-agent/echo"
        args.params = None
        args.timeout = 30

        # Mock the client to avoid actual network calls
        from unittest.mock import AsyncMock

        with patch("agent_uri.cli.AgentClient") as mock_client_class:
            mock_client = Mock()
            # Make invoke an async mock since it's awaited in the CLI
            mock_client.invoke = AsyncMock(return_value={"result": "test response"})
            mock_client_class.return_value = mock_client

            with patch("builtins.print"):
                result = await cmd_invoke(args)
                assert result == 0
                mock_client.invoke.assert_called_once_with(
                    "agent://example.com/my-agent/echo", params={}
                )
