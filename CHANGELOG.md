# Changelog

All notable changes to the `agent-uri` library are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] — 2026-04-18

First release aligned with IETF `draft-narvaneni-agent-uri-03`
(<https://datatracker.ietf.org/doc/draft-narvaneni-agent-uri/03/>). This is a
breaking release: the library has been reshaped top-to-bottom to match the
published spec. There are no deprecation aliases from 0.3.x.

### Breaking changes

- **`capabilities[]` renamed to `skills[]`** throughout descriptors, the
  descriptor schema, the generator, the A2A compatibility converter, and the
  public Python API. `Capability` dataclass is now `Skill`; the `@capability`
  decorator is now `@skill`; `CapabilityMetadata` is now `SkillMetadata`. This
  resolves the type collision with AgentCard's `capabilities` boolean-flag
  object and enables direct 1:1 mapping with AgentCard `skills`.
- **Required skill fields** are now `id`, `name`, `description` (matches
  AgentCard). Skill `id` is required by the spec.
- **Authentication descriptor fields replaced** with OAuth metadata
  discovery: `authorization_server` (RFC 8414) and
  `protected_resource_metadata` (RFC 9728) instead of embedded
  `tokenEndpoint`/`scopes`/`flows`. `jwks_uri` and `jwks` fields added for
  non-OAuth key discovery. The old `details` dict is removed.
- **Delegation** is now via OAuth 2.0 Token Exchange (RFC 8693) nested `act`
  claim; the custom `Delegation-Chain` header and JWT-array format are gone.
- **Descriptor signing** is now via RFC 9421 HTTP Message Signatures with
  RFC 9530 Content-Digest. RFC 7515 JWS with RFC 8785 JCS canonicalization
  remains available as a fallback for out-of-band distribution.
- **Correlation headers** are no longer defined by this library. Use W3C
  Trace Context (`traceparent`, `tracestate`) for tracing and W3C Baggage
  (`session.id`, `enduser.id` per OpenTelemetry) for session/user
  correlation. `Session-ID`, `Task-ID`, `Delegation-Chain`, and
  `Agent-Version` are no longer emitted or consumed.
- **Version negotiation** is now via `Accept: application/agent+json;
  profile="..."` per RFC 6906. The `Agent-Version` header is removed.
- **Rate-limit signaling** follows the IETF `httpapi-ratelimit-headers`
  draft (structured-field `RateLimit` and `RateLimit-Policy` response
  headers). The descriptor-level `rateLimit` field is removed.
- **Descriptor fields removed**: `is_deterministic`,
  `expected_output_variability`, `response_latency`, `requires_context`,
  `memory_enabled`, `orchestration`, `envelope_schemas`, `rate_limit`,
  `confidence_estimation`, and the A2A-compat fields `default_input_modes`,
  `default_output_modes`, `agent_capabilities` — all delegated to the
  communication-protocol layer or to extension namespaces.
- **Resolver algorithm** is now the spec's simple 2-step over
  `/.well-known/agents.json` only. The old cascade (`/agent.json` root,
  `.well-known/agent.json` singular, path-based fallback) is gone.
- **SSRF protection** is applied at three stages: the incoming URI
  authority, the descriptor URL extracted from `agents.json`, and any HTTP
  redirect target. IPv4-mapped IPv6 addresses are unwrapped and
  re-checked. The blocklist covers private, loopback, link-local
  (including `169.254.0.0/16` cloud metadata), and IPv6 unique-local /
  link-local ranges.
- **Python 3.9 dropped.** Minimum Python is now 3.10 (3.9 reached EOL in
  October 2025).

### Added

- Transport bindings for `agent+grpc://`, `agent+mqtt://`, `agent+unix://`
  registered with the transport registry. gRPC and MQTT ship as stubs that
  raise `TransportNotSupportedError` on use; real implementations will
  follow in minor releases.
- `Dependency` dataclass for the `depends` field on a skill (with `uri`,
  `relation`, `version_constraint`).
- `Transport` dataclass replacing the old `Endpoints`; requires at least one
  of `endpoint`, `https`, `wss`, `grpc`, `mqtt`, `local`, `unix`.
- Agent-level `conformance_level` (0–3), `environment`, and `status` fields.
- Skill-level `status`, `idempotent`, `streaming_format`, `content_types` with
  `accepts`/`produces`, per-skill `authentication` override.
- DID authority support: canonical percent-encoded form, convenience
  unencoded form, and a resolution path for `did:web` authorities.
- OAuth Authorization Server Metadata fetcher (RFC 8414) and Protected
  Resource Metadata fetcher (RFC 9728) in `agent_uri.auth`.
- RFC 8693 Token Exchange helper with `act`-claim nesting and monotonic
  scope-narrowing check.
- RFC 9421 HTTP Message Signature verifier + RFC 9530 Content-Digest
  handling.
- Exception hierarchy additions: `SSRFViolationError`, `DIDResolutionError`,
  `RedirectViolationError`, `SignatureVerificationError`,
  `KeyDiscoveryError`, `DelegationError`, `ScopeNarrowingViolationError`,
  `ContentNegotiationError` (HTTP 406), `AgentGoneError` (HTTP 410).
- JSON Schema files at `docs/rfc/schemas/` are now authoritative for
  descriptor and registry validation.

### Security

- dependabot: 24 alerts (8 high / 10 moderate / 6 low) addressed —
  see commit `ed14c52` and successors for the per-package details.
- Minimum Python 3.10 (3.9 EOL).

### Migration guide (0.3.x → 0.5.0)

| 0.3.x | 0.5.0 |
|---|---|
| `from agent_uri.capability import Capability, capability` | `from agent_uri.skill import Skill, skill` |
| `descriptor.capabilities` (list) | `descriptor.skills` |
| `descriptor.endpoints` (`Endpoints` dataclass) | `descriptor.transport` (`Transport` dataclass) |
| `Capability(name=..., description=...)` | `Skill(id=..., name=..., description=...)` — note `id` is required |
| `Authentication(schemes=[...], details={"oauth2": {...}})` | `Authentication(schemes=[...], authorization_server="...", protected_resource_metadata="...")` |
| `Delegation-Chain: [...]` HTTP header | `Authorization: Bearer <token>` with RFC 8693 nested `act` claim |
| `Agent-Version: 3.1.4` HTTP header | `Accept: application/agent+json; profile="..."` |
| `X-Session-ID: ...` | `baggage: session.id=...` per W3C Baggage |
| `interaction_model = "agent2agent"` (string) | `interaction_model = ["agent2agent"]` (list — can signal multiple) |

### Reference

- Spec: <https://datatracker.ietf.org/doc/draft-narvaneni-agent-uri/03/>
- Engagement threads (once posted): IETF `dispatch`, `agent2agent` lists

## [0.3.0] — 2025-10-15

Published against draft-narvaneni-agent-uri-02. See Git history for details.

## [0.2.0] — 2025-06-10

## [0.1.0] — 2025-04-21

Initial release.
