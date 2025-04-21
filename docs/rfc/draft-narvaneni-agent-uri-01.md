---
title: "The agent:// Protocol -- A URI-Based Framework for Interoperable Agents"
abbrev: "agent-uri"
category: exp
docName: draft-narvaneni-agent-uri-01
ipr: trust200902
area: Applications
workgroup: Independent Submission
keyword: Internet-Draft
submissionType: independent
date: 2025-04-21

stand_alone: yes
pi: [toc, sortrefs, symrefs]

author:
 -
    ins: Y. Narvaneni
    name: Yaswanth Narvaneni
    organization: Independent Researcher
    email: yaswanth+ietf@gmail.com
    city: London
    country: United Kingdom

normative:
  RFC3986:
  RFC2119:
  RFC6570:
  RFC9110:
  RFC6750:
  RFC7519:
  RFC9457:
  RFC8705:
  RFC8174:
  RFC7595:
  JSON-LD11:
    title: "JSON-LD 1.1: A JSON-based Serialization for Linked Data"
    author:
      - 
        ins: M. Sporny
      -
        ins: D. Longley
      -
        ins: G. Kellogg
      - 
        ins: M. Lanthaler
      -
        ins: P. Champin
      -
        ins: N. Lindstrom
    date: 2020-07
    seriesinfo:
      W3C: Recommendation
    target: https://www.w3.org/TR/json-ld11/
  DID-CORE:
    title: "Decentralized Identifiers (DIDs) v1.0"
    author:
      - 
        ins: M. Sporny
      -
        ins: D. Longley
      -
        ins: M. Sabadello
      -
        ins: D. Reed
      -
        ins: O. Steele
      -
        ins: C. Allen
    date: 2022-07
    seriesinfo:
      W3C: Recommendation
    target: https://www.w3.org/TR/did-core/

informative:
  SemVer:
    title: Semantic Versioning 2.0.0
    author:
      -
        ins: T. Preston-Werner
    date: 2013
    target: https://semver.org/
  Agent2Agent:
    title: Agent2Agent Protocol
    author:
      -
        ins: Google LLC
    date: 2025-04
    target: https://github.com/google/A2A
  AgentCard:
    title: "Agent Card Schema from Agent2Agent Protocol"
    date: 2025-04
    author:
      - ins: Google LLC
    target: https://github.com/google/A2A/blob/main/specification/json/a2a.json
  MCP:
    title: Model Context Protocol (MCP)
    author:
      -
        ins: Anthropic PBC
    date: 2025-03
    target: https://modelcontextprotocol.io/specification/
  LangChain:
    title: LangChain Documentation
    author:
      -
        ins: LangChain Team
    date: 2024
    target: https://python.langchain.com/v0.3/docs/
  SemanticKernel:
    title: Semantic Kernel SDK
    author:
      -
        ins: Microsoft
    date: 2024
    target: https://github.com/microsoft/semantic-kernel
  AutoGen:
    title: "AutoGen: Enabling LLM Applications with Multi-Agent Conversations"
    author:
      -
        ins: Microsoft Research
    date: 2024
    target: https://microsoft.github.io/autogen/
  OpenAPI:
    title: "OpenAPI Specification v3.1.0"
    author:
      -
        ins: OpenAPI Initiative
    date: 2024-10
    target: https://spec.openapis.org/oas/latest.html
  JSON-RPC:
    title: "JSON-RPC 2.0 Specification"
    author:
      -
        ins: JSON-RPC Working Group
    date: 2013-01-04
    target: https://www.jsonrpc.org/specification
  Matrix:
    title: "Matrix Specification v1.14"
    author:
      -
        ins: The Matrix.org Foundation
    date: 2014
    target: https://spec.matrix.org/
  GraphQL:
    title: "GraphQL: A Query Language for APIs"
    author:
      -
        ins: GraphQL Foundation
    date: 2021-10
    target: https://spec.graphql.org/October2021/
  FIPA-ACL:
    title: "FIPA ACL Message Structure Specification"
    author:
      -
        ins: Foundation for Intelligent Physical Agents
    date: 2002
    target: http://www.fipa.org/specs/fipa00061/SC00061G.html
  FIPA-CNP:
    title: "FIPA Contract Net Interaction Protocol Specification"
    author:
      -
        ins: Foundation for Intelligent Physical Agents
    date: 2002
    target: http://www.fipa.org/specs/fipa00029/SC00029H.html
  AGENT-URI-REPO:
    title: "Agent URI Protocol Reference Implementation"
    date: 2025
    author:
      - ins: Y. Narvaneni
    target: https://github.com/agent-uri/agent-uri
