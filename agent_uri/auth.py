"""
Authentication and signature-verification helpers for agent://.

Aligned with draft-narvaneni-agent-uri-03. Includes:

* :class:`BearerTokenAuth`, :class:`ApiKeyAuth`, :class:`MutualTLSAuth` —
  ``AuthProvider`` implementations that attach credentials to requests.
* :class:`OAuthASMetadata` — RFC 8414 authorization-server metadata
  fetcher with basic TTL caching.
* :class:`ProtectedResourceMetadata` — RFC 9728 resource metadata fetcher.
* :class:`TokenExchangeClient` — RFC 8693 token-exchange helper. Builds
  nested ``act`` claims and enforces scope narrowing on each step.
* :class:`MessageSignatureVerifier` — RFC 9421 HTTP Message Signatures
  verifier with RFC 9530 ``Content-Digest`` support.
* :class:`JWSDescriptorVerifier` — fallback RFC 7515 + RFC 8785 JCS
  descriptor signing for deployments without HTTP Message Signatures.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import ssl
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

import requests

try:
    import jwt  # type: ignore[import]
except ImportError:
    jwt = None  # type: ignore[assignment]

from .exceptions import (
    AuthenticationError,
    DelegationError,
    KeyDiscoveryError,
    ScopeNarrowingViolationError,
    SignatureVerificationError,
)

logger = logging.getLogger(__name__)


class AuthProvider(ABC):
    """Adds authentication credentials to outgoing requests."""

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Return headers to merge into the request."""

    def get_auth_params(self) -> Dict[str, str]:
        """Return query-string params to merge into the request."""
        return {}

    @abstractmethod
    def refresh(self) -> None:
        """Refresh credentials if expired."""

    @property
    def is_expired(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Basic credential holders
# ---------------------------------------------------------------------------


class BearerTokenAuth(AuthProvider):
    """Bearer-token auth (OAuth 2.0 access tokens, JWTs, ...)."""

    def __init__(
        self,
        token: str,
        token_type: str = "Bearer",  # nosec B107
        expires_at: Optional[int] = None,
        refresh_callback: Optional[Callable[[], Any]] = None,
    ):
        self.token = token
        self.token_type = token_type
        self.expires_at = expires_at
        self.refresh_callback = refresh_callback

        if expires_at is None and jwt is not None and token:
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
                if "exp" in payload:
                    self.expires_at = payload["exp"]
            except Exception as e:
                logger.debug("Could not extract JWT exp: %s", e)

    def get_auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"{self.token_type} {self.token}"}

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > (self.expires_at - 30)

    def refresh(self) -> None:
        if not self.is_expired:
            return
        if not self.refresh_callback:
            raise AuthenticationError(
                "Token is expired and no refresh callback provided"
            )
        try:
            new = self.refresh_callback()
            if isinstance(new, dict):
                self.token = new.get("access_token", "")
                self.expires_at = new.get("expires_at")
            else:
                self.token = new
        except Exception as e:
            raise AuthenticationError(f"Failed to refresh token: {e}")


class ApiKeyAuth(AuthProvider):
    """API key auth, carried in a header or query parameter."""

    def __init__(
        self,
        api_key: str,
        header_name: str = "X-API-Key",
        param_name: Optional[str] = None,
    ):
        self.api_key = api_key
        self.header_name = header_name
        self.param_name = param_name

    def get_auth_headers(self) -> Dict[str, str]:
        if self.param_name is None:
            return {self.header_name: self.api_key}
        return {}

    def get_auth_params(self) -> Dict[str, str]:
        if self.param_name is not None:
            return {self.param_name: self.api_key}
        return {}

    def refresh(self) -> None:
        return None


