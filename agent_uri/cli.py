#!/usr/bin/env python3
"""
Command Line Interface for agent-uri package.

This module provides a CLI interface for working with the agent:// protocol,
including URI parsing, agent discovery, and capability invocation.
"""

import argparse
import asyncio
import json
import sys
from typing import Any

from . import __version__
from .client import AgentClient
from .exceptions import AgentClientError
from .parser import AgentUriError, parse_agent_uri
from .resolver.resolver import AgentResolver


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="agent-uri",
        description="Command line interface for the agent:// protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse an agent URI
  agent-uri parse "agent://example.com/my-agent"

  # Resolve an agent URI to get its descriptor
  agent-uri resolve "agent://example.com/my-agent"

  # Invoke a capability on an agent
  agent-uri invoke "agent://example.com/my-agent/echo" --params '{"message": "Hello"}'

  # Get agent descriptor
  agent-uri describe "agent://example.com/my-agent"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse an agent URI")
    parse_parser.add_argument("uri", help="The agent URI to parse")
    parse_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve an agent URI")
    resolve_parser.add_argument("uri", help="The agent URI to resolve")
    resolve_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Invoke command
    invoke_parser = subparsers.add_parser("invoke", help="Invoke an agent capability")
    invoke_parser.add_argument("uri", help="The agent URI with capability")
    invoke_parser.add_argument(
        "--params", type=str, help="JSON parameters to send to the capability"
    )
    invoke_parser.add_argument(
        "--timeout", type=int, default=30, help="Request timeout in seconds"
    )
    invoke_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Describe command
    describe_parser = subparsers.add_parser("describe", help="Get agent descriptor")
    describe_parser.add_argument("uri", help="The agent URI to describe")
    describe_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Version command
    subparsers.add_parser("version", help="Show version information")

    return parser.parse_args()


def format_output(data: Any, json_format: bool = False) -> str:
    """Format output for display."""
    if json_format:
        return json.dumps(data, indent=2, default=str)
    else:
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{key}: {json.dumps(value, indent=2, default=str)}")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)
        else:
            return str(data)


async def cmd_parse(args: argparse.Namespace) -> int:
    """Handle the parse command."""
    try:
        uri = parse_agent_uri(args.uri)

        # Extract capability from path (if path has multiple segments,
        # last one might be capability)
        capability = None
        if uri.path and "/" in uri.path.strip("/"):
            path_parts = uri.path.strip("/").split("/")
            if len(path_parts) > 1:
                capability = path_parts[-1]

        result = {
            "scheme": uri.scheme,
            "transport": uri.transport,
            "host": uri.host,
            "port": uri.port,
            "path": uri.path,
            "capability": capability,
            "query": dict(uri.query) if uri.query else None,
            "fragment": uri.fragment,
        }

        print(format_output(result, args.json))
        return 0

    except AgentUriError as e:
        print(f"Error parsing URI: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


async def cmd_resolve(args: argparse.Namespace) -> int:
    """Handle the resolve command."""
    try:
        resolver = AgentResolver()
        descriptor, metadata = resolver.resolve(args.uri)

        result = {
            "descriptor": (
                descriptor.to_dict()
                if hasattr(descriptor, "to_dict")
                else str(descriptor)
            ),
            "metadata": metadata,
        }

        print(format_output(result, args.json))
        return 0

    except Exception as e:
        print(f"Error resolving URI: {e}", file=sys.stderr)
        return 1


async def cmd_invoke(args: argparse.Namespace) -> int:
    """Handle the invoke command."""
    try:
        # Parse parameters
        params = {}
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"Error parsing parameters JSON: {e}", file=sys.stderr)
                return 1

        # Parse URI to extract capability
        uri = parse_agent_uri(args.uri)

        # Extract capability from path
        capability = None
        if uri.path:
            path_parts = uri.path.strip("/").split("/")
            if path_parts and path_parts[-1]:
                capability = path_parts[-1]

        if not capability:
            print("Error: URI must include a capability path", file=sys.stderr)
            return 1

        # Create client and invoke
        client = AgentClient(timeout=args.timeout)
        result = await client.invoke(args.uri, params=params)

        print(format_output(result, args.json))
        return 0

    except AgentClientError as e:
        print(f"Error invoking capability: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


async def cmd_describe(args: argparse.Namespace) -> int:
    """Handle the describe command."""
    try:
        resolver = AgentResolver()
        descriptor, _ = resolver.resolve(args.uri)

        result = (
            descriptor.to_dict() if hasattr(descriptor, "to_dict") else str(descriptor)
        )
        print(format_output(result, args.json))
        return 0

    except Exception as e:
        print(f"Error getting agent descriptor: {e}", file=sys.stderr)
        return 1


def cmd_version(args: argparse.Namespace) -> int:
    """Handle the version command."""
    try:
        # Try to get version from package metadata
        from importlib.metadata import version

        pkg_version = version("agent-uri")
        print(f"agent-uri {pkg_version}")
    except Exception:
        # Fallback to version from __init__.py
        print(f"agent-uri {__version__}")

    return 0


async def async_main() -> int:
    """Main async entry point."""
    args = parse_arguments()

    if not args.command:
        print(
            "Error: No command specified. Use --help for usage information.",
            file=sys.stderr,
        )
        return 1

    # Dispatch to command handlers
    if args.command == "parse":
        return await cmd_parse(args)
    elif args.command == "resolve":
        return await cmd_resolve(args)
    elif args.command == "invoke":
        return await cmd_invoke(args)
    elif args.command == "describe":
        return await cmd_describe(args)
    elif args.command == "version":
        return cmd_version(args)
    else:
        print(f"Error: Unknown command '{args.command}'", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
