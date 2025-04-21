# Agent URI Protocol Specifications

This directory contains technical specifications for the `agent://` protocol, as implemented in the reference implementation.

## Specification Documents

- [URI Schema Definition](uri-schema.md) - Formal definition of the `agent://` URI syntax and semantics
- [Agent Descriptor Schema](agent-descriptor-schema.json) - JSON Schema for the agent.json descriptor format

## Relationships Between Components

The `agent://` protocol is built on a layered architecture:

1. **URI Layer** - The addressing scheme using `agent://` URIs
2. **Resolution Layer** - The process of resolving URIs to network endpoints
3. **Transport Layer** - The communication protocols used for agent invocation
4. **Descriptor Layer** - The metadata format describing agent capabilities
5. **Security Layer** - Authentication, authorization, and delegation mechanisms

## Specification Versioning

These specifications follow a versioning scheme aligned with the reference implementation:

- Major version changes indicate backward-incompatible changes
- Minor version changes indicate feature additions in a backward-compatible manner
- Patch version changes indicate backward-compatible bug fixes

## Compliance Testing

The reference implementation includes a conformance test suite in `tools/conformance/` that can be used to verify compliance with these specifications.

A compliant implementation should:

1. Parse and validate `agent://` URIs according to the URI schema
2. Support resolution of agent descriptors
3. Implement at least one transport binding (e.g., HTTPS)
4. Support parsing and generating valid agent descriptors

## Extensions

The `agent://` protocol is designed to be extensible. Implementations may add:

- Additional transport bindings
- Extended descriptor fields
- Enhanced security mechanisms
- Custom resolution strategies

Extensions should be documented clearly and should not break compatibility with the core specification.