--- abstract

This document defines the `agent://` protocol, a URI template-based framework as described in RFC 6570 for addressing, invoking, and interoperating with autonomous and semi-autonomous software agents. It introduces a layered architecture that supports minimal implementations (addressing and transport) and extensible features (capability discovery, contracts, orchestration). The protocol aims to foster interoperability among agents across ecosystems, platforms, and modalities, enabling composable and collaborative intelligent systems.

--- middle

# Introduction    {#introduction}

The rise of intelligent software agents necessitates a standardized way to identify, invoke, and coordinate them across diverse platforms. While protocols like [HTTP](#RFC9110) provide a transport mechanism for static APIs, agents differ significantly in behavior, output variability, and interaction patterns. The `agent://` proposes a URI scheme and resolution model designed to complement existing agent communication protocols and libraries like [Agent2Agent](#Agent2Agent), [FIPA-ACL](#FIPA-ACL), [Contract Net Protocol](#FIPA-CNP), [LangChain](#LangChain), [Model Context Protocol](#MCP), [AutoGen](#AutoGen), [SemanticKernel](#SemanticKernel) etc. It serves as an addressing and discovery layer that works alongside these communication protocol.

The `agent://` protocol supports diverse agent deployment models through a unified addressing scheme:

- Cloud-based agents accessible via standard web protocols
- Local agents running on the user's device through the `agent+local://` scheme
- On-premises agents within organizational boundaries
- Decentralized agents operating across distributed networks

This flexibility addresses a critical gap in current agent ecosystems, enabling applications (including browsers) to discover and invoke agents consistently regardless of where they're hosted. By providing standardized URI[RFC6570] patterns for both remote and local agents, the protocol simplifies previously complex integration scenarios like browser-to-local-agent delegation for privileged operations.

~~~
+------------------+
| Agent Applications|
+------------------+
       <-> 
+------------------+
|   agent:// URI   | <- Addressing, Resolution, Discovery
+------------------+
       <-> 
+------------------+  +------------------+
|  Agent2Agent     |  |    CNP,. etc     | <- Communication Protocols
+------------------+  +------------------+
        <->                   <-> 
+------------------+  +------------------+
| Transport Layer  |  | Transport Layer  | <- HTTP, WebSockets, etc.
+------------------+  +------------------+
~~~
{: #fig-protocol-stack title="Agent Protocol Stack Architecture"}


The `agent://` protocol supports:

- Unique and resolvable addressing of agents
- Optional self-describing capabilities
- Consistent invocation semantics over existing transports
- Progressive support for advanced patterns like delegation, collaboration, and orchestration

This document outlines the specification for the `agent://` protocol, beginning with its URI scheme and extending through capability description, transport bindings, and extensibility patterns.

A reference implementation of the `agent://` protocol is available to demonstrate resolution, transport bindings, capability discovery, and orchestration patterns. Implementers and adopters can find this example implementation at: [AGENT-URI-REPO]

# Terminology    {#terminology}

- **Agent**: An autonomous or semi-autonomous software entity that can receive instructions and perform actions.
- **Agent Descriptor (agent.json)**: A machine-readable document that describes an agent's identity, capabilities, and behavior.
- **Capability**: A self-contained function or behavior an agent offers.
- **Resolver**: A service or mechanism that maps a URI to a network endpoint or metadata.
- **Invocation**: The act of calling a capability on an agent with input parameters.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in 
RFC 2119, BCP 14 {{RFC2119}}, {{RFC8174}} when, and only when, they appear in all capitals, as shown here.

# Protocol Scope and Layering    {#protocol-scope}

The `agent://` protocol is designed as a layered framework:

| Layer                       | Purpose                                                 | Mandatory |
| --------------------------- | --------------------------------------------------------| --------- |
| URI Scheme                  | Unique addressing                                       | Yes       |
| Transport Binding           | Mechanism for invocation (e.g., HTTP, WSS, Matrix, IPC) | Yes       |
| Agent Descriptor            | Self-describing agent interface                         | Optional  |
| Resolution Framework        | Maps agent URIs to endpoints                            | Optional  |
| Application Semantics       | Shared vocab for capability naming                      | Optional  |
{: #tab-protocol-layers title="Protocol Layering Structure"}

This layering allows implementations to adopt minimal or full-featured configurations, depending on their needs.

# URI Scheme Specification    {#uri-scheme-specification}

The format of `agent://` URIs is:

~~~
agent://[authority]/[path]?[query]#[fragment] 
agent+<protocol>://[authority]/[path]
~~~
{: #fig-uri-format title="Agent URI Format"}

Examples:

- `agent://example.com/planning/gen-iti?city=Paris`
- `agent://planner.example.com/claude?text=Hello`
- `agent+https://example.com/assistants/chatgpt?query=hello`
- `agent+local://examplelocalagent`
- `agent://did:web:example.com:agent:researcher/get-article?doi=...`

## Components        {#uri-components}

- **Authority**: Uniquely identifies the agent or agent namespace (e.g., DNS or DID).
- **Path**: Specifies the agent being invoked. The `[path]` is opaque to `agent://` and can represent either a namespace or direct capability.
- **Query**: Contains serialized parameters. Query parameters SHOULD be URL-encoded as key=value pairs. If more complex structures are needed, clients SHOULD use HTTP `POST` requests with `application/json` bodies rather than base64-encoding payloads into query parameters.
- **Fragment**: Optional reference for context or sub-capability.
- The optional `+<protocol>` indicates explicit transport binding.
- If not specified, clients use resolution or fall back to HTTPS-based invocation.

## ABNF for `agent://` URI        {#uri-abnf}

~~~abnf

agent-uri      = "agent" ["+" protocol] "://" authority ["/" path]
                 [ "?" query ] [ "#" fragment ]

protocol       = 1*( ALPHA / DIGIT / "-" )
authority      = [ userinfo "@" ] host [ ":" port ]
                 ; <authority, defined in RFC3986, Section 3.2>
path           = path-abempty    
                 ; begins with "/" or is empty.
                 ; Defined in RFC3986, Section 3.3
query          = *( pchar / "/" / "?" )
                 ; <query, defined in RFC3986, Section 3.4>
fragment       = *( pchar / "/" / "?" )
                 ; <fragment, defined in RFC3986, Section 3.5>

pchar          = unreserved / pct-encoded / sub-delims / ":" / "@"
unreserved     = ALPHA / DIGIT / "-" / "." / "_" / "~"
pct-encoded    = "%" HEXDIG HEXDIG
sub-delims     = "!" / "$" / "&" / "'" / "(" / ")" /
                 "*" / "+" / "," / ";" / "="

; Character sets like pchar, unreserved, etc. are defined in RFC3986

~~~
{: #fig-abnf-grammar title="ABNF Grammar for agent:// URI Scheme"}

# Resolution Framework        {#resolution-framework}

Every agent MAY expose a self-describing document at:

~~~txt

<scheme>://<domain>/<path-to-agent>/agent.json

~~~

If a single agent is deployed at the top level then it should be under `/.well-known` to be compatible with Agent2Agent protocol.

- `/.well-known/agent.json` -- For single-agent deployments (compatible with Agent2Agent)
- `/.well-known/agents.json` -- For multi-agent domains (maps agent names -> descriptors)

This descriptor is OPTIONAL but RECOMMENDED. It enables capability discovery, transport resolution, and compatibility with ecosystem tools.

When present, the descriptor MAY use the [AgentCard](#AgentCard) (as defined by Agent2Agent protocol by Google as of April 2025) schema as one possible format, or any equivalent [JSON-LD11] based structure that expresses the agent's identity, capabilities, and behavioral metadata.

If the agent is deployed at a subdomain (e.g., `planner.example.org`), the agent descriptor SHOULD be published at `/.well-known/agent.json` on that domain.

## Ecosystem Registries        {#ecosystem-registries}

Domains MAY publish:

~~~txt

https://<domain>/.well-known/agents.json

~~~

This file should map agent names to their `agent.json` URLs for simplified enumeration. It is OPTIONAL but RECOMMENDED for better ecosystem interoperability.

Implementations MAY support resolution of agent URIs via:

- Static resolution maps
- DID resolution
- WebFinger or custom resolvers

Resolvers SHOULD support caching and capability introspection where applicable.

~~~

+---------+          +-------------+         +-------------+
|  Client | --URI--> |  Resolver   | -->URL->| Agent Server|
+---------+          +-------------+         +-------------+
                              |
                      (agent.json or agents.json)

~~~
{: #fig-resolution-flow title="Agent URI Resolution Process"}

**Example**:

~~~json

{
  "agents": {
    "planner": "https://planner.example.com/.well-known/agent.json",
    "translator": "https://example.com/translator/agent.json"
  }
}

~~~

Agents SHOULD use standard HTTP caching mechanisms (`Cache-Control`, `ETag`, `Last-Modified`) to enable efficient resolution and minimize unnecessary descriptor fetches. Clients SHOULD respect these headers and cache descriptors appropriately

## Trust Anchors        {#trust-anchors}

Domains MAY use trust anchors (e.g., DNSSEC, HTTPS certificates, or DID-based verification) to enhance identity assurance.

A practical example of URI resolution, agent descriptor fetching, and caching strategies is included in the reference implementation available at: [AGENT-URI-REPO]


# Transport Bindings        {#transport-binding}

## Explicit Transport Binding        {#explicit-transport-bindings}

Use the `agent+<protocol>://` scheme for clarity:

| Transport         | Format              | Description                        |
|-------------------|---------------------|------------------------------------|
| HTTPS             | `agent+https://`    | Secure HTTP-based invocation       |
| WebSocket Secure  | `agent+wss://`      | Real-time streaming                |
| Local             | `agent+local://`    | Runtime-registered local agents    |
| Unix Socket       | `agent+unix://`     | IPC for co-located agents          |
| Matrix            | `agent+matrix://`   | Decentralized real-time transport  |
{: #tab-transport-bindings title="Transport Binding Formats"}

The `agent+<transport>://` scheme allows explicit declaration of such bindings, enabling clarity, extensibility, and optimized routing. When no explicit transport is declared, clients MAY rely on resolution metadata (e.g., `agent.json`) or default to HTTPS-based invocation.

This flexibility ensures the protocol can adapt to different performance, privacy, or coordination requirements while remaining consistent at the addressing and invocation layer.

Local agents should be accessed using:

~~~txt

agent+local://<agent-name>

~~~

This allows agent runtimes to register their presence using a local resolver (e.g., via IPC, sockets, or service registry). The transport mechanism is implementation-specific.

The `agent+local://` scheme specifically addresses the current lack of standardized methods for browser-based applications to invoke locally installed agents. This enables web applications to delegate tasks to local agents that can perform privileged operations such as file system access, desktop automation, or hardware interaction - capabilities that are typically restricted in browser environments. Security considerations for such invocations are discussed in [](#security-and-privacy).

## Default Fallback Behavior        {#fallback-behavior}

If the protocol is omitted (i.e., `agent://` is used), clients:

1. Check `.well-known/agents.json` (if available)
2. Retrieve the agent descriptor at `agent.json` for the specified path
3. Use the `transport` or `endpoint` hints from the descriptor

If nothing is found, clients MAY fall back to:

- `HTTPS` (default transport protocol)
- HTTP `POST` if payload present, otherwise `GET`

> Note: This fallback behavior is provided for convenience and basic interoperability, but production systems SHOULD prefer explicit transport bindings or resolver-based discovery for robustness and clarity.

Clients SHOULD prefer explicit transport bindings (agent+https://) where available, and fall back to resolution-based discovery (agent://) when agent transport metadata is reliably available. Explicit binding reduces resolution ambiguity and improves latency.

## Use Cases and Recommended Bindings       {#usecases-and-recommendations}

The following table outlines some use cases and recommended bindings

| Use Case                                 | Recommended Binding           |
| ---------------------------------------- | ----------------------------- |
| Agent with known HTTPS endpoint          | `agent+https://`              |
| Local runtime agent                      | `agent+local://`              |
| Dynamic/multi-transport agents           | `agent://` with agent.json    |
| Inter-agent calls within a known context | `agent://` or agent+matrix:// |
{: #tab-use-cases title="Recommended Bindings for Common Use Cases"}


# Capability Framework        {#capability-framework}

Agents SHOULD expose a descriptor document at:

~~~txt

<agent-base-path>/agent.json

~~~

This descriptor MAY follow:

- The AgentCard structure (as defined by Google's Agent2Agent protocol as of April 2025), or another equivalent format
- Any format other than AgentCard SHOULD be expressed in [JSON-LD11] to enable semantic discovery

Agent descriptors SHOULD include:

- Agent name and version
    - MAY include `supportedVersions` indicating the list of older versions and their end-points.
    - Versioning should follow [SemVer] or later
    - Clients SHOULD verify compatibility based on documented major, minor, and patch versions
- Human-readable description
- Input/output schemas (e.g., JSON Schema)
- Capability list with IDs, descriptions, tags, version
- Optional behavioral metadata (e.g., `isDeterministic`, `expectedOutputVariability`, `requiresContext: boolean`, `memoryEnabled: boolean`, `responseLatency: "low" | "medium" | "high"`, `confidenceEstimation: boolean`)
    - `isDeterministic` (boolean): Indicates whether repeated calls with identical inputs yield identical outputs.
    - `expectedOutputVariability`: indicates typical variability in outputs, similar to temperature setting
    - `responseLatency`: Expected response time.
    - `requiresContext` (boolean): Indicates whether the input needs context or the agent can work on its own
    - `memoryEnabled` (boolean): Indicates whether the agent will remember the interactions
- Optional transport or invocation hints
- Optional authentication or permission requirements
- Optional state management practices
- Optional `interactionModel` to indicate a way to interact (e.g. `agent2agent`, `fipa-acl`, `kqml`, `contract-net`, `emergent` etc). If mentioned, the message payload SHOULD follow the model's defined parameters if any.

Agents MAY expose `inputFormats` and `outputFormats` per capability using standard MIME types (e.g., `application/json`, `application/ld+json`, `application/fipa-acl`).

Agent descriptors SHOULD include input/output schemas (e.g., JSON Schema) and MAY document content negotiation support via the `contentTypes` field per capability. This allows clients to understand and negotiate payload encoding, enabling interoperability across ecosystems that use JSON, [JSON-LD11], RDF/XML, [FIPA-ACL], or other formats.

Clients MAY use standard negotiation mechanisms such as `Content-Type` and Accept headers (in HTTP), or envelope metadata (in protocols like [JSON-RPC](#JSON-RPC), [Matrix](#Matrix), etc.).

Implementations MAY advertise protocol compatility via metadata fields such as `interactionModel`, `orchestration`, or supported `envelopeSchemas` etc. These metadata fields enable clients and agent runtimes to interoperate across heterogeneous ecosystems and communication models.

This extensibility ensures `agent://` can serve as a unifying addressing and invocation layer, bridging agents that follow established standards, platform-specific conventions, or learned behaviors in dynamic environments.

If an `agent.json` is provided, it SHOULD contain at least: `name`, `version`, and one or more capabilities.

Clients SHOULD explicitly specify the agent version either as a URI path segment, query parameter (`?version=3.1.4`), or HTTP header (`X-Agent-Version`). If omitted, servers SHOULD assume the latest version. Agents MUST document their preferred method for version negotiation clearly in their descriptor.

While `.well-known/agents.json` MAY be used to enumerate all available agents under a domain, the individual `agent.json` files serve as the canonical source of truth.

Expressing descriptors in [JSON-LD11] enables semantic interoperability and supports alignment with common web-based data models.

Implementers MAY choose to embed, proxy, or map to other protocols within the `agent.json` descriptor or transport bindings, allowing for seamless orchestration and hybrid deployments.

# Interaction Patterns        {# interaction-patterns}

Supported interaction types include:

- Request/Response (synchronous)
- Deferred response (polling or webhook) SHOULD include a `taskId` and polling interval hint.
- Streaming responses (e.g., Server-Sent Events, WebSocket). Streaming responses over `agent+wss://` SHOULD use newline-delimited JSON (NDJSON)
- Delegated invocation (calling other agents on behalf of user)
- Asynchronous event notifications via HTTP webhooks or WebSockets. Event notifications if available SHOULD include event types, payloads, and identifiers.

All interaction patterns (e.g., streaming, event-driven, polling) are transport-agnostic but MAY impose format constraints (e.g., NDJSON over WebSockets).

Agents SHOULD include status and confidence metadata in responses where applicable.

## Stateful Interactions        {# stateful-interactions}

The `agent://` protocol leverages HTTP's established mechanisms for state management. Clients and agents SHOULD use standard HTTP headers or query parameters to pass identifiers such as `sessionId` or `taskId`. Agents MAY maintain state across interactions using these identifiers. Clients and agents SHOULD agree on session semantics via capability descriptors or invocation headers.

Non-HTTP transports SHOULD include session or task identifiers within message envelopes (e.g., JSON-RPC headers, WebSocket message metadata, Matrix events). These fields SHOULD follow naming conventions similar to `sessionId`, `taskId`, etc.

When the transport lacks a native header mechanism, agents SHOULD extract session information from the body or envelope metadata.

When content negotiation fails or the requested format is not supported, agents SHOULD respond with a `406 Not Acceptable` HTTP error or equivalent, and MAY include supported formats in the response metadata.

### Recommended practices:        {#recommended-practices}

- Use HTTP headers (e.g., `X-Session-ID`, `X-Task-ID`) or query parameters for session and task identifiers.
- Clearly document state identifiers and their expected lifecycle in the agent's descriptor (agent.json).

**Example**:

~~~http

GET /tasks/1234 HTTP/1.1
Host: planner.example.com
X-Session-ID: abcde-12345

~~~

## Orchestration Patterns        {#orchestration-patterns}

Agents MAY invoke other agents as part of delegated or composite tasks. Agents SHOULD explicitly provide orchestration workflows, delegation chains, or composite interactions either in their `agent.json` or in their response metadata.

## Typical Interaction Flows        {#typical-interaction-flows}

### Client-to-Agent Interaction        {#client-agent-interaction}

A typical user-driven invocation of an agent using the `agent://` protocol follows these steps:

~~~art

+--------+       +-----------+       +-------------+
|  User  |  -->  |  Client   |  -->  |  Agent Host |
+--------+       +-----------+       +-------------+
     |                |                    |
     | Initiates      |                    |
     | intent (e.g.,  |                    |
     | "Plan my trip")|                    |
     |                |                    |
     |                | Resolves agent URI |
     |                | --> agents.json / agent.json
     |                | Retrieves capabilities
     |                |                    |
     |                | Constructs request |
     |                | --> agent://plan.example.com/gen-iti?city=Rio
     |                |                    |
     |                |                    | Validate input 
     |                |                    | Process logic/call tools
     |                |                    | May call sub-agents
     |                |                    |
     |                | Receives response  |
     |                | <== itinerary JSON |
     | Presents result to user             |

~~~
{: #fig-client-interaction title="Client-to-Agent Interaction Flow"}

**Notes**:

- The client MAY handle fallback logic if the agent cannot be resolved initially.
- Authentication MAY be required before invocation.
- The invocation can be a simple GET or POST depending on input size and structure.

### Agent-to-Agent Interaction        {#agent-to-agent-interaction}

Agents MAY interact with each other using `agent://` URIs to delegate tasks or compose workflows.

**Example: A planning agent invoking a translation agent**:

~~~art
+----------+       +----------+       +------------+
|Planning  |------>|Resolver/ |------>|Translation |
|Agent     |       |URI       |       |Agent       |
+----------+       +----------+       +------------+
     |                  |                   |
     | Input:           |                   |
     | {"city":"Paris"} |                   |
     |                  |                   |
     | Needs translation|                   |
     |                  |                   |
     |                  | Resolves URI:     |
     |--agent://translator.example/translate?text=Bonjour-->|
     |                  |                   |
     |                  | --> Get           |
     |                  |     agent.json    |
     |                  | --> Determine     |
     |                  |     transport     |
     |                  |                   |
     |                  |                   | Process translation
     |                  |                   | Return translated JSON
     |<-----------------|<------------------|
     | Merge & return   |                   |
     | to user/client   |                   |
     | or continues     |                   |
~~~
{: #fig-agent-interaction title="Agent-to-Agent Interaction Flow"}

**Chaining Behavior**:

- The invoking agent MAY include `X-Task-ID`, `X-Delegation-Chain`, or equivalent headers.
- The response MAY include intermediate metadata such as `confidence`, `sourceAgent`, `taskTrace`, or `timeTaken`.

# Error Handling        {# error-handling}

The `agent://` protocol MAY leverage HTTP standard status codes for signaling errors. Implementations MAY return errors using standard HTTP status codes along with structured JSON error responses conforming to [RFC9457](#RFC9457) ("Problem Details for HTTP APIs").

**Recommended HTTP status codes include (but are not limited to)

| Status Code | Meaning                                |
| ----------- | -------------------------------------- |
| 400         | Bad Request (e.g., invalid parameters) |
| 401         | Unauthorized                           |
| 403         | Forbidden                              |
| 404         | Capability or resource not found       |
| 409         | Conflict (e.g., state mismatch)        |
| 429         | Too Many Requests (rate limiting)      |
| 500         | Internal Server Error                  |
| 503         | Service Unavailable                    |
{: #tab-http-status-codes title="Recommended HTTP status codes"}

Example:

~~~http

HTTP/1.1 404 Not Found
Content-Type: application/problem+json

{
  "type": "https://example.com/errors/capability-not-found",
  "title": "Capability Not Found",
  "status": 404,
  "detail": "The requested capability 'gen-iti' was not found.",
  "instance": "/planner/gen-iti"
}
{: #fig-error-response title="Example HTTP Error Response"}

~~~

This format is not prescriptive but aims to encourage consistency. Implementations MAY adapt the error schema based on their transport layer (e.g., JSON-RPC, HTTP status + body, WebSocket messages).

For non-HTTP transports (e.g., WebSockets, Matrix), agents SHOULD still return structured errors using similar JSON structures (`type`, `title`, `detail`, `status`), encapsulated within the transport's native message envelope (e.g., JSON-RPC `error` objects, Matrix event content fields). Implementers SHOULD document chosen structures clearly in their capability descriptors.

Where applicable, implementations SHOULD align with existing conventions such as:

- JSON-RPC `error` objects (`code`, `message`, `data`)
- [OpenAPI](#OpenAPI) or REST error payloads
- [GraphQL](#GraphQL) `errors` array format

Recommended error categories:

- `CapabilityNotFound`
- `InvalidInput`
- `AmbiguousResponse`
- `Timeout`
- `PermissionDenied`

Clients SHOULD parse and utilize these structured responses to handle errors gracefully.

# Security and Privacy Considerations        {#security-and-privacy}

The `agent://` protocol explicitly relies on widely-adopted HTTP authentication and authorization standards. Agents SHOULD support standard authentication and authorization schemes such as OAuth2 (Bearer tokens), API keys, or signed payloads. When using HTTPS, mutual TLS MAY be employed. JSON Web Tokens (JWT) are RECOMMENDED for conveying signed claims between agents.

Security extensions MAY include:

- [OAuth2](#RFC6750) Bearer Tokens
- JSON Web Tokens ([JWT](#RFC7519))
- Mutual TLS ([mTLS](#RFC8705)) authentication
- API Keys via HTTP headers (e.g., `X-API-Key`)
- Capability-based access control
- Delegation chains

For non-HTTP transports (e.g., WebSocket, Matrix), agents SHOULD leverage native authentication mechanisms, such as WebSocket protocol-level authentication tokens or Matrix homeserver authentication flows. Agents MUST clearly document supported security mechanisms per transport binding.

When using [Decentralized Identifiers](#DID-CORE) as authority, agent descriptors MAY be cryptographically signed. Clients SHOULD verify such signatures against the corresponding DID Document.

For agent-to-agent delegation, agents SHOULD include delegation metadata (e.g., `X-Delegation-Chain`) that identifies prior actors. These chains SHOULD be signed or verifiable via claims (e.g., using JWT, Verifiable Credentials, or DID-linked proofs).

Privacy recommendations:

Agents SHOULD adhere to privacy best practices, including:

- Data minimization (collect only necessary data)
- Explicit consent and revocation mechanisms 
- Clear logging/audit trails
- Ethical AI guidelines, including bias detection and fairness assessments as they evolve

## Compliance and Regulatory Considerations        {#compliance-and-regulatory-considerations}

Implementers SHOULD ensure compliance with relevant legal frameworks (e.g., GDPR, CCPA) of the jurisdictions where the agent is hosted. Agents processing sensitive data SHOULD provide audit trails and explicit consent mechanisms clearly documented in capability descriptors.

# Extensibility        {#extensibility}

The protocol supports extension via:

- Namespaced capability vocabularies
- Alternate transport bindings
- Extended agent descriptors
- Optional orchestration layers (task graphs, workflows)

Extension proposals SHOULD be documented clearly, and ideally reviewed through established processes such as community forums, dedicated working groups, or public registries to ensure transparency and interoperability.

# IANA Considerations        {#iana-considerations}

This document requests the registration of the `agent` URI scheme in the IANA "Uniform Resource Identifier (URI) Schemes" registry.

## URI Scheme Registration Template        {#uri-schem-registration-template}

- **Scheme Name**: `agent`

- **Status**: Provisional

- **Applications/Protocols That Use This Scheme**:  
  The `agent` URI scheme identifies and invokes autonomous or semi-autonomous software agents across systems. It provides transport-agnostic addressing layer supporting discovery, invocation and orchestration. The scheme is compatible with existing schemes such as `https`, `did` and `web+` schemes where appropriate.

- **Contact**:  
  Yaswanth Narvaneni  
  <yaswanth@gmail.com>

- **Change Controller**:  
  The author or a relevant standards body such as the IETF if adopted.

- **References**:  
  This document (Internet-Draft): *agent:// Protocol -- A URI-Based Framework for Interoperable Agents*  
  [RFC3986] - Uniform Resource Identifier (URI): Generic Syntax  
  [RFC7595] - Guidelines and Registration Procedures for URI Schemes

- **URI Syntax**:  
  The general form of an `agent` URI is:

~~~txt

agent:[+<protocol>]://<authority>/<path>[?<query>][#<fragment>]

~~~

Where:
- `authority` is typically a domain name or Decentralized Identifier (DID)  
- `path` is an opaque agent-specific capability or namespace  
- `query` includes serialized key-value parameters  
- `fragment` MAY reference a sub-capability or context  
- The optional `+<protocol>` segment indicates an explicit transport binding (e.g., `agent+https://`)

Detailed ABNF is specified in [](#uri-abnf) of this document.

- **Security Considerations**:  
The `agent` scheme does not introduce new transport-layer vulnerabilities but inherits risks from underlying protocols such as HTTP, WebSocket, or local execution environments. Implementers should apply standard authentication and authorization measures, such as OAuth2, JWTs, or mutual TLS. See Section 10 for security and privacy guidance.


# Appendix A. Example Agent Descriptor        {#example-agent-descriptor}

Following is an example of `agent.json`.

~~~json-ld

{
  "@context": "https://example.org/agent-context.jsonld",
  "name": "planner.example.com",
  "description": "Agent helps in researching & planning itineraries",
  "url": "agent://planner.example.com/",
  "provider": {
    "organization": "Example AI Org"
  },
  "documentationUrl": "https://planner.example.com/docs",
  "interactionModel": "agent2agent",
  "orchestration": "delegation",
  "envelopeSchemas": ["fipa-acl"],
  "version": 3.1.4,
  "supportedVersions": {
    "3.0.0": "/v3/",
    "2.1.2": "/olderversion/v2.1.2/",
    "1.0": "/version-1/"
  },
  "capabilities": [
    {
      "name": "gen-iti",
      "version": "2.1.5",
      "description": "Creates a travel itinerary for a given city.",
      "input": { "city": "string" },
      "output": { "itinerary": "array" },
      "isDeterministic": false,
      "expectedOutputVariability": "medium",
      "contentTypes": {
        "inputFormat": ["application/json", "application/ld+json"],
        "outputFormat": ["application/json"]
      }
    }
  ],
  "authentication": {
    "schemes": ["OAuth2"]
  },
  "skills": [
    {
        "id": "agent-skill-1",
        "name": "research-location"
    }
  ]
}

~~~
{: #fig-agent-descriptor title="Example Agent Descriptor in JSON-LD"}

A JSON-LD context is added to support semantic querying and graph-based processing.

# Appendix B. Use Cases        {#use-cases}

- Composing workflows with agents from different vendors
- Enabling discovery and invocation in agent marketplaces
- Facilitating human-in-the-loop workflows with agent transparency
- Building knowledge-based agents that invoke retrieval agents
- Real-time collaboration among specialized agents
- Browser-to-local-agent delegation for privileged operations and desktop automation
- Consistent addressing for agents across network boundaries and security contexts

# Appendix C. Reference Implementation        {#reference-implementation}

A reference implementation of the `agent://` protocol is available to guide implementers, demonstrating the following functionalities:

- URI parsing and resolution (`agent.json`, `.well-known` endpoints)
- Transport bindings including HTTPS, WebSocket, Matrix, and Local IPC
- Capability descriptor discovery, caching, and semantic processing
- Orchestration and delegation chaining examples
- Error handling, payload negotiation, and versioning patterns
- Security examples covering OAuth2, JWT, and mutual TLS (mTLS)

The implementation is open-source and maintained at:

[AGENT-URI-REPO]

Implementers are encouraged to use this as a starting point or reference during their implementation efforts.

# Acknowledgements        {#acknowledgements}
{:unnumbered}

This draft reflects observations and aspirations drawn from emerging agent ecosystems. It builds on publicly available research, community discussions, and early experimentation with agent-oriented protocols. It is intended as a foundation for future refinement and collaboration.