class MutualTLSAuth(AuthProvider):
    """RFC 8705 mutual-TLS (certificate-bound) credential holder.

    Actual certificate presentation is done by the transport layer when
    it builds the SSL context; this provider just surfaces the cert/key
    paths so callers can wire them through.
    """

    def __init__(
        self,
        cert_path: str,
        key_path: Optional[str] = None,
        ca_path: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.password = password

    def get_auth_headers(self) -> Dict[str, str]:
        return {}

    def refresh(self) -> None:
        return None

    def build_ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context(cafile=self.ca_path)
        ctx.load_cert_chain(
            certfile=self.cert_path,
            keyfile=self.key_path,
            password=self.password,
        )
        return ctx


# ---------------------------------------------------------------------------
# OAuth metadata fetchers (RFC 8414 / RFC 9728)
# ---------------------------------------------------------------------------


class _CachedFetcher:
    """Generic JSON fetcher with TTL caching."""

    def __init__(
        self, ttl_seconds: int = 600, timeout: int = 30, verify_ssl: bool = True
    ):
        self._ttl = ttl_seconds
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def _get(self, url: str, error_cls: type) -> Dict[str, Any]:
        now = time.time()
        hit = self._cache.get(url)
        if hit and hit[0] > now:
            return hit[1]
        try:
            resp = requests.get(
                url,
                timeout=self._timeout,
                verify=self._verify_ssl,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise error_cls(f"Failed to fetch metadata from {url}: {e}")
        except ValueError as e:
            raise error_cls(f"Invalid JSON at {url}: {e}")
        self._cache[url] = (now + self._ttl, data)
        return data


class OAuthASMetadata(_CachedFetcher):
    """RFC 8414 authorization-server metadata fetcher.

    Given an issuer URL (e.g. ``https://issuer.example.com``), fetches
    ``<issuer>/.well-known/oauth-authorization-server`` and returns the
    parsed metadata dict. Results are cached for ``ttl_seconds``.
    """

    WELL_KNOWN = "/.well-known/oauth-authorization-server"

    def fetch(self, issuer: str) -> Dict[str, Any]:
        url = issuer.rstrip("/") + self.WELL_KNOWN
        return self._get(url, KeyDiscoveryError)

    def token_endpoint(self, issuer: str) -> str:
        md = self.fetch(issuer)
        endpoint = md.get("token_endpoint")
        if not isinstance(endpoint, str):
            raise KeyDiscoveryError(
                f"AS metadata for {issuer} has no token_endpoint",
                source=issuer,
            )
        return endpoint

    def jwks_uri(self, issuer: str) -> Optional[str]:
        md = self.fetch(issuer)
        value = md.get("jwks_uri")
        return value if isinstance(value, str) else None


class ProtectedResourceMetadata(_CachedFetcher):
    """RFC 9728 protected-resource metadata fetcher."""

    WELL_KNOWN = "/.well-known/oauth-protected-resource"

    def fetch(self, resource_url: str) -> Dict[str, Any]:
        parsed = resource_url.rstrip("/") + self.WELL_KNOWN
        return self._get(parsed, KeyDiscoveryError)


# ---------------------------------------------------------------------------
# RFC 8693 Token Exchange + scope narrowing
# ---------------------------------------------------------------------------


def _scope_set(scope: Optional[str]) -> Set[str]:
    if not scope:
        return set()
    return set(s for s in scope.split() if s)


def _verify_scope_narrowing(
    outer_scope: Optional[str], inner_scope: Optional[str]
) -> None:
    """Inner scope must be a subset of outer; empty inner means inherit."""
    outer = _scope_set(outer_scope)
    inner = _scope_set(inner_scope)
    if not inner:
        return
    if outer and not inner.issubset(outer):
        widened = inner - outer
        raise ScopeNarrowingViolationError(
            f"Delegation widens scope: added {sorted(widened)}",
            outer_scope=outer_scope,
            inner_scope=inner_scope,
        )


class TokenExchangeClient:
    """RFC 8693 token-exchange helper.

    Builds requests with the standard ``grant_type`` and nested ``act``
    claims, and validates scope narrowing before sending. Obtains the
    token endpoint via :class:`OAuthASMetadata`.
    """

    def __init__(
        self,
        metadata: Optional[OAuthASMetadata] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        self.metadata = metadata or OAuthASMetadata()
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    # --------- static helpers ---------

    @staticmethod
    def build_act_claim(
        actor_sub: str,
        *,
        issuer: Optional[str] = None,
        inner_act: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Construct a nested ``act`` claim for the subject token payload."""
        act: Dict[str, Any] = {"sub": actor_sub}
        if issuer:
            act["iss"] = issuer
        if inner_act:
            act["act"] = inner_act
        return act

    @staticmethod
    def verify_delegation_chain(chain: List[Dict[str, Any]]) -> None:
        """Walk an ordered delegation chain verifying each step narrows scope.

        Chain order: index 0 is the outermost (original) token; each
        subsequent entry must not widen scope.
        """
        if not chain:
            return
        for i in range(1, len(chain)):
            outer = chain[i - 1].get("scope")
            inner = chain[i].get("scope")
            try:
                _verify_scope_narrowing(outer, inner)
            except ScopeNarrowingViolationError:
                raise
            except Exception as e:
                raise DelegationError(
                    f"Delegation chain step {i} invalid: {e}", reason="chain"
                )

    # --------- network ---------

    def exchange(
        self,
        issuer: str,
        subject_token: str,
        *,
        subject_token_type: str = ("urn:ietf:params:oauth:token-type:access_token"),
        requested_scope: Optional[str] = None,
        current_scope: Optional[str] = None,
        audience: Optional[str] = None,
        resource: Optional[str] = None,
        actor_token: Optional[str] = None,
        actor_token_type: Optional[str] = None,
        client_auth: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """Perform an RFC 8693 token exchange.

        ``current_scope`` should be the outer/subject token's scope; the
        requested scope is validated to be a subset before the network
        call is made.

        Raises:
            ScopeNarrowingViolationError: If requested_scope widens scope.
            DelegationError: If the token endpoint rejects the exchange.
        """
        _verify_scope_narrowing(current_scope, requested_scope)

        data: Dict[str, Any] = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": subject_token,
            "subject_token_type": subject_token_type,
        }
        if requested_scope:
            data["scope"] = requested_scope
        if audience:
            data["audience"] = audience
        if resource:
            data["resource"] = resource
        if actor_token:
            data["actor_token"] = actor_token
            data["actor_token_type"] = (
                actor_token_type or "urn:ietf:params:oauth:token-type:access_token"
            )

        token_url = self.metadata.token_endpoint(issuer)
        try:
            resp = requests.post(
                token_url,
                data=data,
                auth=client_auth,
                timeout=self.timeout,
                verify=self.verify_ssl,
                headers={"Accept": "application/json"},
            )
        except requests.RequestException as e:
            raise DelegationError(f"Token exchange request failed: {e}")

        if resp.status_code != 200:
            raise DelegationError(
                f"Token exchange rejected ({resp.status_code}): {resp.text}",
                reason=f"http_{resp.status_code}",
            )
        try:
            return resp.json()
        except ValueError as e:
            raise DelegationError(f"Invalid token-exchange response: {e}")


# ---------------------------------------------------------------------------
# RFC 9421 HTTP Message Signatures
# ---------------------------------------------------------------------------


_SIGNATURE_INPUT_RE = re.compile(
    r"(?P<label>[A-Za-z0-9_-]+)=\((?P<covered>[^)]*)\);(?P<params>.*)"
)
_PARAM_RE = re.compile(r'([A-Za-z0-9_-]+)=("([^"]*)"|([^;]+))')


class MessageSignatureVerifier:
    """Verifier for RFC 9421 ``Signature`` / ``Signature-Input`` headers.

    Parses the headers, reconstructs the signature base, and verifies
    the signature using a pluggable key resolver. RFC 9530
    ``Content-Digest`` verification is available via
    :meth:`verify_content_digest`.

    The signing key is discovered via a ``key_resolver`` callable that
    receives the ``keyid`` parameter and returns a PEM-encoded public
    key (or raises :class:`KeyDiscoveryError`).
    """

    def __init__(
        self,
        key_resolver: Callable[[str], bytes],
        allowed_algs: Optional[Iterable[str]] = None,
        max_age_seconds: int = 300,
    ):
        self.key_resolver = key_resolver
        self.allowed_algs = set(
            allowed_algs or ("ed25519", "ecdsa-p256-sha256", "rsa-pss-sha512")
        )
        self.max_age_seconds = max_age_seconds

    # ------------------------------------------------------------------

    def verify(
        self,
        *,
        method: str,
        target_uri: str,
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Verify the HTTP signature and return its parameters.

        Returns:
            The parsed signature parameters (label, covered, alg, keyid, ...).

        Raises:
            SignatureVerificationError: If verification fails.
        """
        sig_input = headers.get("Signature-Input") or headers.get("signature-input")
        signature = headers.get("Signature") or headers.get("signature")
        if not sig_input or not signature:
            raise SignatureVerificationError(
                "Missing Signature or Signature-Input header"
            )

        label, covered, params = self._parse_signature_input(sig_input)
        sig_bytes = self._parse_signature(signature, label)

        self._check_freshness(params)

        alg = params.get("alg")
        if alg and alg not in self.allowed_algs:
            raise SignatureVerificationError(
                f"Algorithm {alg!r} not in allowlist",
                component="alg",
            )

        keyid = params.get("keyid")
        if not keyid:
            raise SignatureVerificationError("Missing keyid parameter")
        try:
            public_key = self.key_resolver(keyid)
        except KeyDiscoveryError:
            raise
        except Exception as e:
            raise KeyDiscoveryError(f"Could not resolve keyid {keyid!r}: {e}")

        base = self._build_signature_base(
            method=method,
            target_uri=target_uri,
            headers=headers,
            covered=covered,
            params_raw=self._serialize_params(params),
        )
        self._verify_signature(
            public_key=public_key,
            alg=alg or "ed25519",
            signature=sig_bytes,
            signing_input=base.encode("utf-8"),
        )

        return {"label": label, "covered": covered, **params}

    @staticmethod
    def verify_content_digest(
        body: bytes,
        digest_header: str,
    ) -> None:
        """Verify an RFC 9530 ``Content-Digest`` structured-field header."""
        if not digest_header:
            raise SignatureVerificationError(
                "Missing Content-Digest header", component="content-digest"
            )
        # structured-field dict: algo=:base64:
        for entry in digest_header.split(","):
            entry = entry.strip()
            if "=" not in entry:
                continue
            algo, encoded = entry.split("=", 1)
            algo = algo.strip().lower()
            encoded = encoded.strip().strip(":")
            try:
                expected = base64.b64decode(encoded)
            except Exception as e:
                raise SignatureVerificationError(
                    f"Invalid Content-Digest encoding: {e}",
                    component="content-digest",
                )
            if algo == "sha-256":
                actual = hashlib.sha256(body).digest()
            elif algo == "sha-512":
                actual = hashlib.sha512(body).digest()
            else:
                continue
            if actual != expected:
                raise SignatureVerificationError(
                    f"Content-Digest mismatch for {algo}",
                    component="content-digest",
                )
            return
        raise SignatureVerificationError(
            "No supported digest algorithm in Content-Digest",
            component="content-digest",
        )

    # ------------------------------------------------------------------

    def _parse_signature_input(
        self, header: str
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        m = _SIGNATURE_INPUT_RE.match(header.strip())
        if not m:
            raise SignatureVerificationError(
                "Malformed Signature-Input", component="signature-input"
            )
        label = m.group("label")
        covered_raw = m.group("covered").strip()
        covered = [
            part.strip().strip('"') for part in covered_raw.split() if part.strip()
        ]
        params: Dict[str, Any] = {}
        for pm in _PARAM_RE.finditer(m.group("params")):
            key = pm.group(1)
            quoted = pm.group(3)
            bare = pm.group(4)
            if quoted is not None:
                params[key] = quoted
            else:
                stripped = (bare or "").strip()
                if stripped.isdigit():
                    params[key] = int(stripped)
                else:
                    params[key] = stripped
        return label, covered, params

    @staticmethod
    def _serialize_params(params: Dict[str, Any]) -> str:
        pieces: List[str] = []
        for key, value in params.items():
            if isinstance(value, int):
                pieces.append(f"{key}={value}")
            else:
                pieces.append(f'{key}="{value}"')
        return ";".join(pieces)

    def _parse_signature(self, header: str, label: str) -> bytes:
        """Pull the `<label>=:<base64>:` entry out of the Signature header."""
        for entry in header.split(","):
            entry = entry.strip()
            if not entry.startswith(f"{label}="):
                continue
            encoded = entry.split("=", 1)[1].strip().strip(":")
            try:
                return base64.b64decode(encoded)
            except Exception as e:
                raise SignatureVerificationError(
                    f"Invalid signature encoding: {e}", component="signature"
                )
        raise SignatureVerificationError(
            f"No signature entry for label {label!r}", component="signature"
        )

    def _check_freshness(self, params: Dict[str, Any]) -> None:
        created = params.get("created")
        expires = params.get("expires")
        now = int(time.time())
        if isinstance(expires, int) and expires < now:
            raise SignatureVerificationError(
                "Signature is expired", component="expires"
            )
        if isinstance(created, int) and now - created > self.max_age_seconds:
            raise SignatureVerificationError(
                "Signature created time exceeds max_age", component="created"
            )

    def _build_signature_base(
        self,
        *,
        method: str,
        target_uri: str,
        headers: Dict[str, str],
        covered: List[str],
        params_raw: str,
    ) -> str:
        """Construct the signature base string per RFC 9421 §2.5."""
        lines: List[str] = []
        for component in covered:
            name = component.lower()
            if name == "@method":
                lines.append(f'"@method": {method.upper()}')
            elif name == "@target-uri":
                lines.append(f'"@target-uri": {target_uri}')
            elif name.startswith("@"):
                # Derived components other than the two above are
                # intentionally not supported here; callers should use
                # @method/@target-uri plus header components.
                raise SignatureVerificationError(
                    f"Unsupported derived component {component!r}",
                    component=component,
                )
            else:
                # Case-insensitive header lookup.
                value = None
                for key, val in headers.items():
                    if key.lower() == name:
                        value = val.strip()
                        break
                if value is None:
                    raise SignatureVerificationError(
                        f"Covered header {name!r} missing from request",
                        component=name,
                    )
                lines.append(f'"{name}": {value}')
        lines.append(f'"@signature-params": ({" ".join(covered)});{params_raw}')
        return "\n".join(lines)

    def _verify_signature(
        self,
        *,
        public_key: bytes,
        alg: str,
        signature: bytes,
        signing_input: bytes,
    ) -> None:
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import (
                ec,
                ed25519,
                padding,
                rsa,
            )
        except ImportError as e:
            raise SignatureVerificationError(
                f"cryptography package required for signature verification: {e}"
            )

        try:
            key = serialization.load_pem_public_key(public_key)
        except Exception as e:
            raise KeyDiscoveryError(f"Invalid PEM public key: {e}")

        try:
            if alg == "ed25519" and isinstance(key, ed25519.Ed25519PublicKey):
                key.verify(signature, signing_input)
            elif alg == "ecdsa-p256-sha256" and isinstance(
                key, ec.EllipticCurvePublicKey
            ):
                key.verify(signature, signing_input, ec.ECDSA(hashes.SHA256()))
            elif alg == "rsa-pss-sha512" and isinstance(key, rsa.RSAPublicKey):
                key.verify(
                    signature,
                    signing_input,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA512()),
                        salt_length=padding.PSS.MAX_LENGTH,
                    ),
                    hashes.SHA512(),
                )
            else:
                raise SignatureVerificationError(
                    f"Unsupported key/alg combination: {alg}"
                )
        except InvalidSignature:
            raise SignatureVerificationError("Signature verification failed")
        except Exception as e:
            raise SignatureVerificationError(f"Signature verification error: {e}")


# ---------------------------------------------------------------------------
# JWS descriptor signing (RFC 7515 + RFC 8785 JCS)
# ---------------------------------------------------------------------------


def jcs_canonicalize(value: Any) -> bytes:
    """RFC 8785 JSON Canonicalization Scheme (minimal compliant form).

    Sorts object keys, uses no whitespace, and the default JSON encoding
    for strings/numbers — sufficient for signing descriptor JSON that
    uses only basic types.
    """
    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")


class JWSDescriptorVerifier:
    """Verify a JWS-signed descriptor (RFC 7515) over JCS (RFC 8785).

    Expects a detached JWS header in the response's ``X-Agent-JWS``
    header and the raw descriptor body; canonicalises the descriptor
    with JCS and verifies the signature against a resolved public key.
    """

    def __init__(self, key_resolver: Callable[[str], bytes]):
        if jwt is None:
            raise ImportError(
                "PyJWT required for JWSDescriptorVerifier; install 'pyjwt'."
            )
        self.key_resolver = key_resolver

    def verify(self, descriptor: Dict[str, Any], jws_header_value: str) -> None:
        payload = jcs_canonicalize(descriptor)
        try:
            # Detached-payload JWS: header..signature
            head, _, sig = jws_header_value.partition("..")
            encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
            assembled = f"{head}.{encoded_payload}.{sig}"
            unverified = jwt.get_unverified_header(assembled)
            keyid = unverified.get("kid")
            if not keyid:
                raise SignatureVerificationError("JWS missing kid in header")
            key = self.key_resolver(keyid)
            jwt.decode(
                assembled,
                key=key,
                algorithms=[unverified.get("alg", "EdDSA")],
                options={"verify_signature": True, "verify_exp": False},
            )
        except SignatureVerificationError:
            raise
        except Exception as e:
            raise SignatureVerificationError(f"JWS descriptor verification failed: {e}")
