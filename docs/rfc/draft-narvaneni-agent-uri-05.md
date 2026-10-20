---
title: "The agent URI Scheme and Verifiable Agent Identity"
abbrev: "agent-uri"
category: std
docName: draft-narvaneni-agent-uri-05
ipr: trust200902
area: Applications and Real-Time
keyword:
  - agent
  - identity
  - URI scheme
  - HTTP message signatures
submissionType: IETF
date: 2026-10-20

v: 3
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
 -
    ins: S. P. Ravi
    name: Sai Purnima Ravi
    organization: Independent Researcher
    email: r.sai.purnima+ietf@gmail.com

normative:
  RFC3339:
  RFC3986:
  RFC5234:
  RFC5890:
  RFC5891:
  RFC6838:
  RFC6890:
  RFC7515:
  RFC7517:
  RFC7519:
  RFC7595:
  RFC7638:
  RFC8037:
  RFC8259:
  RFC8288:
  RFC8615:
  RFC8693:
  RFC8725:
  RFC8785:
  RFC9110:
  RFC9111:
  RFC9421:
  RFC9530:
  RFC9651:
  WEB-BOT-AUTH: I-D.ietf-webbotauth-httpsig-protocol
  DID-CORE:
    title: "Decentralized Identifiers (DIDs) v1.0"
    author:
      - ins: M. Sporny
      - ins: D. Longley
      - ins: M. Sabadello
      - ins: D. Reed
      - ins: O. Steele
      - ins: C. Allen
    date: 2022-07
    seriesinfo:
      W3C: Recommendation
    target: https://www.w3.org/TR/did-core/
  CID:
    title: "Controlled Identifiers v1.0"
    author:
      - ins: M. Sporny
      - ins: M. Jones
    date: 2025-05
    seriesinfo:
      W3C: Recommendation
    target: https://www.w3.org/TR/cid-1.0/

informative:
  RFC6839:
  RFC6973:
  RFC8417:
  RFC9126:
  RFC9264:
  RFC9449:
  RFC9727:
  DID-WEBVH:
    title: "The did:webvh DID Method"
    author:
      - ins: Decentralized Identity Foundation
    date: 2025
    target: https://identity.foundation/didwebvh/
  A2A:
    title: "Agent2Agent (A2A) Protocol Specification"
    author:
      - ins: A2A Project, Linux Foundation
    date: 2025
    target: https://a2a-protocol.org/latest/specification/
  MCP:
    title: "Model Context Protocol Specification"
    author:
      - ins: Model Context Protocol Project
    date: 2025
    target: https://modelcontextprotocol.io/specification/

--- abstract

Software agents increasingly act on the Internet on behalf of people and
organizations: they call APIs, browse websites, and delegate work to other
agents. Protocols such as A2A and MCP define how agents communicate, but there
is no interoperable way to answer a prior question: *which agent is this, and
how can its claims be verified?*

This document defines the `agent` URI scheme as a stable, human-readable
identifier for an agent, a deterministic mapping from that identifier to an
HTTPS-hosted Agent Identity Document, anchoring of the agent's keys to a web
origin or a Decentralized Identifier, signed statements that bind the agent to
its protocol metadata, and a profile of HTTP Message Signatures for automated
traffic that lets an agent prove its identity on HTTP requests. It
deliberately does not define how agents communicate, describe their
capabilities, or are invoked.

--- middle

# Introduction {#introduction}

Agents are now first-class actors on the Internet. A single user task can cause
an agent to call dozens of APIs and other agents, each of which needs to decide
whether to serve the request. Today those services can see a TLS client, an IP
address, perhaps an OAuth access token issued to *some* client, and a
`User-Agent` string that anyone can forge. They cannot reliably tell which agent
is calling, or whether the protocol metadata it advertises was really published
by whoever controls it.

Communication protocols already exist. {{A2A}} defines agent-to-agent
interaction and an Agent Card; {{MCP}} defines how agents reach tools and
publishes server metadata; OpenAPI describes HTTP APIs. Each of these describes
*how to talk to* an endpoint. None of them defines a portable answer to *who* an
agent is that works across all of them.

This document defines that missing identity layer:

1. **A name.** The `agent` URI (e.g., `agent://example.com/planner`) is a
   stable, human-readable identifier for an agent ({{agent-uri}}).
2. **A document.** Every agent URI maps to an HTTPS URL that serves an Agent
   Identity Document listing the agent's claimed operator, public keys, and
   links to its protocol metadata ({{aid}}).
3. **An anchor.** The agent's keys are trusted because of where the document is
   served, or because of a Decentralized Identifier bound to the agent URI
   ({{anchoring}}).
4. **Statements.** The agent signs statements binding itself to specific
   protocol metadata, so that metadata can be hosted anywhere
   ({{statements}}).
5. **Proof on requests.** The agent signs the HTTP requests it makes
   ({{request-signing}}).

## Design Principles {#principles}

- **Identify, do not invoke.** An agent URI names an agent. It is not a
  locator for an endpoint and carries no invocation parameters.
- **One way to do each thing.** There is one mapping from name to document,
  one key identifier, and one way for an agent to prove its identity on a
  request.
- **Reuse before invent.** Every mechanism is a profile of an existing or
  in-progress standard: HTTPS and well-known URIs {{RFC8615}}, JWK {{RFC7517}},
  JWS {{RFC7515}}, HTTP Message Signatures {{RFC9421}} as profiled by
  {{WEB-BOT-AUTH}}, and DIDs {{DID-CORE}}.
- **Anchor trust outside the document being verified.** A key is trusted
  because of the origin or DID it is published under, never because a document
  names it about itself.
- **Authenticate keys, not claims.** Verification establishes control of keys
  anchored to an agent URI. Everything else an agent says about itself,
  including who operates it, remains a claim.

## Non-Goals {#non-goals}

The following are out of scope:

- Communication semantics, message formats, task lifecycles, and invocation.
  These belong to A2A, MCP, OpenAPI-described APIs, and similar protocols.
- Capability, skill, or tool description. Protocol metadata documents (for
  example, an A2A Agent Card or an MCP server card) remain authoritative for
  these.
