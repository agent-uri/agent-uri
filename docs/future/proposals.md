# Future Enhancement Proposals for agent-uri

This document outlines proposed enhancements to the agent-uri addressing scheme while maintaining its core focus as a URI-based addressing and resolution protocol, not a full platform.

## Core Principle

agent-uri should remain focused on its fundamental purpose: **addressing, resolving, and connecting to agents**. Like HTTP, it should provide the foundation for higher-level applications without implementing application logic itself.

## High-Priority Enhancements

### 1. Protocol Bridge Layer
**Purpose**: Enable agent-uri to serve as a universal addressing layer across agent ecosystems.

**Implementation**:
- URI translation between `agent://`, Google A2A AgentCard URIs, and Anthropic MCP server addresses
- Bidirectional mapping: `agent://translator.example.com/` ↔ A2A task endpoint
- MCP server registration through agent-uri descriptors
- Maintain agent-uri's flexibility while enabling cross-protocol discovery

### 2. Transport Protocol Expansion
**Purpose**: Support more transport bindings for broader agent connectivity.

**New Transports**:
- `agent+grpc://` - High-performance binary protocol
- `agent+graphql://` - Flexible querying interface
- `agent+unix://` - Local inter-process communication
- `agent+matrix://` - Federated, decentralized networks
- `agent+ipc://` - Named pipes and shared memory

**Benefits**: Allows the same agent URI to work across different network environments and performance requirements.

### 3. Enhanced Resolution Framework
**Purpose**: Improve how agent URIs map to concrete endpoints.

**Features**:
- Multiple resolution strategies with fallback chains
- Caching layer for performance (similar to DNS caching)
- Load balancing across multiple agent instances
- Geographic routing (route to nearest agent instance)
- Version-aware resolution (`agent://translator.example.com@v2.1/`)

### 4. Semantic Capability Routing
**Purpose**: Enable intelligent URI resolution based on capability matching.

**Implementation**:
- Capability-aware path resolution: `/translate/text` automatically routes to translation-capable agents
- Semantic query parameters: `?capability=translation&language_pair=en-fr`
- Embedding-based capability matching for natural language queries
- Automatic capability composition: chain compatible agents transparently

### 5. DID Integration Completion
**Purpose**: Full decentralized identity support for agent addressing.

**Features**:
- Complete `did:web`, `did:key`, and `did:peer` resolution
- Verifiable agent identity and capability claims
- Cryptographic proof of agent authority
- Distributed trust without central registries

## Framework Integration Enhancements

### 6. SDK Library Ecosystem
**Purpose**: Native agent-uri support in popular AI frameworks.

**Target Integrations**:
- **LangChain**: Custom agent executor that resolves agent-uri addresses
- **AutoGen**: Agent discovery via agent-uri instead of hardcoded endpoints
- **CrewAI**: Dynamic agent recruitment using capability-based URIs
- **Semantic Kernel**: Plugin that treats agent URIs as semantic functions
- **LlamaIndex**: Query engines that can invoke external agents

### 7. CLI Discovery Tools
**Purpose**: Command-line utilities for agent URI exploration (similar to `dig` for DNS).

**Tools**:
- `agent-resolve` - Resolve URIs to endpoints and capabilities
- `agent-discover` - Find agents by capability or authority
- `agent-test` - Test agent connectivity and response
- `agent-trace` - Debug resolution and transport issues
- `agent-bench` - Performance testing for agent URIs

## Discovery & Registry Enhancements

### 8. Distributed Agent Registry
**Purpose**: DNS-like service for agent URI resolution.

**Features**:
- Hierarchical agent namespace (like DNS zones)
- Distributed resolution with caching
- Capability-based search and discovery
- Agent health monitoring and status
- Federated registries (no single point of control)

### 9. Capability Ontology
**Purpose**: Standardized vocabulary for agent capabilities and paths.

**Components**:
- Standard capability taxonomy (translation, analysis, generation, etc.)
- URI path conventions for common capabilities
- Parameter schemas for capability invocation
- Capability composition rules and patterns

### 10. Security Enhancements
**Purpose**: Secure agent addressing without becoming an authentication platform.

**Features**:
- URI-based capability delegation chains
- Cryptographic agent identity verification
- Transport-agnostic security metadata in descriptors
- Agent certificate and trust management
- Secure resolution (prevent agent spoofing)

## Developer Experience

### 11. Enhanced Documentation
**Purpose**: Clear guidance for implementing and using agent-uri.

**Deliverables**:
- Progressive implementation guide (minimal → full)
- Transport-specific examples and best practices
- Capability modeling guidelines
- Security implementation patterns
- Migration guides from other addressing schemes

### 12. Testing and Validation Tools
**Purpose**: Ensure agent-uri implementations work correctly.

**Tools**:
- Conformance test suite for agent-uri parsers
- Transport compatibility testing
- Descriptor validation tools
- Resolution behavior verification
- Performance benchmarking suite

## Implementation Roadmap

### Phase 1: Core Protocol
1. Complete missing transport implementations
2. Enhanced resolution framework with caching
3. Protocol bridge layer for A2A/MCP compatibility

### Phase 2: Ecosystem Integration
1. Framework SDK integrations
2. CLI discovery tools
3. Capability ontology specification

### Phase 3: Advanced Features
1. Semantic capability routing
2. Complete DID integration
3. Distributed registry implementation

### Phase 4: Maturity
1. Security enhancements
2. Performance optimizations
3. Conformance testing program

## Success Metrics

- **Adoption**: Number of agent frameworks supporting agent-uri natively
- **Interoperability**: Cross-protocol agent discovery and invocation
- **Performance**: Resolution time and transport efficiency
- **Ecosystem**: Growth of publicly discoverable agent URIs

## Anti-Patterns to Avoid

- **Session Management**: Applications should handle state, not the URI scheme
- **Workflow Orchestration**: Multi-agent coordination is application logic
- **Business Logic**: agent-uri should not implement domain-specific functionality
- **Platform Lock-in**: Remain transport and vendor agnostic
- **Complexity Creep**: Keep the protocol simple and focused

---

The goal is to make agent-uri the foundational addressing layer that enables a thriving, interoperable agent ecosystem while remaining focused on its core competency: addressing and resolution.
