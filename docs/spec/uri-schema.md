# Agent URI: URI Schema Definition

This document provides a formal definition of the `agent://` URI scheme syntax and semantics.

## URI Format

The format of `agent://` URIs is:

```
agent://[authority]/[path]?[query]#[fragment]
agent+<protocol>://[authority]/[path]?[query]#[fragment]
```

## ABNF for `agent://` URI

```
agent-uri      = "agent" [ "+" protocol ] "://" authority [ "/" path ] [ "?" query ] [ "#" fragment ]

protocol       = 1*( ALPHA / DIGIT / "-" )
authority      = [ userinfo "@" ] host [ ":" port ] ; <authority, defined in RFC3986, Section 3.2>
path           = path-abempty    ; begins with "/" or is empty. Defined in RFC3986, Section 3.3
query          = *( pchar / "/" / "?" ) ; <query, defined in RFC3986, Section 3.4>
fragment       = *( pchar / "/" / "?" ) ; <fragment, defined in RFC3986, Section 3.5>

pchar          = unreserved / pct-encoded / sub-delims / ":" / "@"
unreserved     = ALPHA / DIGIT / "-" / "." / "_" / "~"
pct-encoded    = "%" HEXDIG HEXDIG
sub-delims     = "!" / "$" / "&" / "'" / "(" / ")" / "*" / "+" / "," / ";" / "="
```

## Component Definitions

| Component | Description | Required | Example |
|-----------|-------------|----------|---------|
| `agent` | Scheme name | Yes | `agent://` |
| `+<protocol>` | Explicit transport binding | No | `agent+https://` |
| `authority` | Authority component (domain or DID) | Yes | `planner.acme.ai` |
| `path` | Path component (capability or namespace) | No | `/generate-itinerary` |
| `query` | Query parameters | No | `?city=Paris&days=3` |
| `fragment` | Fragment identifier | No | `#overview` |

## Component Semantics

### Protocol

The optional `+<protocol>` segment explicitly indicates the transport binding to use:

- `agent+https://` - HTTPS transport
- `agent+wss://` - WebSocket Secure transport
- `agent+local://` - Local IPC transport
- `agent+unix://` - Unix socket transport
- `agent+matrix://` - Matrix protocol transport

If omitted, the client should use the resolution framework or fall back to HTTPS.

### Authority

The authority component identifies the agent or agent namespace:

- **Domain-based**: A standard DNS domain (e.g., `planner.acme.ai`)
- **DID-based**: A decentralized identifier (e.g., `did:web:example.com:agent:planner`)
- **Local**: For local agents, an identifier in the local namespace (e.g., `local:planner`)

### Path

The path component identifies the agent's capability or resource:

- For domain-based agents without a path, the URI refers to the agent itself
- Specific capabilities are indicated using path segments (e.g., `/generate-itinerary`)
- Hierarchical capabilities can use nested paths (e.g., `/planning/itinerary/generate`)

### Query Parameters

Query parameters represent input parameters for the agent capability:

- Key-value pairs following standard URI query syntax
- Values should be URL-encoded
- Complex data structures should preferably use POST requests with JSON bodies instead of encoding in the URI

### Fragment

The optional fragment component can be used to:

- Identify a specific sub-capability or mode
- Reference a specific section or context
- Provide additional client-side context that is not sent to the server

## Examples

```
agent://planner.acme.ai/generate-itinerary?city=Paris&days=3
```
- Authority: `planner.acme.ai`
- Capability: `generate-itinerary`
- Parameters: `city=Paris`, `days=3`

```
agent+https://api.example.com/agents/translator?text=Hello&target=fr
```
- Explicit HTTPS transport
- Authority: `api.example.com`
- Path: `/agents/translator`
- Parameters: `text=Hello`, `target=fr`

```
agent+wss://streaming.example.com/generate#continuous
```
- WebSocket transport
- Authority: `streaming.example.com`
- Capability: `generate`
- Fragment: `continuous` (indicates streaming mode)

```
agent://did:web:example.com:agent:researcher/get-article?doi=10.1234/5678
```
- DID-based authority
- Capability: `get-article`
- Parameter: `doi=10.1234/5678`

```
agent+local://assistant
```
- Local transport
- Local agent named `assistant`

## Resolution Process

1. Parse the URI according to the syntax rules above
2. If explicit transport (`+<protocol>`) is specified, use that transport
3. Otherwise:
   a. Check for `.well-known/agents.json` at the authority domain
   b. Fetch and parse `agent.json` for the specified agent
   c. Use transport hints from the descriptor
4. If no transport information is available, fallback to HTTPS

## Security Considerations

- Agent URIs should be validated before resolution or invocation
- Authority validation is essential for security (domain validation, DID verification)
- Transport security should be enforced (HTTPS, WSS, or authenticated local)
- Query parameters may contain sensitive information and should be handled accordingly
- Clients should implement appropriate security measures (e.g., CSRF protection, input validation)

## See Also

- [Agent Descriptor Schema](agent-descriptor-schema.json) - JSON Schema for agent descriptors
- [RFC3986](https://tools.ietf.org/html/rfc3986) - Uniform Resource Identifier (URI): Generic Syntax