- Credentials for short-lived agent instances, and bindings of agent keys to
  OAuth client authentication. These are expected to be specified in
  companion documents.
- Verification of organizations. This document does not verify that the
  operator an agent claims is real or actually operates it.
- Search, ranking, registries, reputation, pricing, and payments.
- Authorization policy. Knowing who an agent is does not grant it anything.

# Conventions and Terminology {#terminology}

{::boilerplate bcp14-tagged}

This document uses the terms "JSON object", "member", and "string" from
{{RFC8259}}, and "Dictionary", "Item", and "String" from {{RFC9651}}.

Agent:
: A software system that acts autonomously or semi-autonomously, typically on
  behalf of a person or organization.

Operator:
: The person or organization that an agent claims is accountable for it.

Agent URI:
: An `agent` URI as defined in {{agent-uri}}. The human-readable name of an
  agent.

Agent Identity Document (AID):
: A JSON document, retrieved by dereferencing an agent URI, that lists the
  agent's claimed operator, keys, and links ({{aid}}).

AID URL:
: The HTTPS URL that an agent URI maps to ({{dereference}}).

AID Origin:
: The tuple ("https", host, 443) for the host of the agent URI.

Agent Key:
: A public key anchored to an agent ({{anchoring}}).

Key Identifier:
: The JWK SHA-256 Thumbprint of an Agent Key ({{key-ids}}).

Verifier:
: Any party that checks an agent's identity: a website or API receiving
  requests, an authorization server, a registry, or another agent.

# Overview {#overview}

~~~
                    agent://example.com/planner           (name)
                               |
                               | deterministic mapping
                               v
     https://example.com/.well-known/agent/planner        (AID URL)
                               |
          +--------------------+---------------------+
          |                    |                     |
     operator (claim)     keys (JWK Set)        links (rel, href)
                               |                     |
     origin-anchored: trusted via HTTPS        A2A Agent Card,
     DID-anchored: keys from DID document      MCP server card,
                                               OpenAPI description
