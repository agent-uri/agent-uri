# Agent URI: Future Enhancements

This document outlines features specified in the Agent URI RFC (`draft-narvaneni-agent-uri-00.md`) that are not yet implemented in the reference implementation. These items represent planned future work.

## URI Handling

- [ ] **URI Builder Pattern**: Implement a builder pattern for the AgentUri class to construct URIs with a fluent interface.
- [ ] **Enhanced URI Query Parameters**: Improve handling of complex query parameters, including arrays and objects.

## Resolution Framework

- [ ] **DID Resolution**: Implement the DID resolution mechanism described in the RFC for decentralized identifiers.
- [ ] **Resolution Hooks**: Add support for custom resolution hooks and middleware.
- [ ] **Multiple Authority Types**: Enhance the resolver to handle different authority types (DNS, IP, DID) with specialized resolvers.

## Transport Bindings

- [ ] **Unix Socket Transport**: Implement the Unix Socket transport for local, high-performance agent communication.
- [ ] **Matrix Transport**: Implement the Matrix transport for federated, asynchronous communication.
- [ ] **Custom Transport Factory**: Create a transport factory system for easier registration of custom transports.
- [ ] **Transport Fallback Chain**: Implement a configurable fallback chain for transport selection.

## Capability Framework

- [ ] **JSON-LD Support**: Add support for JSON-LD context handling for semantic interoperability.
- [ ] **Capability Discovery Protocol**: Implement the capability discovery protocol for automated agent interaction.
- [ ] **Capability Relation Mapping**: Support for defining relationships between capabilities.
- [ ] **Input/Output Schema Validation**: Enhanced validation against JSON Schema for capability parameters.

## Security Features

- [ ] **OAuth2 Authentication**: Complete OAuth2 authentication flow implementation.
- [ ] **JWT Support**: Add support for JWT tokens for authentication.
- [ ] **mTLS Authentication**: Implement mutual TLS authentication.
- [ ] **Delegation Chains**: Implement delegation chain metadata and verification.
- [ ] **Capability-Based Access Control**: Implement fine-grained access control based on capabilities.
- [ ] **Security Policy Framework**: Add a configurable security policy framework.

## Interaction Patterns

- [ ] **Delegated Invocation**: Implement the ability for agents to call other agents on behalf of a user.
- [ ] **Asynchronous Notifications**: Support for asynchronous event notifications.
- [ ] **Enhanced Session Management**: Implement advanced session management with context preservation.
- [ ] **Multi-Agent Orchestration**: Add support for coordinating multiple agents in a workflow.

## Error Handling

- [ ] **RFC7807 Problem Details**: Complete implementation of RFC7807 Problem Details for error responses.
- [ ] **Standardized Error System**: Implement a comprehensive error system with error codes.
- [ ] **Error Chain Tracking**: Add support for tracking error chains across agent invocations.

## Protocol Integrations

- [ ] **Agent2Agent Integration**: Implement interoperability with Google's Agent2Agent protocol.
- [ ] **Model Context Protocol Integration**: Implement interoperability with Anthropic's MCP.
- [ ] **Integration Adapters Framework**: Create a framework for building integration adapters.

## Developer Tools

- [ ] **CLI Tools**: Implement command-line tools for working with Agent URI.
- [ ] **Conformance Test Suite**: Create a test suite for checking protocol compliance.
- [ ] **Agent Scaffolding Tools**: Add tools for generating agent skeletons.
- [ ] **Documentation Generator**: Build a tool to generate API documentation from code.

## Language Support

- [ ] **JavaScript/TypeScript SDK**: Create JavaScript/TypeScript implementations of the protocol.
- [ ] **Go SDK**: Create a Go implementation of the protocol.
- [ ] **Rust SDK**: Create a Rust implementation of the protocol.
- [ ] **Java SDK**: Create a Java implementation of the protocol.

## Ecosystem Support

- [ ] **Agent Registry**: Implement a centralized agent registry for discovery.
- [ ] **Agent Analytics**: Add support for tracking agent usage and performance.
- [ ] **Agent Verification Framework**: Implement a verification framework for trusted agents.