~~~
{: #fig-overview title="From agent URI to verifiable identity"}

A typical verification, for a request received by an API:

1. The request carries an HTTP message signature and a `Signature-Agent`
   member whose value is the AID URL of `agent://example.com/planner`.
2. The verifier derives the agent URI from the AID URL and retrieves the AID
   (or uses a cached copy).
3. The verifier finds the anchored key identified by the signature and
   verifies the signature and the request content.
4. The verifier now knows that the request was made by a holder of a key
   anchored to `agent://example.com/planner`. It also has the operator the
   agent *claims*, which it must not treat as verified ({{sec-operator}}).
   Whether to serve the request remains a policy decision.

# The agent URI Scheme {#agent-uri}

## Syntax {#uri-syntax}

The following ABNF {{RFC5234}} uses `fragment` from {{RFC3986}} and `ALPHA`
and `DIGIT` from {{RFC5234}}.

~~~ abnf
agent-uri    = "agent://" dns-name [ name-path ] [ "#" fragment ]

dns-name     = label 1*( "." label )
label        = let-dig [ *61( let-dig / "-" ) let-dig ]
let-dig      = ALPHA / DIGIT

name-path    = 1*8( "/" name-segment )
name-segment = lc-let-dig [ *61( lc-let-dig / "-" ) lc-let-dig ]
lc-let-dig   = %x61-7A / DIGIT        ; a-z, 0-9
~~~
{: #fig-abnf title="ABNF for the agent URI"}

Additional constraints:

- `dns-name` MUST NOT exceed 253 octets, and its final label MUST contain at
  least one `ALPHA` character. Together with the ABNF, this excludes IPv4
  addresses in dotted-decimal form and single-label names such as
  `localhost`.
- Internationalized domain names MUST be represented as A-labels
  {{RFC5890}} {{RFC5891}}. IP literals, `userinfo`, ports, and queries are not
  permitted.
- An agent URI with no `name-path` (e.g., `agent://planner.example.com`)
  identifies the domain's root agent.

Examples:

- `agent://example.com/planner`
- `agent://planner.example.com`
- `agent://example.com/acme/billing-assistant`
- `agent://example.com/planner#kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k`
  (a reference to one of the agent's keys; see {{fragments}})

## Normalization and Comparison {#normalization}

The canonical form of an agent URI is produced by:

1. Lowercasing the scheme and `dns-name`.
2. Converting any U-labels to A-labels.
3. Removing a ":443" port, or a ":" with an empty port, after the host.
4. Removing a single trailing "/" if present.

Parsers MAY accept input that differs from the ABNF only by the deviations
corrected above, and MUST normalize it. Any other deviation (another port,
uppercase in `name-path`, percent-encoding, dot-segments, a query, a trailing
"." on the host) MUST be rejected.

Two agent URIs identify the same agent if and only if their canonical forms,
with any fragment removed, are identical octet strings. In particular,
`agent://example.com/planner` and `agent://planner.example.com` are different
agents, even if the same operator runs both.

Agent URIs in AIDs, statements, and tokens MUST be in canonical form and MUST
NOT contain a fragment, unless a fragment is explicitly permitted.

## Dereferencing {#dereference}

An agent URI is dereferenced by mapping it to its AID URL:

~~~
https://<dns-name>/.well-known/agent<name-path>      (named agent)
https://<dns-name>/.well-known/agent/_                (root agent)
~~~

For example:

| Agent URI                                   | AID URL                                                      |
| ------------------------------------------- | ------------------------------------------------------------ |
| `agent://example.com/planner`               | `https://example.com/.well-known/agent/planner`              |
| `agent://example.com/acme/billing-assistant`| `https://example.com/.well-known/agent/acme/billing-assistant` |
| `agent://planner.example.com`               | `https://planner.example.com/.well-known/agent/_`            |
{: #tab-mapping title="Agent URI to AID URL mapping"}

The root agent uses the reserved segment `_`, which cannot appear in a
`name-segment`. This allows the root AID and named AIDs to coexist on static
file hosting, so an operator needs nothing more than the ability to serve
static files over HTTPS for the domain.

The mapping is purely syntactic and reversible: an HTTPS URL is an AID URL if
and only if it has no port, query, or fragment and applying the reverse
mapping yields an agent URI that is valid and canonical. No registry or index
needs to be fetched to dereference an agent URI.

## Fragments {#fragments}

A fragment in an agent URI identifies an Agent Key by its Key Identifier
({{key-ids}}). No other fragment semantics are defined.

# Agent Identity Document {#aid}

## Format {#aid-format}

An AID is a JSON object {{RFC8259}} served with media type
`application/agent-id+json` ({{iana-media-type}}). It has the following
members:

`id`:
: REQUIRED. String. The canonical agent URI that this document describes.

`operator`:
: REQUIRED. Object stating who the agent claims is accountable for it, with
  members `name` (REQUIRED, string) and `url` (OPTIONAL, string, HTTPS URL).
  These values are self-asserted ({{sec-operator}}).

`keys`:
: REQUIRED for origin-anchored agents; MUST be absent for DID-anchored
  agents. A JWK Set {{RFC7517}} containing the agent's public keys
  ({{origin-anchored}}).

`did`:
: OPTIONAL. String. A DID {{DID-CORE}} whose DID document is the anchor for
  this agent's keys ({{did-anchored}}).

`name`:
: OPTIONAL. String. A display name for people. It has no identity semantics.

`status`:
: OPTIONAL. String. One of `"active"` (default), `"suspended"`, or
  `"retired"` ({{lifecycle}}).

`links`:
: OPTIONAL. Array of link objects ({{aid-links}}).

`updated`:
: OPTIONAL. String. The time the document was last changed, as an RFC 3339
  {{RFC3339}} timestamp.

Members not defined here MUST be ignored by verifiers that do not understand
them. Extension member names SHOULD be namespaced (e.g., `"acme_tier"`) to
avoid collision with future versions of this document.

An AID MUST NOT exceed 64 KiB.

## Key Identifiers {#key-ids}

Every Agent Key is identified by its **Key Identifier**: the base64url-encoded
JWK SHA-256 Thumbprint {{RFC7638}} of the key, computed as specified in
{{RFC7638}} for EC keys and in {{Section A.3 of RFC8037}} for OKP keys. This is
the identifier {{WEB-BOT-AUTH}} uses for `keyid`. It is used everywhere a key
is named in this document: JWK `kid` values in an AID, agent URI fragments,
the JWS `kid` header of statements, and the `keyid` parameter of request
signatures.

Verifiers MUST compute the thumbprint of each candidate key themselves and
select keys by comparing it with the presented Key Identifier. They MUST NOT
rely on an operator-supplied `kid` or DID verification method `id` to select a
key. An AID or DID document in which two keys have the same Key Identifier
MUST be rejected.

For DID-anchored agents, each verification method is converted to a JWK before
the thumbprint is computed:

- a `publicKeyJwk` value is used as-is (private members MUST NOT be present);
- a `publicKeyMultibase` value that is a Multikey encoding of an Ed25519
  public key (base58btc with the `0xed01` header, as defined in {{CID}}) is
  converted to an OKP JWK with `"crv": "Ed25519"`; and
- verification methods in any other representation MAY be supported; those a
  verifier cannot convert are ignored.

## Key Purposes {#key-purposes}

Agent Keys have two purposes: **assertion** (signing statements,
{{statements}}) and **authentication** (signing HTTP requests,
{{request-signing}}).

For DID-anchored agents, a key is usable for assertion only if the DID
document's `assertionMethod` relationship references it, and for
authentication only if `authentication` references it {{DID-CORE}}.

For origin-anchored agents, a JWK MAY carry an `agent_use` member
({{iana-jwk-params}}): an array containing `"assertion"`, `"authentication"`,
or both. A key without `agent_use` is usable for both purposes. A key whose
`agent_use` is not an array of strings, or contains no recognized value, MUST
be ignored.

Verifiers MUST enforce key purposes. Operators SHOULD give every key a single
purpose, so that a key held by a running agent for signing requests cannot
sign statements ({{sec-key-compromise}}).

## Links {#aid-links}

Each link object has the following members, with the semantics of Web Linking
{{RFC8288}}:

`rel`:
: REQUIRED. String. A registered link relation type or a URI.

`href`:
: REQUIRED. String. An absolute HTTPS URL.

`type`:
: OPTIONAL. String. The media type of the target.

`statement`:
: OPTIONAL. String. An Agent Statement ({{statements}}) about the target.

Link relations expected to be common include:

| Relation                 | Target                                                     |
| ------------------------ | ---------------------------------------------------------- |
| `agent-card`             | The agent's {{A2A}} Agent Card                             |
| `mcp-server-card`        | The agent's {{MCP}} server metadata                        |
| `service-desc`           | An OpenAPI or other API description {{RFC9727}}            |
{: #tab-links title="Common link relations"}

For origin-anchored agents, a link whose `href` has the same origin as the
AID Origin is trusted to the same degree as the AID itself. To compare, the
verifier lowercases the `href` host, converts it to A-labels, and uses port
443 if none is present; the result must equal the AID Origin exactly
({{tv-origin}}). No other normalization is applied. Every other link MUST
carry a `statement`, and verifiers MUST ignore links without a valid one
({{statement-verify}}).

For DID-anchored agents, every link MUST carry a statement signed with a key
usable for assertion, and verifiers MUST ignore links without one; otherwise
whoever controls the origin could replace linked metadata without holding any
key authorized by the DID.

## Example {#aid-example}

~~~ json
{
  "id": "agent://example.com/planner",
  "name": "Example Trip Planner",
  "operator": {
    "name": "Example Travel Ltd",
    "url": "https://example.com"
  },
  "keys": {
    "keys": [
      {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo",
        "kid": "kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k",
        "alg": "EdDSA",
        "use": "sig"
      }
    ]
  },
  "links": [
    {
      "rel": "agent-card",
      "href": "https://example.com/planner/agent-card.json",
      "type": "application/json"
    },
    {
      "rel": "mcp-server-card",
      "href": "https://cdn.example.net/planner/server.json",
      "statement": "eyJ0eXAiOiJhZ2VudC1zdGF0ZW1lbnQrand0Ii..."
    }
  ],
  "updated": "2026-10-20T09:00:00Z"
}
~~~
{: #fig-aid-example title="Example Agent Identity Document (origin-anchored)"}

## Retrieval and Validation {#aid-retrieval}

To obtain the AID for an agent URI, a verifier:

1. Parses and canonicalizes the agent URI ({{normalization}}), rejecting it on
   failure.
2. Constructs the AID URL ({{dereference}}).
3. Applies the fetch policy of {{sec-fetch}}.
4. Sends an HTTPS GET with `Accept: application/agent-id+json`, validating the
   server certificate for `dns-name`.
5. Treats any status code other than 200 (OK) {{RFC9110}}, and other than
   304 (Not Modified) received in response to a conditional request
   revalidating a cached copy {{RFC9111}}, as a retrieval failure. Redirects
   are always failures.
6. Rejects responses larger than 64 KiB, or that are not valid JSON objects.
   Verifiers MUST NOT reject a response solely because its media type is
   `application/json` (to support static hosting) but MUST reject any other
   media type.
7. Rejects the document unless its `id` member is identical to the canonical
   agent URI.
8. Performs the anchoring checks of {{anchoring}}.

Verifiers SHOULD cache AIDs according to HTTP caching {{RFC9111}}. Operators
SHOULD NOT set a freshness lifetime longer than 24 hours, so that key removal
takes effect promptly ({{lifecycle}}).

# Anchoring {#anchoring}

An Agent Key is *anchored* when the verifier has established that whoever
controls the agent URI published it. An AID uses exactly one of two anchoring
modes.

## Origin-Anchored Agents {#origin-anchored}

The AID contains `keys` and no `did`. The keys are anchored by the HTTPS
retrieval of {{aid-retrieval}}: control of the AID Origin is control of the
agent's identity.

Each JWK in `keys` MUST contain only public key parameters, have a `kid` equal
to its Key Identifier ({{key-ids}}), have an `alg` member, and be usable for
signatures (`"use": "sig"`, or a `key_ops` containing `"verify"`).

Implementations MUST support `EdDSA` (Ed25519) and `ES256`. Algorithms MUST be
restricted as described in {{RFC8725}}; in particular, `none` and symmetric
algorithms MUST NOT be accepted.

This mode needs nothing beyond static HTTPS hosting. Its weakness is that
identity is exactly as durable as control of the domain
({{sec-handle-reassignment}}).

## DID-Anchored Agents {#did-anchored}

The AID contains a `did` member and no `keys`. The agent's keys are the
verification methods of the DID document, with the purposes defined in
{{key-purposes}}.

The binding between the agent URI and the DID MUST be bidirectional: the AID
names the DID in `did`, and the DID document lists the canonical agent URI in
its `alsoKnownAs` property {{DID-CORE}}. Verifiers MUST check both directions
and MUST treat the agent as unverified if either is missing.

**Pinning.** A verifier that has previously verified an agent URI as
DID-anchored and recorded its DID MUST NOT attribute a later AID for that
agent URI to the same agent unless it names the same DID. An AID that is
origin-anchored or names a different DID MUST be treated as a different
identity (for example, by rejecting it, or by treating it as a new agent with
no history), not as a key rotation.

**Continuity and its limits.** For a verifier that has pinned the DID, DID
anchoring preserves identity across a rename or domain move: the operator
publishes an AID under the new agent URI and adds that URI to `alsoKnownAs`.
For a verifier with no prior state, DID anchoring gives no more assurance than
origin anchoring ({{sec-trust-model}}).

**DID methods.** A DID whose resolution depends on the same host as the agent
URI (for example, `did:web` on that host) adds no independence from the
origin. Operators SHOULD NOT use such a DID for DID anchoring, and verifiers
MUST NOT treat it as providing assurance beyond origin anchoring. DID methods
that support verifiable key-rotation history (for example, {{DID-WEBVH}} hosted
independently of the agent URI's host) are RECOMMENDED. Verifiers MUST
maintain an allowlist of DID methods they support and MUST reject any other
method.

## Lifecycle, Rotation, and Revocation {#lifecycle}

Removing a key from the AID (or DID document) revokes it: every statement it
signed stops verifying once verifiers' cached copies expire. Rotation and
revocation are therefore the same operation, and operators rotate as follows:

1. Publish the new key alongside the old one.
2. Re-issue all statements signed by the old key, including statements carried
   in AIDs copied by mirrors and registries.
3. Remove the old key once re-issued statements have propagated.

This document deliberately defines no list of retired keys: with a single way
to stop trusting a key, verifiers never have to distinguish a planned
retirement from a compromise. Statements about metadata that changes SHOULD
carry an `exp` so that copies held by third parties are refreshed regularly.

If `status` is `"suspended"` or `"retired"`, verifiers MUST treat all
signatures and statements from the agent as invalid. A retired agent URI
SHOULD NOT be reassigned to a different agent.

# Agent Statements {#statements}

An Agent Statement is a JWS {{RFC7515}} in compact serialization, signed with
an Agent Key usable for assertion, that binds the agent to a specific version
of a resource such as an Agent Card. It allows protocol metadata to be served
from any origin, mirrored, or included in registries without losing its link to
the agent.

The JWS Protected Header MUST contain `typ` (`"agent-statement+jwt"`), `alg`
(the algorithm of the signing key), and `kid` (the Key Identifier of the
signing key). The payload is a JWT Claims Set {{RFC7519}} with:

`iss`:
: REQUIRED. The canonical agent URI, without a fragment.

`sub`:
: REQUIRED. The URL of the resource the statement is about.

`resource_digest`:
: REQUIRED. An object with members `alg` (`"sha-256"`), `canon` (`"jcs"` or
  `"none"`), and `value` (the base64url-encoded digest). With `"jcs"`, the
  digest is computed over the resource canonicalized per {{RFC8785}}; with
  `"none"`, over the exact bytes of the representation.

`iat`:
: REQUIRED. Issue time.

`exp`:
: OPTIONAL. Expiry time.

A statement protects only the bytes of the resource it names, not other
resources that resource refers to.

## Verification {#statement-verify}

To verify a statement carried in a link of an AID, a verifier:

1. Checks that `typ` is `"agent-statement+jwt"`.
2. Checks that `iss` is identical to the AID's `id`, and checks the AID's
   `status` ({{lifecycle}}).
3. Checks that `sub` is identical to the link's `href`.
4. Selects an anchored key usable for assertion whose Key Identifier equals
   `kid`, and verifies the signature.
5. Checks `iat` and, if present, `exp`.
6. Obtains the resource at `sub`, either by fetching it under the policy of
   {{sec-fetch}} or by using a copy, and compares its digest with
   `resource_digest`.

Statements obtained other than through an AID link (for example, from a
registry) are verified in the same way, except that step 2 uses the AID
retrieved for `iss` and step 3 compares `sub` with the URL the verifier
intends to use.

# Request Signing {#request-signing}

## Signing {#sig-profile}

An agent proves its identity on an HTTP request by signing it as specified in
{{WEB-BOT-AUTH}}, with the additional requirements in this section. A request
signed this way is a conforming {{WEB-BOT-AUTH}} request.

The request MUST include a `Signature-Agent` Dictionary member, keyed by the
signature label, whose value is the agent's AID URL ({{dereference}}) and which
carries the parameter `type=agent-id`:

~~~ http
Signature-Agent: sig1="https://example.com/.well-known/agent/planner"
    ;type=agent-id
~~~
{: #fig-sig-agent title="Signature-Agent member (line break for display only)"}

The signature MUST:

- cover `@method`, `@authority`, `@target-uri`, and
  `"signature-agent";key="<label>"`, and also `content-digest` {{RFC9530}}
  when the request has content;
- include `created` and `expires`, with `expires` no more than 300 seconds
  after `created`;
- include a `keyid` equal to the Key Identifier of the signing key; and
- include `tag="web-bot-auth"`.

A `nonce` parameter SHOULD be included where the verifier is expected to detect
replay.

~~~ http
POST /v1/bookings HTTP/1.1
Host: api.example.net
Content-Type: application/json
Content-Digest: sha-256=:...:
Signature-Agent: sig1="https://example.com/.well-known/agent/planner"
    ;type=agent-id
Signature-Input: sig1=("@method" "@authority" "@target-uri"
    "signature-agent";key="sig1" "content-digest");
    created=1792486800;expires=1792486860;
    keyid="kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k";
    tag="web-bot-auth"
Signature: sig1=:...:
~~~
{: #fig-signed-request title="A signed request (line breaks for display only)"}

## Verification {#sig-verify}

A verifier MUST perform all of the following steps, and MUST NOT rely on a
generic HTTP Message Signatures implementation to enforce them:

1. Select the signature with `tag="web-bot-auth"` whose label has a
   `Signature-Agent` member with `type=agent-id`. If there is none, the
   request does not carry an agent identity under this document.
2. Check that the member value is exactly an AID URL, without normalizing it,
   and derive the agent URI from it by reverse mapping ({{dereference}}).
3. Check that the covered components include every component required by
   {{sig-profile}}, that `expires` is no more than 300 seconds after
   `created`, and that the current time is between them, allowing for modest
   clock skew.
4. Retrieve the AID ({{aid-retrieval}}) and check `status` ({{lifecycle}}).
5. Select an anchored key usable for authentication whose Key Identifier
   equals `keyid`. Key lookup is keyed on the pair (agent URI, `keyid`), as
   required by {{WEB-BOT-AUTH}}.
6. Verify the signature as specified in {{RFC9421}}.
7. If the request has content, recompute its digest as specified in
   {{RFC9530}} and compare it with the covered `Content-Digest` value. A
   request with content and a missing, unsupported, or mismatched
   `Content-Digest` MUST be rejected, because a valid signature over
   `Content-Digest` does not by itself authenticate the content
   ({{Section 7.2.8 of RFC9421}}).

On success, the verifier has established that the request, including its
content, was made by a holder of a key anchored to the agent URI. On failure,
the verifier MUST NOT treat the request as coming from the named agent; it MAY
process it as an unauthenticated request.

A {{WEB-BOT-AUTH}} verifier that does not support `type=agent-id` ignores the
member, as that specification requires, and so treats the request as not
signed by a known agent rather than failing.

# Use with OAuth {#oauth}

Identity is not authorization, and this document defines no new OAuth
mechanisms. It adds one rule: **only a request signature verified under
{{request-signing}} establishes agent identity.** OAuth client authentication,
of any kind, authenticates an OAuth client, not an agent. An authorization
server MUST NOT present a client to users, or record it, as a verified agent
unless the request in question carries such a signature, and the agent it
attributes is always the one derived from that signature.

Consent screens are reached through front-channel redirects that an agent
cannot sign. An authorization server can therefore show a verified agent
identity at consent only if the agent signed a back-channel request for the
same authorization request beforehand. Agents that want this SHOULD use Pushed
Authorization Requests {{RFC9126}} and sign the pushed request. When a
verified identity is shown, it MUST be the agent URI or DID, with the operator
name presented as claimed by the agent ({{sec-operator}}).

When an agent acts on behalf of a user or another agent, the delegation SHOULD
be expressed with OAuth 2.0 Token Exchange {{RFC8693}}, with the agent
identified in the `act` claim by `"sub"` set to its canonical agent URI. As
required by {{RFC8693}}, only the current actor is relevant to access-control
decisions.

Access tokens used by agents SHOULD be sender-constrained, for example with
DPoP {{RFC9449}}, using a key that is not an Agent Key usable for assertion.
Resource servers MAY require a valid agent signature in addition to an access
token.

# Discovery {#discovery}

Dereferencing a known agent URI requires no discovery. To let others find
which agents a domain operates, a domain MAY list them in an API catalog
{{RFC9727}} (a linkset {{RFC9264}}) at `/.well-known/api-catalog`, using the
agent URI as the link context and `agent-identity` links to the AIDs:

~~~ json
{
  "linkset": [
    {
      "anchor": "agent://example.com/planner",
      "agent-identity": [
        { "href": "https://example.com/.well-known/agent/planner",
          "type": "application/agent-id+json" }
      ]
    }
  ]
}
~~~
{: #fig-catalog title="Listing agents in an API catalog"}

Publishing a catalog is optional ({{privacy}}). Registries and search services
that index agents SHOULD verify AIDs and statements themselves rather than
asking clients to trust the index.

# Security Considerations {#security}

## Trust Model {#sec-trust-model}

For origin-anchored agents, the trust anchors are DNS and the Web PKI: anyone
who can obtain a certificate for the agent URI's host and serve content there
can impersonate the agent. This is the same trust model as the web itself and
is appropriate for most agents.

DID anchoring reduces this dependency only for verifiers that have pinned the
agent's DID ({{did-anchored}}). On first contact, a verifier cannot tell a
legitimate origin-anchored agent from an attacker who has taken over the
domain and replaced a DID-anchored AID with an origin-anchored one. Even for a
pinned DID, assurance holds only if verifiers rely solely on DID-authorized
keys and on metadata covered by statements made with them ({{aid-links}}).

## Handle Reassignment {#sec-handle-reassignment}

If a domain lapses and is registered by someone else, the new holder can
publish an AID for the same agent URIs. Verifiers that record identities for
audit or reputation SHOULD record the Key Identifiers (and DID, when present)
alongside the agent URI, and SHOULD treat a change of all keys for an agent as
a significant event.

## Operator Claims {#sec-operator}

Verification establishes possession of a key anchored to an agent URI or DID.
It does not establish who operates the agent: `operator.name` and
`operator.url` are supplied by the same party that publishes the AID. The
owner of `attacker.example` can claim `"Example Travel Ltd"` as operator and
point `operator.url` at the real company's website.

User interfaces and logs MUST NOT present an operator name as verified unless
it has been confirmed by a separate mechanism trusted by the verifier, which
this document does not define. They SHOULD display the authenticated agent URI
host (in A-label form) or DID alongside any operator name.

## Verifier-Initiated Fetches {#sec-fetch}

Verification causes network requests to destinations chosen by untrusted
parties: AID URLs from `Signature-Agent` values, statement subjects, and
requests made by DID resolvers. Each of these can be used for server-side
request forgery or denial of service. The following policy applies to
**every** fetch made in the course of verification:

- Only HTTPS URLs are fetched, with certificate validation.
- Destinations whose host is, or resolves to, an address that the IANA IPv4 or
  IPv6 Special-Purpose Address Registries {{RFC6890}} mark as not globally
  reachable MUST NOT be fetched, nor hosts that are special-use names that do
  not resolve in the global DNS (for example, `localhost` or names under
  `local` or `internal`). Administrators MAY configure explicit exceptions for
  private deployments.
- The resolved address MUST be checked and then used for the connection
  (pinned), so that DNS changes cannot redirect the request after the check.
- HTTP redirects MUST NOT be followed, as in {{WEB-BOT-AUTH}}.
- Verifiers MUST enforce timeouts and bound response sizes: 64 KiB for AIDs
  and a locally configured limit for other resources.
- Verifiers MUST bound the number of fetches per verification; a limit of 4
  (for example, the AID, a DID resolution, and a statement subject) is
  RECOMMENDED, with a DID resolution counting as one fetch and the requests a
  DID resolver makes bounded separately. Verifiers MUST NOT recursively follow
  links from fetched documents.
- Verifiers MUST rate-limit fetches per host and cache results, including
  failures.

A statement whose signature is valid does not make its `sub` safe to fetch:
an attacker can publish a legitimate AID under its own domain and sign a
statement whose `sub` names an internal address.

## Request Content and Replay {#sec-replay}

HTTP message signatures authenticate header values, not content. Verifiers
MUST recompute `Content-Digest` over received content ({{sig-verify}});
otherwise an attacker can change the content of a signed request while keeping
the signed digest.

Signatures cover the method, target URI, and authority, which prevents replay
against a different resource or service. The short `created`-`expires` window
limits replay against the same resource; verifiers for non-idempotent
operations SHOULD require and track `nonce` values.

## Key Compromise {#sec-key-compromise}

Compromise of an Agent Key lets the attacker act as the agent until the key is
removed and caches expire. Operators SHOULD keep Agent Keys in hardware or a
key management service, and SHOULD use separate keys for assertion and
authentication ({{key-purposes}}), so that compromise of a running agent does
not let the attacker sign statements.

## Cross-Origin Metadata {#sec-cross-origin}

Requiring statements bound to the exact `href` for links outside the AID
Origin ({{aid-links}}, {{statement-verify}}) prevents a compromised or
malicious third-party host, mirror, or registry from attaching metadata to an
agent's identity. A statement only proves that the agent published the
resource; it does not vouch for the truth of the resource's contents.

## Confusable Names {#sec-confusables}

Agent URIs can be visually similar (e.g., `agent://examp1e.example/planner`
and `agent://example.example/planner`). User interfaces that display agent
identities SHOULD display the A-label form of the host, and SHOULD warn when an
agent URI or DID is new to the user.

# Privacy Considerations {#privacy}

The considerations of {{RFC6973}} apply.

- **Linkability is the point, for agents.** Request signatures make an agent's
  traffic attributable and linkable across services. That is intended for the
  agent; it must not extend to the people it acts for. Agent URIs and
  `Signature-Agent` values MUST NOT encode user identifiers.
- **Per-user agents.** Deployments that create one agent per end user (e.g.,
  `agent://example.com/u/alice`) make that user's activity linkable across all
  services the agent visits. Such deployments SHOULD use a shared agent
  identity and convey user context only through authorization tokens sent to
  parties entitled to it.
- **Enumeration.** API catalogs ({{discovery}}) let anyone list a domain's
  agents. Domains that do not want their agents to be enumerable should not
  publish them in a catalog; AIDs remain retrievable by those who already
  know the agent URI.
- **Verifier fetches.** Fetching an AID reveals to the operator that a
  verifier has seen the agent. Caching reduces this signal.

# IANA Considerations {#iana}

## URI Scheme Registration {#iana-uri-scheme}

IANA is requested to register the `agent` URI scheme in the "Uniform Resource
Identifier (URI) Schemes" registry, using the template of {{RFC7595}}:

Scheme name:
: agent

Status:
: Permanent

Applications/protocols that use this scheme name:
: Identification of software agents. An agent URI is dereferenced to an Agent
  Identity Document as described in {{dereference}}.

Contact:
: IESG &lt;iesg@ietf.org&gt;

Change controller:
: IETF

References:
: {{agent-uri}} of this document

Well-Known URI Support:
: The `agent` well-known URI ({{iana-well-known}})

## Well-Known URI Registration {#iana-well-known}

IANA is requested to register the following in the "Well-Known URIs" registry
{{RFC8615}}:

URI suffix:
: agent

Change controller:
: IETF

Specification document(s):
: {{dereference}} of this document

Status:
: permanent

Related information:
: Sub-paths are used: `/.well-known/agent/<name-path>` for named agents and
  `/.well-known/agent/_` for a host's root agent.

## Media Types {#iana-media-type}

IANA is requested to register the following media types in the "Media Types"
registry {{RFC6838}}.

### application/agent-id+json

Type name:
: application

Subtype name:
: agent-id+json

Required parameters:
: N/A

Optional parameters:
: N/A

Encoding considerations:
: binary; an Agent Identity Document is JSON {{RFC8259}} encoded in UTF-8.

Security considerations:
: See {{security}} of this document.

Interoperability considerations:
: N/A

Published specification:
: {{aid}} of this document

Applications that use this media type:
: Verifiers of agent identity, such as websites, APIs, authorization servers,
  registries, and other agents.

Fragment identifier considerations:
: As specified for the `+json` structured syntax suffix in
  {{Section 3.1 of RFC6839}}.

Additional information:
: Deprecated alias names for this type: N/A; Magic number(s): N/A; File
  extension(s): N/A; Macintosh file type code(s): N/A

Person & email address to contact for further information:
: IESG &lt;iesg@ietf.org&gt;

Intended usage:
: COMMON

Restrictions on usage:
: N/A

Author:
: See the Authors' Addresses section of this document.

Change controller:
: IETF

### application/agent-statement+jwt

Type name:
: application

Subtype name:
: agent-statement+jwt

Required parameters:
: N/A

Optional parameters:
: N/A

Encoding considerations:
: 7bit; an Agent Statement is a JWS Compact Serialization {{RFC7515}}, a
  sequence of base64url-encoded values separated by period characters. The
  `+jwt` structured syntax suffix is registered by {{RFC8417}}.

Security considerations:
: See {{security}} of this document.

Interoperability considerations:
: N/A

Published specification:
: {{statements}} of this document

Applications that use this media type:
: Agents publishing statements about their protocol metadata, and verifiers
  of those statements.

Fragment identifier considerations:
: N/A

Additional information:
: Deprecated alias names for this type: N/A; Magic number(s): N/A; File
  extension(s): N/A; Macintosh file type code(s): N/A

Person & email address to contact for further information:
: IESG &lt;iesg@ietf.org&gt;

Intended usage:
: COMMON

Restrictions on usage:
: N/A

Author:
: See the Authors' Addresses section of this document.

Change controller:
: IETF

## Signature-Agent Type {#iana-sig-agent-type}

{{request-signing}} uses the `Signature-Agent` member parameter value
`type=agent-id`. {{WEB-BOT-AUTH}} does not currently establish a registry of
type values. This document asks that such a registry be created and that
`agent-id` be registered in it, referencing {{request-signing}} of this
document (see {{open-issues}}).

## Link Relation {#iana-link-relations}

IANA is requested to register the following in the "Link Relation Types"
registry {{RFC8288}}:

Relation Name:
: agent-identity

Description:
: Refers to the Agent Identity Document of the link context.

Reference:
: {{discovery}} of this document

Registration of `agent-card` and `mcp-server-card` is an open issue
({{open-issues}}).

## JSON Web Key Parameter {#iana-jwk-params}

IANA is requested to register the following in the "JSON Web Key Parameters"
registry {{RFC7517}}:

Parameter Name:
: agent_use

Parameter Description:
: Purposes for which an Agent Key may be used

Used with "kty" Value(s):
: *

Parameter Information Class:
: Public

Change Controller:
: IETF

Specification Document(s):
: {{key-purposes}} of this document

## JSON Web Token Claim {#iana-jwt-claims}

IANA is requested to register the following in the "JSON Web Token Claims"
registry {{RFC7519}}:

Claim Name:
: resource_digest

Claim Description:
: Digest of the resource identified by the sub claim

Change Controller:
: IETF

Specification Document(s):
: {{statements}} of this document

--- back

# Test Vectors: Agent URI Processing {#test-vectors}

This appendix is informative. It gives expected results for the syntactic
processing defined in {{agent-uri}} and {{aid-links}}, so that independent
implementations can check that they agree.

## Parsing and Canonicalization {#tv-parsing}

Each vector shows an input, then its result. "valid" inputs are canonical.
"normalized" inputs differ from the ABNF only by deviations listed in
{{normalization}}; parsers MAY accept them and, if they do, MUST produce the
canonical form shown. "reject" inputs MUST be rejected. `<U+00FC>` denotes the
single character LATIN SMALL LETTER U WITH DIAERESIS.

~~~
agent://example.com/planner
    valid       agent://example.com/planner
agent://planner.example.com
    valid       agent://planner.example.com    (root agent)
agent://example.com/acme/billing-assistant
    valid       agent://example.com/acme/billing-assistant
agent://123.example/planner
    valid       agent://123.example/planner
agent://example.com/p#kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k
    valid       agent://example.com/p          (plus key fragment)

AGENT://Example.COM/planner
    normalized  agent://example.com/planner
agent://example.com:443/planner
    normalized  agent://example.com/planner
agent://example.com:/planner
    normalized  agent://example.com/planner
agent://example.com/planner/
    normalized  agent://example.com/planner
agent://planner.example.com/
    normalized  agent://planner.example.com
agent://b<U+00FC>cher.example/planner
    normalized  agent://xn--bcher-kva.example/planner

agent://192.168.0.1/planner             reject  all-digit final label
agent://localhost/planner               reject  single-label host
agent://[::1]/planner                   reject  IP literal
agent://user@example.com/planner        reject  userinfo
agent://example.com./planner            reject  trailing "." on host
agent://example.com:8443/planner        reject  port
agent://example.com:0443/planner        reject  port
agent://example.com/planner?task=1      reject  query
agent://example.com/Planner             reject  uppercase name-path
agent://example.com/plan%6Eer           reject  percent-encoding
agent://example.com/a/../planner        reject  dot-segment
agent://example.com//planner            reject  empty segment
agent://example.com/-planner            reject  leading "-"
agent://example.com/_                   reject  reserved segment
agent://example.com/a/b/c/d/e/f/g/h/i   reject  more than 8 segments
agent+https://example.com/planner       reject  not the agent scheme
~~~
{: #fig-tv-parsing title="Parsing and canonicalization vectors"}

`agent://example.com/p` with and without the key fragment identify the same
agent ({{normalization}}).

## Mapping to AID URLs {#tv-mapping}

~~~
agent://example.com/planner
    https://example.com/.well-known/agent/planner
agent://planner.example.com
    https://planner.example.com/.well-known/agent/_
agent://example.com/acme/billing-assistant
    https://example.com/.well-known/agent/acme/billing-assistant
agent://xn--bcher-kva.example/planner
    https://xn--bcher-kva.example/.well-known/agent/planner
~~~
{: #fig-tv-mapping title="Agent URI to AID URL vectors"}

## Reverse Mapping of Signature-Agent Values {#tv-reverse}

Values are compared exactly, without normalization ({{sig-verify}}).

~~~
https://example.com/.well-known/agent/planner
    agent://example.com/planner
https://planner.example.com/.well-known/agent/_
    agent://planner.example.com
https://example.com:8443/.well-known/agent/planner
    reject  port
https://Example.com/.well-known/agent/planner
    reject  not canonical (host case)
https://example.com:443/.well-known/agent/planner
    reject  not canonical (default port)
https://example.com/.well-known/agent/planner/
    reject  not canonical (trailing "/")
https://example.com/.well-known/agent/planner?v=1
    reject  query
http://example.com/.well-known/agent/planner
    reject  not HTTPS
https://example.com/.well-known/agent
    reject  neither a name-path nor the reserved segment
https://example.com/.well-known/agent/_/planner
    reject  reserved segment inside a name-path
https://example.com/.well-known/agent/Planner
    reject  invalid name-path
https://example.com/.well-known/agent/planner#k
    reject  fragment
https://b<U+00FC>cher.example/.well-known/agent/planner
    reject  not canonical (U-label host)
~~~
{: #fig-tv-reverse title="Reverse mapping vectors"}

## AID Origin Comparison {#tv-origin}

For `agent://example.com/planner`, the AID Origin is ("https", "example.com",
443). Link targets compare as follows ({{aid-links}}):

~~~
https://example.com/planner/agent-card.json         same origin
https://example.com:443/planner/agent-card.json     same origin
https://EXAMPLE.com/planner/agent-card.json         same origin
https://planner.example.com/agent-card.json         different host
https://example.com:8443/planner/agent-card.json    different port
https://example.com./planner/agent-card.json        different host
http://example.com/planner/agent-card.json          invalid href
~~~
{: #fig-tv-origin title="AID Origin comparison vectors"}

A link whose `href` is not an HTTPS URL is invalid regardless of origin, and a
statement cannot make it valid ({{aid-links}}).

# Open Issues {#open-issues}

This appendix will be removed before publication.

1. **Signature-Agent type registry.** {{WEB-BOT-AUTH}} has no registry for
   `type` values. Work with the webbotauth WG to create one, or to define
   `agent-id` there. Until then, verifiers that only implement
   {{WEB-BOT-AUTH}} ignore agent identities.
2. **Back-references from protocol metadata.** Agree with the A2A and MCP
   projects on how an Agent Card or MCP server card names its agent URI, and
   who registers the `agent-card` and `mcp-server-card` link relations.
3. **Companion documents.** Credentials for short-lived agent instances
   (in -04, a profile of the WIMSE Workload Identity Token) and bindings of
   agent keys to OAuth client authentication (in -04, `private_key_jwt`
   attribution) are to be specified separately, in coordination with the
   WIMSE and OAuth working groups.
4. **Cryptographic test vectors.** {{test-vectors}} covers URI processing.
   Once an implementation can produce and cross-check them, add vectors for
   statement `iss`/`sub` binding, DID key conversion and per-purpose
   selection, `agent_use` enforcement, content tampering with a valid
   signature, fetches to forbidden destinations, and expired statements.

# Changes from draft-narvaneni-agent-uri-04 {#changes}

This revision simplifies the document so that each task has one mechanism.

Removed or moved out:

- **Ports.** Agent URIs no longer contain ports, so an agent's identity
  depends only on its host and name.
- **Instance credentials.** The profile of the WIMSE Workload Identity Token
  moves to a companion document ({{open-issues}}).
- **OAuth client-authentication attribution.** The association check,
  qualifying-key rules, and the `agent_uri` client metadata parameter are
  removed. Only a verified request signature establishes agent identity
  ({{oauth}}).
- The appendix listing changes from draft-narvaneni-agent-uri-03.

Added or completed:

- Full IANA registration templates.
- "One way to do each thing" as a design principle.

Closed open issues:

- **Retired keys:** the re-issue model is kept, giving a single way to stop
  trusting a key ({{lifecycle}}).
- **DNS-based verification:** not adopted. Any operator that can obtain a TLS
  certificate for a domain can serve AIDs from static hosting, and a DNS
  alternative would need DNSSEC and a second verification path.
- **Reserved root segment and name-path rules:** kept as specified.
- **Ports:** removed.

# Acknowledgments {#acknowledgments}
{:numbered="false"}

The authors thank the reviewers of earlier revisions, whose feedback shaped
this document.
